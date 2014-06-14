
import feedparser
import webFunctions
import bs4
import re

import urllib.parse
import time
import dateutil.parser
import runStatus
import settings
import datetime

import ScrapePlugins.RetreivalDbBase
import nameTools as nt

class SkFeedLoader(ScrapePlugins.RetreivalDbBase.ScraperDbBase):



	wg = webFunctions.WebGetRobust()
	loggerPath = "Main.Sk.Fl"
	pluginName = "Starkana Link Retreiver"
	tableName = "SkMangaItems"
	dbName = settings.dbName


	urlBase = "http://starkana.com/"

	feedUrl = "http://starkana.com/new/%d"


	def checkLogin(self):
		for cookie in self.wg.cj:
			if "SMFCookie232" in str(cookie):   # We have a log-in cookie
				return True

		self.log.info( "Getting Login cookie")
		logondict = {"login-user" : settings.skSettings["login"], "login-pass" : settings.skSettings["passWd"], "rememberme" : "on"}
		self.wg.getpage('http://www.mangatraders.com/login/processlogin', postData=logondict)

		self.wg.saveCookies()

	def closeDB(self):
		self.log.info( "Closing DB...",)
		self.conn.close()
		self.log.info( "done")



	def getItemFromContainer(self, segmentSoup, addDate):
		seriesName, chapter = segmentSoup.get_text().strip().split(" chapter ")

		chName = "{series} - {chapter}".format(series=seriesName, chapter=chapter)

		# chName, seriesName, size, view = segmentSoupItems


		item = {}

		item["date"] = time.mktime(addDate.timetuple())
		item["dlName"] = chName
		item["dlLink"] =  urllib.parse.urljoin(self.urlBase, segmentSoup.a["href"])
		item["baseName"] = nt.makeFilenameSafe(seriesName)

		return item

	def getSeriesPage(self, seriesUrl):
		page = self.wg.getpage(seriesUrl)
		soup = bs4.BeautifulSoup(page)
		itemDivs = soup.find_all("td", class_=re.compile("c_h2b?"), align="left")

		ret = []

		for td in itemDivs:
			ret.append(self.getItemFromContainer(td, datetime.date.today()))
		return ret

	def getMainItems(self, rangeOverride=None, rangeOffset=None):
		# for item in items:
		# 	self.log.info( item)
		#

		self.log.info( "Loading SK Main Feed")

		ret = []

		seriesPages = []

		if not rangeOverride:
			dayDelta = 1
		else:
			dayDelta = int(rangeOverride)
		if not rangeOffset:
			rangeOffset = 0

		currentDate = None

		for daysAgo in range(1, dayDelta+1):

			url = self.feedUrl % daysAgo
			page = self.wg.getpage(url)
			soup = bs4.BeautifulSoup(page)

			# Find the divs containing either new files, or the day a file was uploaded
			itemDivs = soup.find_all("div", class_=re.compile("c_h[12]b?"))

			for div in itemDivs:
				if "c_h1" in div["class"]:
					dateStr = div.get_text()
					currentDate = dateutil.parser.parse(dateStr)


				else:
					if not currentDate:
						raise ValueError("How did we get a file before a valid date?")

					if not "chapter" in div.a["href"]:
						seriesPages.append(urllib.parse.urljoin(self.urlBase, div.a["href"]))
					else:
						item = self.getItemFromContainer(div, currentDate)
						ret.append(item)

		for SeriesPage in seriesPages:
			seriesItems = self.getSeriesPage(SeriesPage)
			if seriesItems:
				ret.extend(seriesItems)

			if not runStatus.run:
				self.log.info( "Breaking due to exit flag being set")
				break

		return ret



	def resetStuckItems(self):
		self.log.info("Resetting stuck downloads in DB")
		self.conn.execute('''UPDATE {table} SET dlState=0 WHERE dlState=1'''.format(table=self.tableName))
		self.conn.commit()
		self.log.info("Download reset complete")


	def processLinksIntoDB(self, linksDicts, isPicked=False):

		self.log.info( "Inserting...",)
		newItems = 0
		for link in linksDicts:
			if link is None:
				print("linksDicts", linksDicts)
				print("WAT")

			row = self.getRowsByValue(sourceUrl=link["dlLink"])
			if not row:
				newItems += 1
					# Flags has to be an empty string, because the DB is annoying.
					#
					# TL;DR, comparing with LIKE in a column that has NULLs in it is somewhat broken.
					#
				flagStr = ""
				if isPicked:
					flagStr = "picked"

				self.insertIntoDb(retreivalTime = link["date"],
									sourceUrl   = link["dlLink"],
									originName  = link["dlName"],
									dlState     = 0,
									seriesName  = link["baseName"],
									flags       = flagStr)


				self.log.info("New item: %s", (link["date"], link["dlLink"], link["baseName"], link["dlName"]))


			else:
				row = row.pop()
				if isPicked and not "picked" in row["flags"]:  # Set the picked flag if it's not already there, and we have the item already
					self.updateDbEntry(link["dlLink"],flags=" ".join([row["flags"], "picked"]))

				# Starkana is fucking annoying, and when someone uploads more then just one chapter, the "view"
				# link just goes to the root-page of the manga series, rather then actually having volume archives.
				# Blaugh.
				# As such, just reset the download state of the file so we can go and actually look at the series files.
				if link["date"] > row["retreivalTime"] and not "chapter" in dlLink:
					self.log.warning("Link to series page. Fuck you, starkana")
					self.updateDbEntry(link["dlLink"], dlState = 0)

				# TODO: in the future, replace this with something that goes and just grabs ALL THE FILES from the manga in question, and enqueues them?


		self.log.info( "Done")
		self.log.info( "Committing...",)
		self.conn.commit()
		self.log.info( "Committed")

		#for row in cur.execute('SELECT * FROM links'):
		#	self.log.info( row)

		return newItems


	def go(self):

		self.resetStuckItems()
		self.log.info("Getting feed items")

		feedItems = self.getMainItems()
		self.log.info("Processing feed Items")

		self.processLinksIntoDB(feedItems)
		self.log.info("Complete")



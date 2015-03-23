
# -*- coding: utf-8 -*-

import webFunctions
import os
import os.path

import random
import sys
import zipfile
import nameTools as nt

import runStatus
import time
import urllib.request, urllib.parse, urllib.error
import traceback

import settings
import bs4
import re

import processDownload
import json
from concurrent.futures import ThreadPoolExecutor

import ScrapePlugins.RetreivalDbBase

class FakkuContentLoader(ScrapePlugins.RetreivalDbBase.ScraperDbBase):




	shouldCanonize = False
	dbName = settings.DATABASE_DB_NAME
	loggerPath = "Main.Manga.Fakku.Cl"
	pluginName = "Fakku Content Retreiver"
	tableKey   = "fk"
	urlBase = "http://www.fakku.net/"

	tableName = "HentaiItems"

	wg = webFunctions.WebGetRobust(logPath=loggerPath+".Web")

	retreivalThreads = 6

	shouldCanonize = False

	def go(self):

		newLinks = self.retreiveTodoLinksFromDB()
		if newLinks:
			self.processTodoLinks(newLinks)

	def retreiveTodoLinksFromDB(self):

		self.log.info("Fetching items from db...",)

		rows = self.getRowsByValue(dlState=0)
		if not rows:
			self.log.info("No items")
			return
		self.log.info("Done")
		# print(rows)
		items = []
		for row in rows:
			# self.log.info("Row = %s", row)

			# Wait 18 hours after an item is uploaded to actually scrape it, since it looks like uploads
			# are almost always in a fucked up order at the start
			# Seriously, these kind of things are sequentially numbered. How can you fuck that up?
			# They manage, somehow.
			if row["retreivalTime"] < (time.time() + 60*60*18):
				items.append(row)  # Actually the contentID
		self.log.info("Have %s new items to retreive in FakkuDownloader" % len(items))

		return items



	def processTodoLinks(self, links):
		if links:

			def iter_baskets_from(items, maxbaskets=3):
				'''generates evenly balanced baskets from indexable iterable'''
				item_count = len(items)
				baskets = min(item_count, maxbaskets)
				for x_i in range(baskets):
					yield [items[y_i] for y_i in range(x_i, item_count, baskets)]

			linkLists = iter_baskets_from(links, maxbaskets=self.retreivalThreads)

			with ThreadPoolExecutor(max_workers=self.retreivalThreads) as executor:

				for linkList in linkLists:
					fut = executor.submit(self.downloadItemsFromList, linkList)

				executor.shutdown(wait=True)




	def downloadItemsFromList(self, linkList):


		for contentId in linkList:

			try:
				dlDict = self.processDownloadInfo(contentId)
				ret = self.doDownload(dlDict)
				if ret:
					delay = random.randint(5, 30)
				else:
					delay = 0

			except:
				self.log.error("ERROR WAT?")
				self.log.error(traceback.format_exc())
				self.log.error("Continuing...")
				delay = 1


			for x in range(delay):
				time.sleep(1)
				remaining = delay-x
				sys.stdout.write("\rFakku CL sleeping %d          " % remaining)
				sys.stdout.flush()
				if not runStatus.run:
					self.log.info("Breaking due to exit flag being set")
					return
			if not runStatus.run:
				self.log.info("Breaking due to exit flag being set")
				return

	def processDownloadInfo(self, linkDict):

		self.updateDbEntry(linkDict["sourceUrl"], dlState=1)

		sourcePage = linkDict["sourceUrl"]
		category   = linkDict['seriesName']

		self.log.info("Retreiving item: %s", sourcePage)

		linkDict['dirPath'] = os.path.join(settings.fkSettings["dlDir"], nt.makeFilenameSafe(category))

		if not os.path.exists(linkDict["dirPath"]):
			os.makedirs(linkDict["dirPath"])
		else:
			self.log.info("Folder Path already exists?: %s", linkDict["dirPath"])

		self.log.info("Folderpath: %s", linkDict["dirPath"])

		self.log.debug("Linkdict = ")
		for key, value in list(linkDict.items()):
			self.log.debug("		%s - %s", key, value)


		return linkDict


	def doDownload(self, linkDict):


		images = []
		containerUrl = linkDict["sourceUrl"]+"/read"

		if "http://www.fakku.net/videos/" in containerUrl:
			self.log.warning("Cannot download video items.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-5, downloadPath="Video", fileName="ERROR: Video", lastUpdate=time.time())
			return False

		if "http://www.fakku.net/games/" in containerUrl:
			self.log.warning("Cannot download game items.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-6, downloadPath="Game", fileName="ERROR: Game", lastUpdate=time.time())
			return False

		try:
			imagePage = self.wg.getpage(containerUrl, addlHeaders={'Referer': linkDict["sourceUrl"]})
		except urllib.error.URLError:
			self.log.warning("Failure to retreive base page!.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-1, downloadPath="ERROR", fileName="ERROR", lastUpdate=time.time())
			return False


		if "This content has been disabled due to a DMCA takedown notice, it is no longer available to download or read online in your region." in imagePage:
			self.log.warning("Assholes have DMCAed this item. Not available anymore.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-4, downloadPath="DMCA", fileName="ERROR: DMCAed", lastUpdate=time.time())
			return False

		if "Content does not exist." in imagePage:
			self.log.warning("Page removed?.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-7, downloadPath="REMOVED", fileName="ERROR: File removed", lastUpdate=time.time())
			return False

		# Fuck you Fakku, don't include pay-content in your free gallery system.
		if "You must purchase this book in order to read it." in imagePage:
			self.log.warning("Page removed?.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-7, downloadPath="REMOVED", fileName="ERROR: Paywalled. ", lastUpdate=time.time())
			return False

		# So...... Fakku's reader is completely javascript driven. No (easily) parseable shit here.
		# Therefore: WE DECEND TO THE LEVEL OF REGEXBOMINATIONS!
		pathFormatterRe = re.compile(r"return '(//t\.fakku\.net/images/.+/.+/.+?/images/)' \+ x \+ '(\.jpg|\.gif|\.png)';", re.IGNORECASE)

		# We need to know how many images there are, but there is no convenient way to access this information.
		# The fakku code internally uses the length of the thumbnail array for the number of images, so
		# we extract that array, parse it (since it's javascript, variables are JSON, after all), and
		# just look at the length ourselves as well.
		thumbsListRe    = re.compile(r"window\.params\.thumbs = (\[.+?\]);", re.IGNORECASE)

		thumbs        = thumbsListRe.search(imagePage)
		pathFormatter = pathFormatterRe.search(imagePage)


		if not thumbs:
			self.log.error("Could not find thumbnail array on page!")
			self.log.error("URL: '%s'", containerUrl)

		if not pathFormatter:
			self.log.error("Could not find pathformatter on page!")
			self.log.error("URL: '%s'", containerUrl)

		items = json.loads(thumbs.group(1))

		prefix, postfix = pathFormatter.group(1), pathFormatter.group(2)
		print("pathFormatter = ", prefix, prefix)


		imageUrls = []
		for x in range(len(items)):
			item = '{prefix}{num:03d}{postfix}'.format(prefix=pathFormatter.group(1), num=x+1, postfix=pathFormatter.group(2))
			imageUrls.append(item)

		# print("Prepared image URLs = ")
		# print(imageUrls)

		# print(linkDict)

		images = []
		try:
			for imageUrl in imageUrls:

				imagePath = urllib.parse.urlsplit(imageUrl)[2]
				imageFileName = imagePath.split("/")[-1]
				if imageUrl.startswith("//"):
					imageUrl = "https:" + imageUrl
				imageData = self.wg.getpage(imageUrl, addlHeaders={'Referer': containerUrl})

				images.append((imageFileName, imageData))
				# Find next page
		except urllib.error.URLError:
			self.log.error("Failure retreiving item images.")
			self.updateDbEntry(linkDict["sourceUrl"], dlState=-1, downloadPath="ERROR", fileName="ERROR: Could not retreive images!", lastUpdate=time.time())

			self.conn.commit()
			return False


		# self.log.info(len(content))

		if images:
			fileN = linkDict["originName"]+".zip"
			fileN = nt.makeFilenameSafe(fileN)


			# self.log.info("geturl with processing", fileN)
			wholePath = os.path.join(linkDict["dirPath"], fileN)
			self.log.info("Complete filepath: %s", wholePath)

					#Write all downloaded files to the archive.
			arch = zipfile.ZipFile(wholePath, "w")
			for imageName, imageContent in images:
				arch.writestr(imageName, imageContent)
			arch.close()


			self.log.info("Successfully Saved to path: %s", wholePath)

			if not linkDict["tags"]:
				linkDict["tags"] = ""

			self.updateDbEntry(linkDict["sourceUrl"], downloadPath=linkDict["dirPath"], fileName=fileN)


			# Deduper uses the path info for relinking, so we have to dedup the item after updating the downloadPath and fileN
			dedupState = processDownload.processDownload(None, wholePath, pron=True, deleteDups=True, includePHash=True)
			self.log.info( "Done")

			if dedupState:
				self.addTags(sourceUrl=linkDict["sourceUrl"], tags=dedupState)


			self.updateDbEntry(linkDict["sourceUrl"], dlState=2)
			self.conn.commit()


			return wholePath

		else:

			self.updateDbEntry(linkDict["sourceUrl"], dlState=-1, downloadPath="ERROR", fileName="ERROR: FAILED", lastUpdate=time.time())

			self.conn.commit()
			return False



if __name__ == "__main__":
	import utilities.testBase as tb

	with tb.testSetup(startObservers=False):
		# getHistory()
		run = FakkuContentLoader()
		# run.getFeed()
		run.go()

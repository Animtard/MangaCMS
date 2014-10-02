
# -*- coding: utf-8 -*-



import runStatus
runStatus.preloadDicts = False


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

import archCleaner

import ScrapePlugins.RetreivalBase

class HBrowseContentLoader(ScrapePlugins.RetreivalBase.ScraperBase):

	archCleaner = archCleaner.ArchCleaner()


	dbName = settings.dbName
	loggerPath = "Main.HBrowse.Cl"
	pluginName = "H-Browse Content Retreiver"
	tableKey   = "hb"
	urlBase = "http://www.hbrowse.com/"

	wg = webFunctions.WebGetRobust(logPath=loggerPath+".Web")

	tableName = "HentaiItems"

	retreivalThreads = 3

	shouldCanonize = False

	def getFileName(self, soup):
		title = soup.find("h1", class_="otitle")
		if not title:
			raise ValueError("Could not find title. Wat?")
		return title.get_text()

	def getCategoryTags(self, soup):
		tables = soup.find_all("table", class_="listTable")

		tags = []


		formatters = {

						'Genre'        : 'Genre',
						'Type'         : '',
						'Setting'      : '',
						'Fetish'       : 'Fetish',
						'Role'         : '',
						'Relationship' : '',
						'Male Body'    : 'Male',
						'Female Body'  : 'Female',
						'Grouping'     : 'Grouping',
						'Scene'        : '',
						'Position'     : 'Position'

					}

		ignoreTags = [
						'Title',
						'Artist',
						'Length'
					]



		# 'Origin'       : '',  (Category)
		category = "Unknown?"
		for table in tables:
			for tr in table.find_all("tr"):
				if len(tr.find_all("td")) != 2:
					continue

				what, values = tr.find_all("td")
				what = what.get_text().strip()
				if what in ignoreTags:
					continue


				elif what == "Origin":
					category = values.get_text().strip()
				elif what in formatters:
					for rawTag in values.find_all("a"):
						tag = " ".join([formatters[what], rawTag.get_text().strip()])
						tag = tag.strip()
						tag = tag.replace("  ", " ")
						tag = tag.replace(" ", "-")
						tags.append(tag)

		print(category, tags)
		return category, tags

	def getGalleryStartPages(self, soup):
		linkTds = soup.find_all("td", class_="listMiddle")

		ret = []

		for td in linkTds:
			ret.append(td.a['href'])

		return ret

	def getDownloadInfo(self, linkDict, retag=False):
		sourcePage = linkDict["sourceUrl"]

		self.log.info("Retreiving item: %s", sourcePage)

		if not retag:
			self.updateDbEntry(linkDict["sourceUrl"], dlState=1)


		try:
			soup = self.wg.getSoup(sourcePage, addlHeaders={'Referer': 'http://hbrowse.com/'})
		except:
			self.log.critical("No download at url %s! SourceUrl = %s", sourcePage, linkDict["sourceUrl"])
			raise IOError("Invalid webpage")

		category, tags = self.getCategoryTags(soup)
		tags = ' '.join(tags)

		linkDict['dirPath'] = os.path.join(settings.hbSettings["dlDir"], nt.makeFilenameSafe(category))

		if not os.path.exists(linkDict["dirPath"]):
			os.makedirs(linkDict["dirPath"])
		else:
			self.log.info("Folder Path already exists?: %s", linkDict["dirPath"])


		self.log.info("Folderpath: %s", linkDict["dirPath"])
		#self.log.info(os.path.join())


		startPages = self.getGalleryStartPages(soup)


		linkDict["dlLink"] = startPages



		self.log.debug("Linkdict = ")
		for key, value in list(linkDict.items()):
			self.log.debug("		%s - %s", key, value)


		if tags:
			self.log.info("Adding tag info %s", tags)

			self.addTags(sourceUrl=linkDict["sourceUrl"], tags=tags)


		self.updateDbEntry(linkDict["sourceUrl"], seriesName=category, lastUpdate=time.time())



		return linkDict


	def fetchImages(self, linkDict):
		title = None
		toFetch = {key:0 for key in linkDict["dlLink"]}


		images = {}
		while not all(toFetch.values()):

			# get a random dict element where downloadstate = 0
			thisPage = list(toFetch.keys())[list(toFetch.values()).index(0)]

			soup = self.wg.getSoup(thisPage, addlHeaders={'Referer': linkDict["sourceUrl"]})

			imageTd = soup.find('td', class_='pageImage')



			imageUrl = urllib.parse.urljoin(self.urlBase, imageTd.img["src"])

			imagePath = urllib.parse.urlsplit(imageUrl)[2]
			chapter = imageUrl.split("/")[-2]
			imName = imagePath.split("/")[-1]
			imageFileName = '{c} - {i}'.format(c=chapter, i=imName)

			self.log.info("Using filename '%s'", imageFileName)


			imageData = self.wg.getpage(imageUrl, addlHeaders={'Referer': thisPage})
			images[imageFileName] = imageData

			toFetch[thisPage] = 1
			# Find next page

			nextPageLink = imageTd.a['href']
			if nextPageLink != linkDict["sourceUrl"]:
				if not nextPageLink in toFetch:
					toFetch[nextPageLink] = 0


		# Use a dict, and then flatten to a list because we will fetch some items twice.
		# Basically, `http://www.hbrowse.com/{sommat}/c00000` has the same image
		# as  `http://www.hbrowse.com/{sommat}/c00000/00001`, but the strings are not matches.
		images = [(key, value) for key, value in images.items()]
		return images


	def doDownload(self, linkDict):

		images = self.fetchImages(linkDict)


		# self.log.info(len(content))

		if images:
			fileN = linkDict['originName']+".zip"
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


			dedupState = self.archCleaner.processNewArchive(wholePath, deleteDups=True, includePHash=True)
			self.log.info( "Done")


			if dedupState:
				self.addTags(sourceUrl=linkDict["sourceUrl"], tags=dedupState)

			self.updateDbEntry(linkDict["sourceUrl"], dlState=2, downloadPath=linkDict["dirPath"], fileName=fileN, seriesName=linkDict["seriesName"])

			self.conn.commit()
			return wholePath

		else:

			self.updateDbEntry(linkDict["sourceUrl"], dlState=-1, downloadPath="ERROR", fileName="ERROR: FAILED")

			self.conn.commit()
			return False


	def getLink(self, link):
		url = self.getDownloadInfo(link)
		self.doDownload(url)



if __name__ == "__main__":
	import utilities.testBase as tb

	with tb.testSetup(startObservers=False):

		run = HBrowseContentLoader()
		run.resetStuckItems()
		run.go()


import webFunctions
import settings
import os
import os.path

import nameTools as nt


import urllib.parse

import zipfile
import runStatus
import traceback
import bs4
import ScrapePlugins.RetreivalBase
import settings


import processDownload

class ContentLoader(ScrapePlugins.RetreivalBase.RetreivalBase):



	loggerPath = "Main.Manga.Sura.Cl"
	pluginName = "MangaCow Content Retreiver"
	tableKey = "sura"
	dbName = settings.DATABASE_DB_NAME
	tableName = "MangaItems"

	wg = webFunctions.WebGetRobust(logPath=loggerPath+".Web")

	retreivalThreads = 2

	def checkLogin(self):
		pg = self.wg.getpage('http://www.surasplace.com/index.php/login.html')
		expect = 'Hi {name},'.format(name=settings.suraSettings['login'])
		if expect in pg:
			self.log.info("Still logged in!")
		soup = bs4.BeautifulSoup(pg, "lxml")
		logindiv = soup.find('div', class_='login')

		params = logindiv.find_all("input")

		loginDict = {}
		for item in params:
			loginDict[item['name']] = item['value']

		loginDict['username'] = settings.suraSettings['login']
		loginDict['password'] = settings.suraSettings['passWd']

		target = logindiv.find("form")['action']
		target = urllib.parse.urljoin('http://www.surasplace.com/', target)

		page = self.wg.getpage(target, postData=loginDict)

		if not expect in page:
			self.log.error("Login failed?")
			raise ValueError("Login failed!")
		else:
			self.log.info("Logged in!")

		self.wg.syncCookiesFromFile()

	def setup(self):
		self.checkLogin()


	def getImage(self, imageUrl, referrer):

		content, handle = self.wg.getpage(imageUrl, returnMultiple=True, addlHeaders={'Referer': referrer})
		if not content or not handle:
			raise ValueError("Failed to retreive image from page '%s'!" % referrer)

		fileN = urllib.parse.unquote(urllib.parse.urlparse(handle.geturl())[2].split("/")[-1])
		fileN = bs4.UnicodeDammit(fileN).unicode_markup
		self.log.info("retreived image '%s' with a size of %0.3f K", fileN, len(content)/1000.0)
		return fileN, content



	def getImageUrls(self, baseUrl):
		soup = self.wg.getSoup(baseUrl, addlHeaders={'Referer': 'http://www.surasplace.com/index.php/projects.html'})

		# The item title isn't available in a nice format on the
		# hub page. Therefore, we scrape it here.
		title = soup.find("h2", itemprop="name")
		itemTitle = title.get_text().strip()

		imageUrls = []

		content = soup.find('div', itemprop='articleBody')


		# So, for contexts where there is only a single image, it's just in a <p> tag, rather
		# then in a proper <td>
		tds = content.find_all('td')
		imgs = content.find_all('img')
		if tds:
			for td in tds:
				# print(td.img['src'])
				imageUrls.append((td.img['src'], baseUrl))
		elif imgs:
			for img in imgs:
				# print(img['src'])
				imageUrls.append((img['src'], baseUrl))
		else:
			self.log.error("Cannot find any images! Wat?")


		return itemTitle, imageUrls




	def getLink(self, link):
		sourceUrl  = link["sourceUrl"]
		seriesName = link["seriesName"]
		chapterVol = link["originName"]

		sourceUrl = sourceUrl.encode("ascii").decode('ascii')

		# print("Item:", link)
		try:
			self.log.info( "Should retreive url - %s", sourceUrl)
			self.updateDbEntry(sourceUrl, dlState=1)

			chapterVol, imageUrls = self.getImageUrls(sourceUrl)
			if not imageUrls:
				self.log.critical("Failure on retreiving content at %s", sourceUrl)
				self.log.critical("No images found on page!")
				self.updateDbEntry(sourceUrl, dlState=-1)
				return


			self.log.info("Downloading = '%s', '%s'", seriesName, chapterVol)
			dlPath, newDir = self.locateOrCreateDirectoryForSeries(seriesName)

			if link["flags"] == None:
				link["flags"] = ""

			if newDir:
				self.updateDbEntry(sourceUrl, flags=" ".join([link["flags"], "haddir"]), originName=chapterVol)
			self.updateDbEntry(sourceUrl, originName=chapterVol)

			chapterName = nt.makeFilenameSafe(chapterVol)

			fqFName = os.path.join(dlPath, chapterName+"[Sura's Place].zip")

			loop = 1
			while os.path.exists(fqFName):
				fqFName, ext = os.path.splitext(fqFName)
				fqFName = "%s (%d)%s" % (fqFName, loop,  ext)
				loop += 1
			self.log.info("Saving to archive = %s", fqFName)

			images = []
			imgCnt = 1

			for imgUrl, referrerUrl in imageUrls:
				imageName, imageContent = self.getImage(imgUrl, referrerUrl)
				imageName = "{num:03.0f} - {srcName}".format(num=imgCnt, srcName=imageName)
				imgCnt += 1

				images.append([imageName, imageContent])

				if not runStatus.run:
					self.log.info( "Breaking due to exit flag being set")
					self.updateDbEntry(sourceUrl, dlState=0)
					return

			self.log.info("Creating archive with %s images", len(images))

			if not images:
				self.updateDbEntry(sourceUrl, dlState=-1, seriesName=seriesName, originName=chapterVol, tags="error-404")
				return

			#Write all downloaded files to the archive.
			arch = zipfile.ZipFile(fqFName, "w")
			for imageName, imageContent in images:
				arch.writestr(imageName, imageContent)
			arch.close()


			dedupState = processDownload.processDownload(seriesName, fqFName, deleteDups=True, includePHash=True, rowId=link['dbId'])
			self.log.info( "Done")

			filePath, fileName = os.path.split(fqFName)
			self.updateDbEntry(sourceUrl, dlState=2, downloadPath=filePath, fileName=fileName, seriesName=seriesName, originName=chapterVol, tags=dedupState)
			return



		except Exception:
			self.log.critical("Failure on retreiving content at %s", sourceUrl)
			self.log.critical("Traceback = %s", traceback.format_exc())
			self.updateDbEntry(sourceUrl, dlState=-1)



if __name__ == "__main__":
	import utilities.testBase as tb

	# with tb.testSetup(startObservers=True):
	with tb.testSetup(startObservers=True):
		get = ContentLoader()
		# get.getSeriesPages()
		# get.getAllItems()
		get.go()
		# get.setup()





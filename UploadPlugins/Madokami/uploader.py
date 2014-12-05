
import runStatus
if __name__ == "__main__":
	runStatus.preloadDicts = False

import ftplib
import settings
import logging
import os
import nameTools as nt
import base64
import Levenshtein as lv
import json
import time
import webFunctions

COMPLAIN_ABOUT_DUPS = True

import urllib.parse
import ScrapePlugins.RetreivalDbBase

class MkUploader(ScrapePlugins.RetreivalDbBase.ScraperDbBase):
	log = logging.getLogger("Main.Mk.Uploader")

	loggerPath = "Main.Mk.Up"
	pluginName = "Manga.Madokami Content Retreiver"
	tableKey = "mk"
	dbName = settings.dbName

	tableName = "MangaItems"


	def __init__(self):

		super().__init__()


		self.wg = webFunctions.WebGetRobust(logPath=self.loggerPath+".Web")

		# Override undocumented class member to set the FTP encoding.
		# This is a HORRIBLE hack.
		# ftplib.FTP.encoding = "UTF-8"

		self.ftp = ftplib.FTP(host=settings.mkSettings["ftpAddr"])

		self.ftp.login()
		self.mainDirs     = {}
		self.unsortedDirs = {}

	def go(self):
		pass

	def moveItemsInDir(self, srcDirPath, dstDirPath):
		# FTP is /weird/. Rename apparently really wants to use the cwd for the srcpath param, even if the
		# path starts with "/". Therefore, we have to reset the CWD.
		self.ftp.cwd("/")
		for itemName, dummy_stats in self.ftp.mlsd(srcDirPath):
			if itemName == ".." or itemName == ".":
				continue
			srcPath = os.path.join(srcDirPath, itemName)
			dstPath = os.path.join(dstDirPath, itemName)
			self.ftp.rename(srcPath, dstPath)
			self.log.info("	Moved from '%s'", srcPath)
			self.log.info("	        to '%s'", dstPath)


	def aggregateDirs(self, pathBase, dir1, dir2):
		canonName = nt.getCanonicalMangaUpdatesName(dir1)
		canonNameAlt = nt.getCanonicalMangaUpdatesName(dir2)
		if canonName != canonNameAlt:
			self.log.critical("Error in uploading file. Name lookup via MangaUpdates table not commutative!")
			self.log.critical("First returned value    '%s'", canonName)
			self.log.critical("For directory with path '%s'", dir1)
			self.log.critical("Second returned value   '%s'", canonNameAlt)
			self.log.critical("For directory with path '%s'", dir2)

			raise ValueError("Identical and yet not?")
		self.log.info("Aggregating directories for canon name '%s':", canonName)

		n1 = lv.distance(dir1, canonName)
		n2 = lv.distance(dir2, canonName)

		self.log.info("	%s - '%s'", n1, dir1)
		self.log.info("	%s - '%s'", n2, dir2)

		# I'm using less then or equal, so situations where
		# both names are equadistant get aggregated anyways.
		if n1 <= n2:
			src = dir2
			dst = dir1
		else:
			src = dir1
			dst = dir2

		src = os.path.join(pathBase, src)
		dst = os.path.join(pathBase, dst)

		self.moveItemsInDir(src, dst)
		self.log.info("Removing directory '%s'", src)
		self.ftp.rmd(src)

		return dst

	def loadRemoteDirectory(self, fullPath, aggregate=False):
		ret = {}



		for dirName, stats in self.ftp.mlsd(fullPath):

			# Skip items that aren't directories
			if stats["type"]!="dir":
				continue

			canonName = nt.getCanonicalMangaUpdatesName(dirName)
			matchingName = nt.prepFilenameForMatching(canonName)

			fqPath = os.path.join(fullPath, dirName)

			# matchName = os.path.split(ret[matchingName])[-1]

			if matchingName in ret:
				# if aggregate:
				# 	fqPath = self.aggregateDirs(fullPath, dirName, matchName)
				# else:
				if COMPLAIN_ABOUT_DUPS:
					self.log.warning("Duplicate directories for series '%s'!", canonName)
					self.log.warning("	'%s'", dirName)
					self.log.warning("	'%s'", matchingName)
				ret[matchingName] = fqPath

			else:
				ret[matchingName] = fqPath

		return ret

	def loadMainDirs(self):
		ret = {}
		try:
			dirs = list(self.ftp.mlsd(settings.mkSettings["mainContainerDir"]))
		except ftplib.error_perm:
			self.log.critical("Container dir ('%s') does not exist!", settings.mkSettings["mainContainerDir"])
		for dirPath, dummy_stats in dirs:
			if dirPath == ".." or dirPath == ".":
				continue
			dirPath = os.path.join(settings.mkSettings["mainContainerDir"], dirPath)
			items = self.loadRemoteDirectory(dirPath)
			for key, value in items.items():
				if key not in ret:
					ret[key] = value
				else:
					for item in value:
						ret[key].append(item)

			self.log.info("Loading contents of FTP dir '%s'.", dirPath)
		self.log.info("Have '%s remote directories on FTP server.", len(ret))
		return ret

	def checkInitDirs(self):
		try:
			dirs = list(self.ftp.mlsd(settings.mkSettings["uploadContainerDir"]))
		except ftplib.error_perm:
			self.log.critical("Container dir for uploads ('%s') does not exist!", settings.mkSettings["uploadContainerDir"])
			raise

		fullPath = os.path.join(settings.mkSettings["uploadContainerDir"], settings.mkSettings["uploadDir"])
		if settings.mkSettings["uploadDir"] not in [item[0] for item in dirs]:
			self.log.info("Need to create base container path")
			self.ftp.mkd(fullPath)
		else:
			self.log.info("Base container directory exists.")

		# self.mainDirs     = self.loadMainDirs()
		self.unsortedDirs = self.loadRemoteDirectory(fullPath, aggregate=True)


	def migrateTempDirContents(self):
		for key in self.unsortedDirs.keys():
			if key in self.mainDirs and len(self.mainDirs[key]) == 1:
				print("Should move", key)
				print("	Src:", self.unsortedDirs[key])
				print("	Dst:", self.mainDirs[key][0])
				src = self.unsortedDirs[key]
				dst = self.mainDirs[key][0]

				self.moveItemsInDir(src, dst)
				self.log.info("Removing directory '%s'", src)
				self.ftp.rmd(src)


	def getExistingDir(self, seriesName):

		mId = nt.getMangaUpdatesId(seriesName)
		if not mId:
			return False

		self.log.info("Found mId for %s - %s", mId, seriesName)

		passStr = '%s:%s' % (settings.mkSettings["login"], settings.mkSettings["passWd"])
		authHeader = base64.encodestring(passStr.encode("ascii"))
		authHeader = authHeader.replace(b'\n', b'')
		authHeader = {"Authorization": "Basic %s" % authHeader.decode("ascii")}


		dirInfo = self.wg.getpage("https://manga.madokami.com/api/muid/{mId}".format(mId=mId), addlHeaders = authHeader)

		ret = json.loads(dirInfo)
		if not 'result' in ret or not ret['result']:
			self.log.info("No directory information in returned query.")
			return False

		self.log.info("Have directory info from API query. Contains %s directories.", len(ret['data']))
		if len(ret['data']) == 0:
			return False

		dirInfo = ret['data'].pop()
		return dirInfo['path']

	def getUploadDirectory(self, seriesName):

		ulDir = self.getExistingDir(seriesName)

		if not ulDir:
			seriesName = nt.getCanonicalMangaUpdatesName(seriesName)
			safeFilename = nt.makeFilenameSafe(seriesName)
			matchName = nt.prepFilenameForMatching(seriesName)
			matchName = matchName.encode('latin-1', 'ignore').decode('latin-1')

			self.checkInitDirs()
			if matchName in self.unsortedDirs:
				ulDir = self.unsortedDirs[matchName]
			else:

				self.log.info("Need to create container directory for %s", seriesName)
				ulDir = os.path.join(settings.mkSettings["uploadContainerDir"], settings.mkSettings["uploadDir"], safeFilename)
				self.ftp.mkd(ulDir)


		return ulDir

	def uploadFile(self, seriesName, filePath):

		ulDir = self.getUploadDirectory(seriesName)


		dummy_path, filename = os.path.split(filePath)
		self.log.info("Uploading file %s", filePath)
		self.log.info("From series %s", seriesName)
		self.log.info("To container directory %s", ulDir)
		self.ftp.cwd(ulDir)

		command = "STOR %s" % filename

		self.ftp.storbinary(command, open(filePath, "rb"))
		self.log.info("File Uploaded")


		dummy_fPath, fName = os.path.split(filePath)
		url = urllib.parse.urljoin("http://manga.madokami.com", urllib.parse.quote(filePath.strip("/")))

		fName = fName.encode('latin-1', 'ignore').decode('latin-1')

		self.insertIntoDb(retreivalTime = time.time(),
							sourceUrl   = url,
							originName  = fName,
							dlState     = 3,
							seriesName  = seriesName,
							flags       = '',
							tags="uploaded",
							commit = True)  # Defer commiting changes to speed things up





def uploadFile(seriesName, filePath):
	uploader = MkUploader()
	uploader.uploadFile(seriesName, filePath)


def test():
	uploader = MkUploader()
	uploader.checkInitDirs()
	uploader.getExistingDir('87 Clockers')
	# uploader.uploadFile('87 Clockers', '/media/Storage/Manga/87 Clockers/87 Clockers - v4 c21 [batoto].zip')


if __name__ == "__main__":

	import utilities.testBase as tb
	with tb.testSetup(startObservers=False):
		test()


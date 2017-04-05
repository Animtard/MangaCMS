import os.path

import processDownload
import nameTools as nt
import shutil
import settings
import DbBase
import rpyc
import signal
import traceback
import os
import deduplicator.archChecker


class DirDeduper(DbBase.DbBase):


	def addTag(self, srcPath, newTags):
		# Don't do anything if we're not actually doing anything.
		if newTags == '':
			return

		with self.context_cursor() as cur:

			tagsets = []
			rowIds = []

			cur.execute("BEGIN;")
			basePath, fName = os.path.split(srcPath)
			# print("fname='%s', path='%s'" % (fName, basePath))
			cur.execute('''SELECT dbId, tags FROM {tableName} WHERE fileName=%s AND downloadPath=%s;'''.format(tableName=self.tableName), (fName, basePath))
			rows = cur.fetchall()
			if len(rows) >= 1:
				exists = 0
				for rowid, tagsTmp in rows:

					if tagsTmp is None:
						tagsTmp = ''
					if not any([tmp in tagsTmp for tmp in ["deleted", "missing", "duplicate"]]):
						exists += 1
						rowIds.append(rowid)

					tagsets.append(tagsTmp)

			else:
				self.log.info("File {fname} not in manga database!".format(fname=srcPath))
				return

			if not rowIds:
				self.log.warning("Wat?")
				return

			for tags, rowId in zip(tagsets, rowIds):
				if tags is None:
					tags = ''
				tags = set(tags.split())
				for tag in newTags.split():
					if tag:
						tags.add(tag)

				tags = [tag.lower() for tag in tags]
				tags.sort()
				cur.execute('''UPDATE {tableName} SET tags=%s WHERE dbId=%s;'''.format(tableName=self.tableName), (" ".join(tags), rowId))
			cur.execute("COMMIT;")


	def removeTag(self, dbid, deltag):

		with self.transaction() as cur:
			cur.execute('''SELECT dbId, tags FROM {tableName} WHERE dbid=%s;'''.format(tableName=self.tableName), (dbid, ))
			rows = cur.fetchall()
			assert len(rows) == 1
			dbid, tags = rows[0]
			tags = tags.split(" ")
			tags.remove(deltag)

			tags = [tag.lower() for tag in tags]
			tags.sort()

			cur.execute('''UPDATE {tableName} SET tags=%s WHERE dbId=%s;'''.format(tableName=self.tableName), (" ".join(tags), dbid))
			print("Item return:", dbid, tags)


	def setupDbApi(self):
		pass

	def cleanDirectory(self, dirPath, includePhash=False, pathPositiveFilter=None):
		if pathPositiveFilter is None:
			pathPositiveFilter = ['']

		self.log.info("Cleaning path '%s'", dirPath)
		items = os.listdir(dirPath)
		items.sort()
		for item in items:
			item = os.path.join(dirPath, item)
			if os.path.isdir(item):
				print("Scanning", item)
				self.cleanSingleDir(item, includePhash, pathPositiveFilter)


	def __process_download(self, basePath, pathPositiveFilter):
		failures = 0
		while True:
			try:
				self.log.info("Scanning '%s'", basePath)

				proc = processDownload.MangaProcessor()
				tags = proc.processDownload(seriesName=None, archivePath=basePath, pathPositiveFilter=pathPositiveFilter)
				self.addTag(basePath, tags)
				return
			except EOFError:
				failures += 1
				if failures > 5:
					raise

			except KeyboardInterrupt:
				raise


	def cleanSingleDir(self, dirPath, includePhash=True, pathPositiveFilter=None):
		if pathPositiveFilter is None:
			pathPositiveFilter = ['']

		self.log.info("Processing subdirectory '%s'", dirPath)
		if not dirPath.endswith("/"):
			dirPath = dirPath + '/'

		items = os.listdir(dirPath)

		items = [os.path.join(dirPath, item) for item in items]

		dirs = [i for i in items if os.path.isdir(i)]
		self.log.info("Recursing into %s subdirectories!", len(dirs))
		for subDir in dirs:
			self.cleanSingleDir(subDir, includePhash, pathPositiveFilter)


		parsedItems = [(os.path.getsize(i), i) for i in items if os.path.isfile(i)]

		parsedItems.sort()


		for dummy_num, basePath in parsedItems:
			self.__process_download(basePath, pathPositiveFilter)

	def cleanBySourceKey(self, sourceKey, includePhash=True, pathPositiveFilter=None):
		if pathPositiveFilter is None:
			pathPositiveFilter = ['']

		self.log.info("Getting fetched items from database for source: %s", sourceKey)
		with self.context_cursor() as cur:
			cur.execute('''SELECT dbid, filename, downloadpath, tags FROM mangaitems WHERE sourcesite=%s and dlstate=2;''', (sourceKey, ))
			ret = cur.fetchall()
		self.log.info("Found %s items from source %s.", len(ret), sourceKey)
		for dbid, filename, downloadpath, tags in ret:
			if not tags:
				tags = ""

			taglist = tags.split()

			fpath = os.path.join(downloadpath, filename)

			if tags and 'dup-checked' in taglist:
				self.log.info("File %s was dup-checked in the current session. Skipping.", fpath)
				continue

			if tags and 'was-duplicate' in taglist:
				continue

			if not filename or not downloadpath:
				self.log.error("Invalid path info: '%s', '%s'", downloadpath, filename)


			if not os.path.exists(fpath):
				continue


			proc = processDownload.MangaProcessor()
			tags = proc.processDownload(seriesName=None, archivePath=fpath, doUpload=False)
			tags += " dup-checked"
			self.log.info("Adding tags: '%s'", tags)
			self.addTag(fpath, tags)

		self.globalRemoveHTag('dup-checked')

	def cleanHHistory(self):
		self.log.info("Querying for items.")
		with self.context_cursor() as cur:
			cur.execute("SELECT dbid, filename, downloadpath, tags FROM hentaiitems WHERE dlstate=2 ORDER BY dbid ASC")
			ret = cur.fetchall()

		for dbid, filename, downloadpath, tags in ret:
			if not tags:
				tags = ""


			taglist = tags.split()

			fpath = os.path.join(downloadpath, filename)

			if tags and 'dup-checked' in taglist:
				self.log.info("File %s was dup-checked in the current session. Skipping.", fpath)
				continue

			if tags and 'was-duplicate' in taglist:
				continue

			if not filename or not downloadpath:
				self.log.error("Invalid path info: '%s', '%s'", downloadpath, filename)


			if not os.path.exists(fpath):
				continue


			proc = processDownload.HentaiProcessor()
			tags = proc.processDownload(seriesName=None, archivePath=fpath)
			tags += " dup-checked"
			self.log.info("Adding tags: '%s'", tags)
			self.addTag(fpath, tags)

		self.globalRemoveHTag('dup-checked')

	def cleanMHistory(self):
		self.log.info("Querying for items.")
		with self.context_cursor() as cur:
			cur.execute("SELECT dbid, filename, downloadpath, tags FROM mangaitems ORDER BY dbid ASC")
			ret = cur.fetchall()

		for dbid, filename, downloadpath, tags in ret:
			taglist = tags.split()

			fpath = os.path.join(downloadpath, filename)

			if tags and 'dup-checked' in taglist:
				self.log.info("File %s was dup-checked in the current session. Skipping.", fpath)
				continue

			if tags and 'was-duplicate' in taglist:
				continue

			if not filename or not downloadpath:
				self.log.error("Invalid path info: '%s', '%s'", downloadpath, filename)


			if not os.path.exists(fpath):
				continue


			proc = processDownload.MangaProcessor()
			tags = proc.processDownload(seriesName=None, archivePath=fpath, doUpload=False)
			tags += " dup-checked"
			self.log.info("Adding tags: '%s'", tags)
			self.addTag(fpath, tags)

		self.globalRemoveHTag('dup-checked')

	def globalRemoveHTag(self, bad_tag):
		assert bad_tag

		self.log.info("Querying for items.")
		with self.context_cursor() as cur:
			cur.execute("SELECT dbid, filename, downloadpath, tags FROM hentaiitems ORDER BY dbid ASC")
			ret = cur.fetchall()


		for dbid, filename, downloadpath, tags in ret:
			if not all([filename, downloadpath, tags]):
				continue
			taglist = tags.split()
			fpath = os.path.join(downloadpath, filename)
			if not taglist:
				continue
			if not bad_tag in taglist:
				continue

			self.log.info("Stripping tag from %s", fpath)
			self.removeTag(dbid, bad_tag)
		self.log.info("Scanned %s rows", len(ret))

	def purgeDedupTempsMd5Hash(self, dirPath):

		self.remote = rpyc.connect("localhost", 12345)
		self.db = self.remote.root.DbApi()

		self.log.info("Cleaning path '%s'", dirPath)
		items = os.listdir(dirPath)
		for itemInDelDir in items:

			fqPath = os.path.join(dirPath, itemInDelDir)
			try:
				dc = deduplicator.archChecker.ArchChecker(fqPath)
				fileHashes = dc.getHashes(shouldPhash=False)
			except ValueError:
				self.log.critical("Failed to create archive reader??")
				self.log.critical(traceback.format_exc())
				self.log.critical("File = '%s'", fqPath)
				self.log.critical("Skipping file")
				continue

			# Get all the hashes for every file /but/ any that are windows Thumbs.db files.
			itemHashes = set([item[1] for item in fileHashes if not item[0].endswith("Thumbs.db")])

			matches = [self.db.getByHash(fHash) for fHash in itemHashes]

			if not all(matches):
				self.log.error("Missing match for file '%s'", itemInDelDir)
				self.log.error("Skipping")
				continue

			badMatch = [match for match in matches if fqPath in match[0]]

			files = set([subitem[0] for item in matches for subitem in item])

			exists = []
			for item in files:
				if os.path.exists(item):
					exists.append(True)
				else:
					exists.append(False)
					self.log.warn("File no longer seems to exist: '%s'!", item)
					self.log.warn("Deleting from database")
					try:
						self.db.deleteDbRows(fspath=item)
					except KeyError:
						self.log.error("Key error when deleting. Already deleted?")

			# Check the SHIT OUTTA DAT
			# Check if all items in the DB exist,
			# print("allExist", all(allExist))

			self.log.info("AllMatched = '%s'", all(matches))
			self.log.info("allExist = '%s'", all(exists))
			self.log.info("haveBad = '%s'", any(badMatch))

			if all(matches) and all(exists) and not any(badMatch):
				self.log.info("Should delete!")

				self.log.critical("DELETING '%s'", fqPath)
				os.unlink(fqPath)

			else:
				self.log.critical("Scan failed? '%s'", itemInDelDir)
				self.log.critical("AllMatched = '%s'", all(matches))
				self.log.critical("allExist = '%s'", all(exists))
				self.log.critical("haveBad = '%s'", any(badMatch))


	def restoreDirectory(self, dirPath):


		self.log.info("Restoring path '%s'", dirPath)
		items = os.listdir(dirPath)
		items.sort()
		for item in items:
			split = len(item)
			while True:
				try:
					newName = item[:split].replace(";", "/")+item[split:]
					shutil.move(os.path.join(dirPath, item), os.path.join("/media/Storage/MP", newName))
					break
				except FileNotFoundError:
					print("ERR", newName)
					split -= 1
			print("item = ", newName)

	def reprocessFailedH(self):

		with self.context_cursor() as cur:
			cur.execute('''SELECT dbid, filename, downloadpath, tags FROM hentaiitems WHERE tags LIKE %s;''', ('%unprocessable%', ))
			ret = cur.fetchall()
		for dbid, fname, dpath, tags in ret:
			basePath = os.path.join(dpath, fname)

			tags = tags.split(" ")
			badtags = ['unprocessable', 'corrupt']
			for bad in badtags:
				while bad in tags:
					tags.remove(bad)
			print(os.path.exists(basePath), basePath)
			print(tags)

			proc = processDownload.MangaProcessor()
			tags = proc.processDownload(seriesName=None, archivePath=basePath, pathPositiveFilter=[''])
			self.addTag(basePath, tags)


	def moveUnlinkableDirectories(self, dirPath, toPath):


		print("Moving Unlinkable from", dirPath)
		print("To:", toPath)
		if not os.path.isdir(dirPath):
			print(dirPath, "is not a directory")
			raise ValueError
		if not os.path.isdir(toPath):
			print(toPath, "is not a directory")
			raise ValueError

		srcItems = os.listdir(dirPath)
		srcItems.sort()
		print("Len ", len(srcItems))
		for item in srcItems:
			itemPath = os.path.join(dirPath, item)
			if not os.path.isdir(itemPath):
				continue

			if not nt.haveCanonicalMangaUpdatesName(item):
				targetDir = os.path.join(toPath, item)
				print("Moving item", item, "to unlinked dir")
				shutil.move(itemPath, targetDir)


		srcItems = os.listdir(toPath)
		srcItems.sort()
		print("Len ", len(srcItems))
		for item in srcItems:
			itemPath = os.path.join(toPath, item)
			if not os.path.isdir(itemPath):
				continue

			if nt.haveCanonicalMangaUpdatesName(item):
				print("Moving item", item, "to linked dir")
				targetDir = os.path.join(dirPath, item)
				shutil.move(itemPath, targetDir)
			else:
				mId = nt.getAllMangaUpdatesIds(item)
				if mId:
					print("Item has multiple matches:", itemPath)
					for no in mId:
						print("	URL: https://www.mangaupdates.com/series.html?id=%s" % (no, ))

	# This is implemented as a separate codepath from the mormal dir dedup calls as a precautionary measure against
	# stupid coding issues. It's not a perfect fix, but it's better then nothing.
	def purgeDupDirPhash(self, dirPath):

		self.remote = rpyc.connect("localhost", 12345)
		self.db = self.remote.root.DbApi()

		items = os.listdir(dirPath)
		items = [os.path.join(dirPath, item) for item in items]
		items = [item for item in items if os.path.isfile(item)]

		for fileName in items:
			isDup = self.checkIfNotUnique(fileName)
			if isDup:
				self.log.critical("DELETING '%s'", fileName)
				os.unlink(fileName)

	def checkIfNotUnique(self, fileName):
		'''
		Check if item `filename` in the currently open archive is unique

		Returns True if item not unique, False if it is unique
		'''

		dc = deduplicator.archChecker.ArchChecker(fileName)
		try:
			hashes = dc.getHashes(shouldPhash=True)
		except Exception:
			self.log.error("Error when scanning item!")
			self.log.error("File: '%s'", fileName)
			self.log.error(traceback.format_exc())
			return False

		for hashVal in hashes:
			if hashVal[2] == None:

				if hashVal[0].endswith("Thumbs.db"):
					self.log.info("Windows Thumbs.db file")
					continue

				if hashVal[0].endswith("deleted.txt"):
					self.log.info("Advert Deletion note.")
					continue

				self.log.info("Empty hash: '%s', for file '%s'", hashVal[2], hashVal)
				return False

			if hashVal[2] == 0:
				self.log.info("Stupidly common hash (%s). Skipping", hashVal[2])
				continue

			matches = self.db.getWithinDistance(hashVal[2], wantCols=['dbId', 'fspath'])


			exists = [os.path.exists(item[1]) for item in matches]

			# if we have no returned rows, or none of the returned rows exist, return false
			if not len(exists) or not any(matches):
				return False

		return True



class MDirDeduper(DirDeduper):
	loggerPath = "Main.MDirDedup"
	tableName  = "MangaItems"
	pluginName = "MDirDeduper"


class HDirDeduper(DirDeduper):
	loggerPath = "Main.HDirDedup"
	tableName  = "HentaiItems"
	pluginName = "HDirDeduper"


def runRestoreDeduper(sourcePath):

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.restoreDirectory(sourcePath)



def runMDeduper():

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.cleanMHistory()



def runSrcDeduper(sourceKey):

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.cleanBySourceKey(sourceKey)



def runKissDeduper():

	runSrcDeduper("ki")


def runHDeduper():

	dd = HDirDeduper()
	dd.setupDbApi()
	dd.cleanHHistory()


def resetDeduperScan():

	dd = HDirDeduper()
	dd.globalRemoveHTag('dup-checked')
	dd = MDirDeduper()
	dd.globalRemoveHTag('dup-checked')




def purgeDedupTemps(basePath):

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.purgeDedupTempsMd5Hash(basePath)


def purgeDedupTempsPhash(basePath):

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.purgeDupDirPhash(basePath)


def moveUnlinkable(dirPath, toPath):

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.moveUnlinkableDirectories(dirPath, toPath)


def runSingleDirDeduper(dirPath, deletePath):

	dd = MDirDeduper()
	dd.setupDbApi()
	if not os.path.isdir(dirPath):
		raise ValueError("Passed path is not a directory! Path: '%s'" % dirPath)

	dd.cleanSingleDir(dirPath, deletePath)






def reprocessHFailed():

	dd = MDirDeduper()
	dd.setupDbApi()
	dd.reprocessFailedH()



if __name__ == '__main__':
	import logSetup
	logSetup.initLogging()

	dd = HDirDeduper()
	dd.globalRemoveHTag("dup-checked")



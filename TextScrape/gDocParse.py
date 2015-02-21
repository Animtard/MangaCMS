

import bs4

import re
import io
import logging

import zipfile
import webFunctions
import mimetypes
import urllib.parse
import urllib.error
import json

import TextScrape.jsLiteralParse



def isGdocUrl(url):
	# This is messy, because it has to work through bit.ly redirects.
	# I'm just resolving them here, rather then keeping them around because it makes things easier.
	gdocBaseRe = re.compile(r'(https?://docs.google.com/document/d/[-_0-9a-zA-Z]+)')
	simpleCheck = gdocBaseRe.search(url)
	if simpleCheck and not url.endswith("/pub"):
		return True, simpleCheck.group(1)

	return False, url


def isGFileUrl(url):
	# This is messy, because it has to work through bit.ly redirects.
	# I'm just resolving them here, rather then keeping them around because it makes things easier.
	gFileBaseRe = re.compile(r'(https?://docs.google.com/file/d/[-_0-9a-zA-Z]+)')
	simpleCheck = gFileBaseRe.search(url)
	if simpleCheck and not url.endswith("/pub"):
		return True, simpleCheck.group(1)

	return False, url



def clearOutboundProxy(url):
	'''
	So google proxies all their outbound links through a redirect so they can detect outbound links.
	This call strips them out if they are present.

	'''
	if url.startswith("http://www.google.com/url?q="):
		qs = urllib.parse.urlparse(url).query
		query = urllib.parse.parse_qs(qs)
		if not "q" in query:
			raise ValueError("No target?")

		return query["q"].pop()

	return url



def clearBitLy(url):

	if "bit.ly" in url:
		wg = webFunctions.WebGetRobust(logPath="Main.BitLy.Web")
		try:

			dummy_ctnt, handle = wg.getpage(url, returnMultiple=True)
			# Recurse into redirects
			return clearBitLy(handle.geturl())

		except urllib.error.URLError:
			print("Error resolving redirect!")
			return None

	return url


class GDocExtractor(object):

	log = logging.getLogger("Main.GDoc")
	wg = webFunctions.WebGetRobust(logPath="Main.GDoc.Web")

	def __init__(self, targetUrl):

		isGdoc, url = isGdocUrl(targetUrl)
		if not isGdoc:
			raise ValueError("Passed URL '%s' is not a google document?" % targetUrl)

		self.url = url+'/export?format=zip'
		self.refererUrl = targetUrl

		self.document = ''

		self.currentChunk = ''

	@classmethod
	def getDriveFileUrls(cls, url):
		ctnt, handle = cls.wg.getpage(url, returnMultiple=True)

		# Pull out the title for the disambiguation page.
		soup = bs4.BeautifulSoup(ctnt)
		title = soup.title.string

		# horrible keyhole optimization regex abomination
		# this really, /REALLY/ should be a actual parser.
		# Unfortunately, the actual google doc URLs are only available in some JS literals,
		# so we have to deal with it.
		driveFolderRe = re.compile(r'(https://docs.google.com/(?:document|file)/d/[-_0-9a-zA-Z]+)')
		items = driveFolderRe.findall(ctnt)

		ret = set()

		# Google drive supports a `read?{google doc path} mode. As such, we look at the actual URL,
		# which tells us if we redirected to a plain google doc, and add it of we did.
		handleUrl = handle.geturl()
		if handleUrl != url:
			if isGdocUrl(handleUrl):
				cls.log.info("Direct read redirect: '%s'", handleUrl)
				ret.add(handleUrl)
		for item in items:
			ret.add(item)
		return items, title


	def extract(self):
		try:
			arch, fName = self.wg.getFileAndName(self.url, addlHeaders={'Referer': self.refererUrl})
		except IndexError:
			print("ERROR: Failure retreiving page!")
			return None, []

		baseName = fName.split(".")[0]

		if not isinstance(arch, bytes):
			if 'You need permission' in arch or 'Sign in to continue to Docs':
				self.log.critical("Retreiving zip archive failed?")
				self.log.critical("Retreived content type: '%s'", type(arch))
				raise TypeError("Cannot access document? Is it protected?")
			else:
				with open("tmp_page.html", "w") as fp:
					fp.write(arch)
				raise ValueError("Doc not valid?")

		zp = io.BytesIO(arch)
		zfp = zipfile.ZipFile(zp)

		resources = []
		baseFile = None

		for item in zfp.infolist():
			if not "/" in item.filename and not baseFile:
				contents = zfp.open(item).read()
				contents = bs4.UnicodeDammit(contents).unicode_markup

				baseFile = (item.filename, contents)

			elif baseName in item.filename and baseName:
				raise ValueError("Multiple base file items?")

			else:
				resources.append((item.filename, mimetypes.guess_type(item.filename)[0], zfp.open(item).read()))

		if not baseFile:
			raise ValueError("No base file found!")

		return baseFile, resources





class GFileExtractor(object):

	log = logging.getLogger("Main.GFile")
	wg = webFunctions.WebGetRobust(logPath="Main.GFile.Web")

	def __init__(self, targetUrl):

		isGdoc, url = isGFileUrl(targetUrl)
		if not isGdoc:
			raise ValueError("Passed URL '%s' is not a google document?" % targetUrl)

		self.url = url
		self.refererUrl = url

		self.document = ''

		self.currentChunk = ''

	def extract(self):

		try:
			content = self.wg.getpage(self.url, addlHeaders={'Referer': self.refererUrl})
		except IndexError:
			print("ERROR: Failure retreiving page!")
			return None, []




		initRe = re.compile('_initProjector\((.*?)\)', re.DOTALL)

		pageConf = initRe.findall(content)
		if not pageConf:
			self.log.error('Could not find download JSON on google file page "%s"', self.url)
		conf = pageConf.pop()

		conf = TextScrape.jsLiteralParse.jsParse('[{cont}]'.format(cont=conf.strip()))

		# assert len(conf)
		metadata = conf[-1]
		assert len(metadata) == 32
		title = metadata[1]
		dlUrl = metadata[18]

		print(title)
		print(dlUrl)
		fileUrl = dlUrl.encode("ascii").decode('unicode-escape')



		# baseName = fName.split(".")[0]

		# if not isinstance(arch, bytes):
		# 	if 'You need permission' in arch or 'Sign in to continue to Docs':
		# 		self.log.critical("Retreiving zip archive failed?")
		# 		self.log.critical("Retreived content type: '%s'", type(arch))
		# 		raise TypeError("Cannot access document? Is it protected?")
		# 	else:
		# 		with open("tmp_page.html", "w") as fp:
		# 			fp.write(arch)
		# 		raise ValueError("Doc not valid?")

		# zp = io.BytesIO(arch)
		# zfp = zipfile.ZipFile(zp)

		# resources = []
		# baseFile = None

		# for item in zfp.infolist():
		# 	if not "/" in item.filename and not baseFile:
		# 		contents = zfp.open(item).read()
		# 		contents = bs4.UnicodeDammit(contents).unicode_markup

		# 		baseFile = (item.filename, contents)

		# 	elif baseName in item.filename and baseName:
		# 		raise ValueError("Multiple base file items?")

		# 	else:
		# 		resources.append((item.filename, mimetypes.guess_type(item.filename)[0], zfp.open(item).read()))

		# if not baseFile:
		# 	raise ValueError("No base file found!")

		# return baseFile, resources


def makeDriveDisambiguation(urls, pageHeader):

	soup = bs4.BeautifulSoup()

	tag = soup.new_tag('h3')
	tag.string = 'Google Drive directory: %s' % pageHeader
	soup.append(tag)
	for url in urls:
		tag = soup.new_tag('a', href=url)
		tag.string = url
		soup.append(tag)
		tag = soup.new_tag('br')
		soup.append(tag)
	return soup.prettify()


def test():
	import webFunctions
	wg = webFunctions.WebGetRobust()

	# url = 'https://docs.google.com/document/d/1ljoXDy-ti5N7ZYPbzDsj5kvYFl3lEWaJ1l3Lzv1cuuM/preview'
	# url = 'https://docs.google.com/document/d/17__cAhkFCT2rjOrJN1fK2lBdpQDSO0XtZBEvCzN5jH8/preview'
	url = 'https://docs.google.com/document/d/1t4_7X1QuhiH9m3M8sHUlblKsHDAGpEOwymLPTyCfHH0/preview'

	urls = [
		'https://docs.google.com/document/d/1RrLZ-j9uS5dJPXR44VLajWrGPJl34CVfAeJ7pELPMy4',
		'https://docs.google.com/document/d/1_1e7D30N16Q1Pw6q68iCrOGhHZNhXd3C9jDrRXbXCTc',
		'https://docs.google.com/document/d/1ke-eW78CApO0EgfY_X_ZgLyEEcEQ2fH8vK_oGbhROPM',
		'https://docs.google.com/document/d/1Dl5XbPHThX6xCxhIHL9oY0zDbIuQn6fXckXQ16rECps',
		'https://docs.google.com/document/d/12UHbPduKDVjSk99VVdf5OHdaHxzN3nuIcAGrW5oV5E8',
		'https://docs.google.com/document/d/1ebJOszL08TqJw1VvyaVfO72On4rQBPca6CujSYy-McY',
		'https://docs.google.com/document/d/19vXfdmkAyLWcfV2BkgIxNawD2QwCoeFEQtV8wYwTamU',
		'https://docs.google.com/document/d/1RGqoPR6sfjJY_ZxLfQGa4YLNIW5zKj1HTWa6qmFLQfg',
		'https://docs.google.com/document/d/1TDmwoB6Y7XiPJRZ7-OGjAhEqPPbdasazn0vBbCvj8IM',
		'https://docs.google.com/document/d/1o40vXZAW6v81NlNl4o6Jvjch0GO2ETv5JgwKqXfOpOQ',
		'https://docs.google.com/document/d/1STcAhI6J9CEEx7nQFGAt_mnxfgo0fMOrb4Ls0EYWRHk',
		'https://docs.google.com/document/d/1xyyhV5yeoRTZHPCPX6yeL8BbVzybhFM27EyInFtjwZQ',
		'https://docs.google.com/document/d/11RzD2ILc1MKH5VA4jBzCDO7DIFRzUFCjAe7-MnJfDLY',
		'https://docs.google.com/document/d/1AVyCN0nXTTqVrrMaqJRUSkTP1Ksyop9H-UHWvdMB5Ps',
		'https://docs.google.com/document/d/18VaVO2VnFMo5Lv6VFZ4hP-lbX3XxHKnPu6wc2sxxA6U',
		'https://docs.google.com/document/d/1XuD5iloTWdpFAAzuSHpQuPKVwsrQeyAlT0CSFoIYk3A',
		'https://docs.google.com/document/d/1yoKoZq3DBCXLJ__1LNod_d_p6SkKC2VzQ3r-pjlOa4M',
		'https://docs.google.com/document/d/1CIJLV1CN57naLf9gG9Y6C7aZ6ieLM9uL5CGquxCNPQM',
		'https://docs.google.com/document/d/1m9yGcNhNfQRCfdcmwb4mAy2sVG3BXHjM6cBFKjzmvFw',
	]

	# print(makeDriveDisambiguation(urls))
	# parse = GDocExtractor(url)
	# base, resc = parse.extract()
	# # parse.getTitle()

	# print(GDocExtractor.getDriveFileUrls('https://drive.google.com/folderview?id=0B_mXfd95yvDfQWQ1ajNWZTJFRkk&usp=drive_web'))


	extr = GFileExtractor('https://docs.google.com/file/d/0B8UYgI2TD_nmNUMzNWJpZnJkRkU')
	extr = GFileExtractor('https://docs.google.com/file/d/0B8UYgI2TD_nmNUMzNWJpZnJkRkU/edit')
	print(extr)
	print(extr.extract())

	# with open("test.html", "wb") as fp:
	# 	fp.write(ret.encode("utf-8"))

if __name__ == "__main__":
	import logSetup
	if __name__ == "__main__":
		print("Initializing logging")
		logSetup.initLogging()

	test()




import runStatus
runStatus.preloadDicts = False

# import Levenshtein as lv

import markdown
import logging
import settings
import abc
import threading
import urllib.parse
import functools
import operator as opclass

import sql
# import sql.operators as sqlo


import hashlib
import psycopg2
import os
import traceback
import bs4
import readability.readability
import os.path
import os
from importlib.machinery import SourceFileLoader
import time
import queue
from concurrent.futures import ThreadPoolExecutor

import nameTools

from contextlib import contextmanager


import TextScrape.gDocParse as gdp

class DownloadException(Exception):
	pass

@contextmanager
def transaction(cursor, commit=True):
	if commit:
		cursor.execute("BEGIN;")

	try:
		yield

	except Exception as e:
		if commit:
			cursor.execute("ROLLBACK;")
		raise e

	finally:
		if commit:
			cursor.execute("COMMIT;")


########################################################################################################################
#
#	#### ##     ## ########   #######  ########  ########    ##        #######   #######  ##    ## ##     ## ########
#	 ##  ###   ### ##     ## ##     ## ##     ##    ##       ##       ##     ## ##     ## ##   ##  ##     ## ##     ##
#	 ##  #### #### ##     ## ##     ## ##     ##    ##       ##       ##     ## ##     ## ##  ##   ##     ## ##     ##
#	 ##  ## ### ## ########  ##     ## ########     ##       ##       ##     ## ##     ## #####    ##     ## ########
#	 ##  ##     ## ##        ##     ## ##   ##      ##       ##       ##     ## ##     ## ##  ##   ##     ## ##
#	 ##  ##     ## ##        ##     ## ##    ##     ##       ##       ##     ## ##     ## ##   ##  ##     ## ##
#	#### ##     ## ##         #######  ##     ##    ##       ########  #######   #######  ##    ##  #######  ##
#
########################################################################################################################

def rebaseUrl(url, base):
	"""Rebase one url according to base"""

	parsed = urllib.parse.urlparse(url)
	if parsed.scheme == parsed.netloc == '':
		return urllib.parse.urljoin(base, url)
	else:
		return url


def getPythonScriptModules():
	moduleDir = os.path.split(os.path.realpath(__file__))[0]


	ret = []
	moduleRoot = 'TextScrape'
	for fName in os.listdir(moduleDir):
		itemPath = os.path.join(moduleDir, fName)
		if os.path.isdir(itemPath):
			modulePath = "%s.%s" % (moduleRoot, fName)
			for fName in os.listdir(itemPath):

				# Skip files without a '.py' extension
				if not fName == "Scrape.py":
					continue

				fPath = os.path.join(itemPath, fName)
				fName = fName.split(".")[0]
				fqModuleName = "%s.%s" % (modulePath, fName)
				# Skip the __init__.py file.
				if fName == "__init__":
					continue

				ret.append((fPath, fqModuleName))

	return ret

def findPluginClass(module, prefix):

	interfaces = []
	for item in dir(module):
		if not item.startswith(prefix):
			continue

		plugClass = getattr(module, item)
		if not "plugin_type" in dir(plugClass) and plugClass.plugin_type == "TextScraper":
			continue
		if not 'tableKey' in dir(plugClass):
			continue

		interfaces.append((plugClass.tableKey, plugClass))

	return interfaces

def loadPlugins():
	modules = getPythonScriptModules()
	ret = {}

	for fPath, modName in modules:
		loader = SourceFileLoader(modName, fPath)
		mod = loader.load_module()
		plugClasses = findPluginClass(mod, 'Scrape')
		for key, pClass in plugClasses:
			if key in ret:
				raise ValueError("Two plugins providing an interface with the same name? Name: '%s'" % key)
			ret[key] = pClass
	return ret


def fetchRelinkableDomains():
	domains = set()
	pluginDict = loadPlugins()
	for plugin in pluginDict:
		plg = pluginDict[plugin]

		if isinstance(plg.baseUrl, (set, list)):
			for url in plg.baseUrl:
				url = urllib.parse.urlsplit(url.lower()).netloc
				domains.add(url)

				if url.startswith("www."):
					domains.add(url[4:])

		else:
			url = urllib.parse.urlsplit(plg.baseUrl.lower()).netloc

		domains.add(url)
		if url.startswith("www."):
			domains.add(url[4:])
		if hasattr(plg, 'scannedDomains'):
			for domain in plg.scannedDomains:
				url = urllib.parse.urlsplit(domain.lower()).netloc

				domains.add(url)
				if url.startswith("www."):
					domains.add(url[4:])

	return domains


# All tags you need to look into to do link canonization
# source: http://stackoverflow.com/q/2725156/414272
# TODO: "These aren't necessarily simple URLs ..."
urlContainingTargets = [
	('a', 'href'), ('applet', 'codebase'), ('area', 'href'), ('base', 'href'),
	('blockquote', 'cite'), ('body', 'background'), ('del', 'cite'),
	('form', 'action'), ('frame', 'longdesc'), ('frame', 'src'),
	('head', 'profile'), ('iframe', 'longdesc'), ('iframe', 'src'),
	('img', 'longdesc'), ('img', 'src'), ('img', 'usemap'), ('input', 'src'),
	('input', 'usemap'), ('ins', 'cite'), ('link', 'href'),
	('object', 'classid'), ('object', 'codebase'), ('object', 'data'),
	('object', 'usemap'), ('q', 'cite'), ('script', 'src'), ('audio', 'src'),
	('button', 'formaction'), ('command', 'icon'), ('embed', 'src'),
	('html', 'manifest'), ('input', 'formaction'), ('source', 'src'),
	('video', 'poster'), ('video', 'src'),
]


class RowExistsException(Exception):
	pass

# This whole mess is getting too hueg and clumsy. FIXME!


########################################################################################################################
#
#	##     ##    ###    #### ##    ##     ######  ##          ###     ######   ######
#	###   ###   ## ##    ##  ###   ##    ##    ## ##         ## ##   ##    ## ##    ##
#	#### ####  ##   ##   ##  ####  ##    ##       ##        ##   ##  ##       ##
#	## ### ## ##     ##  ##  ## ## ##    ##       ##       ##     ##  ######   ######
#	##     ## #########  ##  ##  ####    ##       ##       #########       ##       ##
#	##     ## ##     ##  ##  ##   ###    ##    ## ##       ##     ## ##    ## ##    ##
#	##     ## ##     ## #### ##    ##     ######  ######## ##     ##  ######   ######
#
########################################################################################################################


class TextScraper(metaclass=abc.ABCMeta):

	# Abstract class (must be subclassed)
	__metaclass__ = abc.ABCMeta

	plugin_type = 'TextScraper'

	validKwargs = []

	tableName       = "book_items"
	changeTableName = "book_changes"

	threads = 2

	QUERY_DEBUG = False
	IGNORE_MALFORMED_URLS = False
	FOLLOW_GOOGLE_LINKS = True

	@abc.abstractproperty
	def pluginName(self):
		pass

	@abc.abstractproperty
	def loggerPath(self):
		pass

	@abc.abstractproperty
	def tableKey(self):
		pass

	@abc.abstractproperty
	def baseUrl(self):
		pass
	@abc.abstractproperty
	def startUrl(self):
		pass

	@abc.abstractproperty
	def badwords(self):
		pass



	# `decompose` and `decomposeBefore` are defined in the child plugins
	decompose       = []
	decomposeBefore = []


	fileDomains     = []

	allImages       = False
	tld             = set()

	stripTitle = ''

	def __init__(self):
		# These two lines HAVE to be before ANY logging statements, or the automagic thread
		# logging context management will fail.
		self.loggers = {}
		self.lastLoggerIndex = 1

		self._tld           = set()
		self._fileDomains   = set()
		self.scannedDomains = set()


		self._badwords       = set([
			'gprofiles.js',
			'netvibes.com',
			'accounts.google.com',
			'edit.yahoo.com',
			'add.my.yahoo.com',
			'public-api.wordpress.com',
			'r-login.wordpress.com',
			'twitter.com',
			'facebook.com',
			'public-api.wordpress.com',
			'wretch.cc',
			'ws-na.amazon-adsystem.com',
			'delicious.com',
			'paypal.com',
			'digg.com',
			'topwebfiction.com',
			'/page/page/',
			'addtoany.com',
			'stumbleupon.com',
			'delicious.com',
			'reddit.com',
			'newsgator.com',
			'technorati.com',
			])

		# `_decompose` and `_decomposeBefore` are the actual arrays of items to decompose, that are loaded with the contents of
		# `decompose` and `decomposeBefore` on plugin initialization
		self._decompose       = []
		self._decomposeBefore = [
			{'name'     : 'likes-master'},  # Bullshit sharing widgets
			{'id'       : 'jp-post-flair'},
			{'class'    : 'commentlist'},  # Scrub out the comments so we don't try to fetch links from them
			{'class'    : 'post-share-buttons'},
			{'class'    : 'comments'},
			{'id'       : 'comments'},
		]

		self._relinkDomains = set()
		for url in fetchRelinkableDomains():
			self._relinkDomains.add(url)

		if isinstance(self.baseUrl, (set, list)):
			for url in self.baseUrl:
				self.scannedDomains.add(url)
				self._fileDomains.add(urllib.parse.urlsplit(url.lower()).netloc)
		else:
			self.scannedDomains.add(self.baseUrl)
			self._fileDomains.add(urllib.parse.urlsplit(self.baseUrl.lower()).netloc)

		self._scannedDomains = set()

		if self.FOLLOW_GOOGLE_LINKS:
			# Tell the path filtering mechanism that we can fetch google doc files
			self._scannedDomains.add('https://docs.google.com/document/')
			self._scannedDomains.add('https://drive.google.com/folderview')
			self._scannedDomains.add('https://drive.google.com/open')

		# Lower case all the domains, since they're not case sensitive, and it case mismatches can break matching.
		# We also extract /just/ the netloc, so http/https differences don't cause a problem.
		for url in self.scannedDomains:
			self.installBaseUrl(url)

		# Loggers are set up dynamically on first-access.
		self.log.info("TextScrape Base startup")

		# I have to wrap the DB in locks, since two pages may return
		# identical links at the same time.
		# Using transactions could result in collisions, so we lock.
		# Most of the time is spent in processing pages anyways
		self.dbLock = threading.Lock()

		self.dbConnections = {}

		self.newLinkQueue = queue.Queue()


		self.log.info("Loading %s Runner BaseClass", self.pluginName)

		self.checkInitPrimaryDb()


		# Move the plugin-defined decompose calls into the control lists
		for item in self.decompose:
			self._decompose.append(item)

		for item in self.decomposeBefore:
			self._decomposeBefore.append(item)

		for item in self.badwords:
			self._badwords.add(item)

		for item in self.fileDomains:
			self._fileDomains.add(item)

		for item in self.tld:
			self._tld.add(item)

		tmp = list(self._scannedDomains)
		tmp.sort()
		for url in tmp:
			self.log.info("Scanned domain:		%s", url)


	# More hackiness to make sessions intrinsically thread-safe.
	def __getattribute__(self, name):

		threadName = threading.current_thread().name
		if name == "log":
			if "Thread-" in threadName:
				if threadName not in self.loggers:
					self.loggers[threadName] = logging.getLogger("%s.Thread-%d" % (self.loggerPath, self.lastLoggerIndex))
					self.lastLoggerIndex += 1

			# If we're not called in the context of a thread, just return the base log-path
			else:
				self.loggers[threadName] = logging.getLogger("%s" % (self.loggerPath,))


			return self.loggers[threadName]


		elif name == "conn":
			if threadName not in self.dbConnections:

				# First try local socket connection, fall back to a IP-based connection.
				# That way, if the server is local, we get the better performance of a local socket.
				try:
					self.dbConnections[threadName] = psycopg2.connect(dbname=settings.DATABASE_DB_NAME, user=settings.DATABASE_USER,password=settings.DATABASE_PASS)
				except psycopg2.OperationalError:
					self.dbConnections[threadName] = psycopg2.connect(host=settings.DATABASE_IP, dbname=settings.DATABASE_DB_NAME, user=settings.DATABASE_USER,password=settings.DATABASE_PASS)

				# self.dbConnections[threadName].autocommit = True
			return self.dbConnections[threadName]



		else:
			return object.__getattribute__(self, name)



	def installBaseUrl(self, url):
		netloc = urllib.parse.urlsplit(url.lower()).netloc
		if not netloc:
			raise ValueError("One of the scanned domains collapsed down to an empty string: '%s'!" % url)

		# Generate the possible wordpress netloc values.
		if 'wordpress.com' in netloc:
			subdomain, mainDomain, tld = netloc.rsplit(".")[-3:]

			self._scannedDomains.add("www.{sub}.{main}.{tld}".format(sub=subdomain, main=mainDomain, tld=tld))
			self._scannedDomains.add("{sub}.{main}.{tld}".format(sub=subdomain, main=mainDomain, tld=tld))
			self._scannedDomains.add("www.{sub}.files.{main}.{tld}".format(sub=subdomain, main=mainDomain, tld=tld))
			self._scannedDomains.add("{sub}.files.{main}.{tld}".format(sub=subdomain, main=mainDomain, tld=tld))

		# Blogspot is annoying and sometimes a single site is spread over several tlds. *.com, *.sg, etc...
		if 'blogspot.' in netloc:
			subdomain, mainDomain, tld = netloc.rsplit(".")[-3:]
			self._tld.add(tld)
			for tld in self._tld:
				self._scannedDomains.add("www.{sub}.{main}.{tld}".format(sub=subdomain, main=mainDomain, tld=tld))
				self._scannedDomains.add("{sub}.{main}.{tld}".format(sub=subdomain, main=mainDomain, tld=tld))

				self._fileDomains.add('bp.blogspot.{tld}'.format(tld=tld))


		if 'sites.google.com/site/' in url:
			self._scannedDomains.add(url)

		elif 'google.' in netloc:
			self.log.info("Skipping URL: '%s'", url)

		else:
			self._scannedDomains.add(netloc)




	########################################################################################################################
	#
	#	 ######   ######  ########     ###    ########  #### ##    ##  ######      ######## ##     ## ##    ##  ######  ######## ####  #######  ##    ##  ######
	#	##    ## ##    ## ##     ##   ## ##   ##     ##  ##  ###   ## ##    ##     ##       ##     ## ###   ## ##    ##    ##     ##  ##     ## ###   ## ##    ##
	#	##       ##       ##     ##  ##   ##  ##     ##  ##  ####  ## ##           ##       ##     ## ####  ## ##          ##     ##  ##     ## ####  ## ##
	#	 ######  ##       ########  ##     ## ########   ##  ## ## ## ##   ####    ######   ##     ## ## ## ## ##          ##     ##  ##     ## ## ## ##  ######
	#	      ## ##       ##   ##   ######### ##         ##  ##  #### ##    ##     ##       ##     ## ##  #### ##          ##     ##  ##     ## ##  ####       ##
	#	##    ## ##    ## ##    ##  ##     ## ##         ##  ##   ### ##    ##     ##       ##     ## ##   ### ##    ##    ##     ##  ##     ## ##   ### ##    ##
	#	 ######   ######  ##     ## ##     ## ##        #### ##    ##  ######      ##        #######  ##    ##  ######     ##    ####  #######  ##    ##  ######
	#
	########################################################################################################################



	def urlClean(self, url):
		# Google docs can be accessed with or without the '/preview' postfix
		# We want to remove this if it's present, so we don't duplicate content.
		url = gdp.trimGDocUrl(url)

		while True:
			url2 = urllib.parse.unquote(url)
			url2 = url2.split("#")[0]
			if url2 == url:
				break
			url = url2

		# Clean off whitespace.
		url = url.strip()

		return url

	def getItem(self, itemUrl):

		content, handle = self.wg.getpage(itemUrl, returnMultiple=True)
		if not content or not handle:
			raise ValueError("Failed to retreive file from page '%s'!" % itemUrl)

		fileN = urllib.parse.unquote(urllib.parse.urlparse(handle.geturl())[2].split("/")[-1])
		fileN = bs4.UnicodeDammit(fileN).unicode_markup
		mType = handle.info()['Content-Type']

		# If there is an encoding in the content-type (or any other info), strip it out.
		# We don't care about the encoding, since WebFunctions will already have handled that,
		# and returned a decoded unicode object.

		if mType and ";" in mType:
			mType = mType.split(";")[0].strip()


		self.log.info("Retreived file of type '%s', name of '%s' with a size of %0.3f K", mType, fileN, len(content)/1000.0)
		return content, fileN, mType

	# Hook so plugins can modify the internal URLs as part of the relinking process
	def preprocessReaderUrl(self, inUrl):
		return inUrl


	def convertToReaderUrl(self, inUrl):
		inUrl = self.urlClean(inUrl)
		inUrl = self.preprocessReaderUrl(inUrl)
		# The link will have been canonized at this point
		url = '/books/render?url=%s' % urllib.parse.quote(inUrl)
		return url

	# check if domain `url` is a sub-domain of the scanned domains.
	def checkDomain(self, url):
		# if "drive" in url:
		for rootUrl in self._scannedDomains:
			if urllib.parse.urlsplit(url).netloc:
				if urllib.parse.urlsplit(url).netloc == rootUrl:
					return True

			elif url.lower().startswith(rootUrl):
				return True

		# print("CheckDomain False", url)
		return False

	def checkFollowGoogleUrl(self, url):
		'''
		I don't want to scrape outside of the google doc document context.

		Therefore, if we have a URL that's on docs.google.com, and doesn't have
		'/document/d/ in the URL, block it.
		'''
		# Short circuit for non docs domains
		url = url.lower()
		netloc = urllib.parse.urlsplit(url).netloc
		if not "docs.google.com" in netloc:
			return True

		if '/document/d/' in url:
			return True

		return False


	# check if domain `url` is a sub-domain of the domains we should relink.
	def checkRelinkDomain(self, url):
		# if "drive" in url:
		# 	print("CheckDomain", any([rootUrl in url.lower() for rootUrl in self._scannedDomains]), url)
		return any([rootUrl in url.lower() for rootUrl in self._relinkDomains])


	def processLinkItem(self, url, baseUrl):


		url = gdp.clearOutboundProxy(url)
		url = gdp.clearBitLy(url)



		# Filter by domain
		if not self.checkDomain(url):
			# print("Filtering", self.checkDomain(url), url)
			return


		# and by blocked words
		hadbad = False
		for badword in self._badwords:
			if badword in url:
				hadbad = True
		if hadbad:

			# print("hadbad", self.checkDomain(url), url)
			return


		if not self.checkFollowGoogleUrl(url):
			return

		url = self.urlClean(url)

		if "google.com" in urllib.parse.urlsplit(url.lower()).netloc:
			url = gdp.trimGDocUrl(url)

			if url.startswith('https://docs.google.com/document/d/images'):
				return

			# self.log.info("Resolved URL = '%s'", url)
			self.putNewUrl(url, baseUrl)
			# self.log.info("New G link: '%s'", url)

		else:
			# Remove any URL fragments causing multiple retreival of the same resource.
			if url != gdp.trimGDocUrl(url):
				print('Old URL: "%s"' % url)
				print('Trimmed: "%s"' % gdp.trimGDocUrl(url))
				raise ValueError("Wat? Url change? Url: '%s'" % url)
			self.putNewUrl(url, baseUrl)
			# self.log.info("Newlink: '%s'", url)

	def extractLinks(self, soup, baseUrl):
		# All links have been resolved to fully-qualified paths at this point.


		for (tag, attr) in urlContainingTargets:

			for link in soup.findAll(tag):


				# Skip empty anchor tags
				try:
					url = link[attr]
				except KeyError:
					continue


				self.processLinkItem(url, baseUrl)


	def extractImages(self, soup, baseUrl):

		for imtag in soup.find_all("img"):
						# Skip empty anchor tags
			try:
				url = imtag["src"]
			except KeyError:
				continue

			# Skip tags with `img src=""`.
			# No idea why they're there, but they are
			if not url:
				continue

			# Filter by domain
			if not self.allImages and not any([base in url for base in self._fileDomains]):
				continue

			# and by blocked words
			hadbad = False
			for badword in self._badwords:
				if badword in url:
					hadbad = True
			if hadbad:
				continue


			# upsert for `url`. Do not reset dlstate to avoid re-transferring binary files.
			url = self.urlClean(url)

			self.putNewUrl(url, baseUrl=baseUrl, istext=False)


	def convertToReaderImage(self, inStr):
		inStr = self.urlClean(inStr)
		return self.convertToReaderUrl(inStr)

	def relink(self, soup, imRelink=None):
		# The google doc reader relinking mechanisms requires overriding the
		# image relinking mechanism. As such, allow that to be overridden
		# if needed

		# TODO: Convert this to use list of all tags with src attributes.

		if not imRelink:
			imRelink = self.convertToReaderImage

		# print("Image relinker:", imRelink)

		for aTag in soup.find_all("a"):
			try:
				if self.checkRelinkDomain(aTag["href"]):
					aTag["href"] = self.convertToReaderUrl(aTag["href"])
			except KeyError:
				continue

		for imtag in soup.find_all("img"):
			try:
				imtag["src"] = imRelink(imtag["src"])
				# print("New image URL", imtag['src'])

				# Force images that are oversize to fit the window.
				imtag["style"] = 'max-width: 95%;'

				if 'width' in imtag.attrs:
					del imtag.attrs['width']
				if 'height' in imtag.attrs:
					del imtag.attrs['height']

			except KeyError:
				continue

		return soup



	def getFilenameFromIdName(self, rowid, filename):
		if not os.path.exists(settings.bookCachePath):
			self.log.warn("Cache directory for book items did not exist. Creating")
			self.log.warn("Directory at path '%s'", settings.bookCachePath)
			os.makedirs(settings.bookCachePath)

		# one new directory per 1000 items.
		dirName = '%s' % (rowid // 1000)
		dirPath = os.path.join(settings.bookCachePath, dirName)
		if not os.path.exists(dirPath):
			os.mkdir(dirPath)

		filename = 'ID%s - %s' % (rowid, filename)
		filename = nameTools.makeFilenameSafe(filename)
		fqpath = os.path.join(dirPath, filename)

		return fqpath



	def canonizeUrls(self, soup, pageUrl):
		self.log.info("Making all links on page absolute.")

		for (tag, attr) in urlContainingTargets:
			for link in soup.findAll(tag):
				try:
					url = link[attr]
				except KeyError:
					pass
				else:
					link[attr] = rebaseUrl(url, pageUrl)
					if link[attr] != url:
						self.log.debug("Changed URL from '%s' to '%s'", url, link[attr])
		return soup


	def decomposeItems(self, soup, toDecompose):
		# Decompose all the parts we don't want
		for key in toDecompose:
			for instance in soup.find_all(True, attrs=key):

				# So.... yeah. At least one blogspot site has EVERY class used in the
				# <body> tag, for no coherent reason. Therefore, *never* decompose the <body>
				# tag, even if it has a bad class in it.
				if instance.name == 'body':
					continue

				instance.decompose() # This call permutes the tree!

		return soup

	def decomposeAdditional(self, soup):

		# Clear out all the iframes
		for instance in soup.find_all('iframe'):
			instance.decompose()

		# Clean out any local stylesheets
		for instance in soup.find_all('style'):
			instance.decompose()

		return soup

	def cleanHtmlPage(self, srcSoup, url=None):

		# since readability strips tag attributes, we preparse with BS4,
		# parse with readability, and then do reformatting *again* with BS4
		# Yes, this is ridiculous.

		ctnt = srcSoup.prettify()
		doc = readability.readability.Document(ctnt)
		doc.parse()
		content = doc.content()

		soup = bs4.BeautifulSoup(content)
		soup = self.relink(soup)
		contents = ''



		# Since the content we're extracting will be embedded into another page, we want to
		# strip out the <body> and <html> tags. `unwrap()`  replaces the soup with the contents of the
		# tag it's called on. We end up with just the contents of the <body> tag.
		soup.body.unwrap()
		contents = soup.prettify()

		title = self.extractTitle(soup, doc, url)

		if isinstance(self.stripTitle, (list, set)):
			for stripTitle in self.stripTitle:
				title = title.replace(stripTitle, "")
		else:
			title = title.replace(self.stripTitle, "")

		title = title.strip()
		return title, contents

	# Methods to allow the child-class to modify the content at various points.
	def extractTitle(self, srcSoup, doc, url):
		title = doc.title()
		return title

	def postprocessBody(self, soup):
		return soup

	def preprocessBody(self, soup):
		return soup


	# Process a plain HTML page.
	# This call does a set of operations to permute and clean a HTML page.
	#
	# First, it decomposes all tags with attributes dictated in the `_decomposeBefore` class variable
	# it then canonizes all the URLs on the page, extracts all the URLs from the page,
	# then decomposes all the tags in the `decompose` class variable, feeds the content through
	# readability, and finally saves the processed HTML into the database
	def processHtmlPage(self, url, content, mimeType):
		self.log.info("Processing '%s' as HTML.", url)
		soup = bs4.BeautifulSoup(content)


		# Allow child-class hooking
		soup = self.preprocessBody(soup)

		# Clear out any particularly obnoxious content before doing any parsing.
		soup = self.decomposeItems(soup, self._decomposeBefore)

		# Make all the page URLs fully qualified, so they're unambiguous
		soup = self.canonizeUrls(soup, url)

		# Conditionally pull out the page content and enqueue it.
		if self.checkDomain(url):
			self.extractLinks(soup, url)
			self.extractImages(soup, url)
		else:
			self.log.warn("Not extracting images or links for url '%s'", url)

		# Do the later cleanup to prep the content for local rendering.
		soup = self.decomposeItems(soup, self._decompose)

		soup = self.decomposeAdditional(soup)

		# Allow child-class hooking
		soup = self.postprocessBody(soup)

		# Process page with readability, extract title.
		pgTitle, pgBody = self.cleanHtmlPage(soup, url=url)
		self.log.info("Page with title '%s' retreived.", pgTitle)
		self.updateDbEntry(url=url, title=pgTitle, contents=pgBody, mimetype=mimeType, dlstate=2)


	# Format a text-file using markdown to make it actually nice to look at.
	def processAsMarkdown(self, content, url):
		self.log.info("Plain-text file. Processing with markdown.")
		# Take the first non-empty line, and just assume it's the title. It'll be close enough.
		title = content.strip().split("\n")[0].strip()
		content = markdown.markdown(content)

		self.updateDbEntry(url=url, title=title, contents=content, mimetype='text/html', dlstate=2)



	def retreivePlainResource(self, url):
		self.log.info("Fetching Simple Resource: '%s'", url)
		try:
			content, fName, mimeType = self.getItem(url)
		except ValueError:

			for line in traceback.format_exc().split("\n"):
				self.log.critical(line)
			self.upsert(url, dlstate=-1, contents='Error downloading!')
			return

		self.dispatchContent(url, content, fName, mimeType)


	########################################################################################################################
	#
	#	##     ## #### ##     ## ########         ######## ##    ## ########  ########
	#	###   ###  ##  ###   ### ##                  ##     ##  ##  ##     ## ##
	#	#### ####  ##  #### #### ##                  ##      ####   ##     ## ##
	#	## ### ##  ##  ## ### ## ######   #######    ##       ##    ########  ######
	#	##     ##  ##  ##     ## ##                  ##       ##    ##        ##
	#	##     ##  ##  ##     ## ##                  ##       ##    ##        ##
	#	##     ## #### ##     ## ########            ##       ##    ##        ########
	#
	#	########  ####  ######  ########     ###    ########  ######  ##     ## ######## ########
	#	##     ##  ##  ##    ## ##     ##   ## ##      ##    ##    ## ##     ## ##       ##     ##
	#	##     ##  ##  ##       ##     ##  ##   ##     ##    ##       ##     ## ##       ##     ##
	#	##     ##  ##   ######  ########  ##     ##    ##    ##       ######### ######   ########
	#	##     ##  ##        ## ##        #########    ##    ##       ##     ## ##       ##   ##
	#	##     ##  ##  ##    ## ##        ##     ##    ##    ##    ## ##     ## ##       ##    ##
	#	########  ####  ######  ##        ##     ##    ##     ######  ##     ## ######## ##     ##
	#
	########################################################################################################################

	def dispatchContent(self, url, content, fName, mimeType):
		self.log.info("Dispatching file '%s' with mime-type '%s'", fName, mimeType)
		if mimeType == 'text/html':
			self.processHtmlPage(url, content, mimeType)

		elif mimeType in ['text/plain']:
			self.processAsMarkdown(content, url)

		elif mimeType in ['text/xml', 'text/atom+xml', 'application/xml']:
			self.log.info("XML File?")
			self.log.info("URL: '%s'", url)
			self.updateDbEntry(url=url, title='', contents=content, mimetype=mimeType, dlstate=2, istext=True)


		elif mimeType in ['text/css']:
			self.log.info("CSS!")
			self.log.info("URL: '%s'", url)
			self.updateDbEntry(url=url, title='', contents=content, mimetype=mimeType, dlstate=2, istext=True)

		elif mimeType in ['application/x-javascript', 'application/javascript']:
			self.log.info("Javascript Resource!")
			self.log.info("URL: '%s'", url)
			self.updateDbEntry(url=url, title='', contents=content, mimetype=mimeType, dlstate=2, istext=True)

		elif mimeType in ["image/gif", "image/jpeg", "image/pjpeg", "image/png", "image/svg+xml", "image/vnd.djvu"]:
			self.log.info("Processing '%s' as an image file.", url)
			self.saveFile(url, mimeType, fName, content)

		elif mimeType in ["application/octet-stream", "application/x-mobipocket-ebook", "application/pdf", "application/zip"]:
			self.log.info("Processing '%s' as an binary file.", url)
			self.saveFile(url, mimeType, fName, content)

		else:
			self.log.warn("Unknown MIME Type? '%s', Url: '%s'", mimeType, url)



	########################################################################################################################
	#
	#	 ######    #######   #######   ######   ##       ########    ########   #######   ######   ######
	#	##    ##  ##     ## ##     ## ##    ##  ##       ##          ##     ## ##     ## ##    ## ##    ##
	#	##        ##     ## ##     ## ##        ##       ##          ##     ## ##     ## ##       ##
	#	##   #### ##     ## ##     ## ##   #### ##       ######      ##     ## ##     ## ##        ######
	#	##    ##  ##     ## ##     ## ##    ##  ##       ##          ##     ## ##     ## ##             ##
	#	##    ##  ##     ## ##     ## ##    ##  ##       ##          ##     ## ##     ## ##    ## ##    ##
	#	 ######    #######   #######   ######   ######## ########    ########   #######   ######   ######
	#
	########################################################################################################################


	def processGdocResources(self, resources):

		self.fMap = {}


		for fName, mimeType, content in resources:
			m = hashlib.md5()
			m.update(content)
			fHash = m.hexdigest()

			hashName = self.tableKey+fHash

			self.fMap[fName] = fHash

			fName = os.path.split(fName)[-1]

			self.log.info("Resource = '%s', '%s', '%s'", fName, mimeType, hashName)
			if mimeType in ["image/gif", "image/jpeg", "image/pjpeg", "image/png", "image/svg+xml", "image/vnd.djvu"]:
				self.log.info("Processing resource '%s' as an image file. (mimetype: %s)", fName, mimeType)
				self.upsert(hashName, istext=False)
				self.saveFile(hashName, mimeType, fName, content)
			elif mimeType in ["application/octet-stream"]:
				self.log.info("Processing '%s' as an binary file.", fName)
				self.upsert(hashName, istext=False)
				self.saveFile(hashName, mimeType, fName, content)
			else:
				self.log.warn("Unknown MIME Type? '%s', FileName: '%s'", mimeType, fName)

		if len(resources) == 0:
			self.log.info("File had no resource content!")



	def cleanGdocPage(self, soup):

		title = soup.title.get_text().strip()

		for span in soup.find_all("span"):
			span['style'] = ''

		return title, soup



	# Hook so plugins can modify the internal URLs as part of the relinking process
	def preprocessGdocReaderUrl(self, inUrl):
		if inUrl.lower().endswith("/preview"):
			inUrl = inUrl[:-len("/preview")]

		return inUrl


	def convertToGdocReaderImage(self, srcUrl):

		itemHash = None
		for rscEnd in self.fMap:
			if srcUrl.endswith(rscEnd):
				itemHash = self.fMap[rscEnd]

		# if srcUrl in self.fMap:
		# 	url = self.fMap[srcUrl]
		# elif any([fUrl in url for fUrl in self.fMap]):
		# 	print('wat')
		# 	raise ValueError("Unknown image URL! = '%s'" % url)
		if not itemHash:
			raise ValueError("Unknown image URL! = '%s' (hash '%s')" % (srcUrl, itemHash))

		url = '/books/render?mdsum=%s' % urllib.parse.quote(itemHash)

		return url



	def processGdocPage(self, url, content):
		dummy_fName, content = content
		print("Page size: ", len(content))
		soup = bs4.BeautifulSoup(content)
		self.canonizeUrls(soup, url)

		pgTitle, soup = self.cleanGdocPage(soup)

		self.extractLinks(soup, url)
		self.log.info("Page title = '%s'", pgTitle)
		soup = self.relink(soup, imRelink=self.convertToGdocReaderImage)

		url = self.preprocessGdocReaderUrl(url)
		url = gdp.trimGDocUrl(url)
		# Since the content we're extracting will be embedded into another page, we want to
		# strip out the <body> and <html> tags. `unwrap()`  replaces the soup with the contents of the
		# tag it's called on. We end up with just the contents of the <body> tag.
		soup.body.unwrap()
		pgBody = soup.prettify()

		self.updateDbEntry(url=url, title=pgTitle, contents=pgBody, mimetype='text/html', dlstate=2)




	def retreiveGoogleDoc(self, url):


		self.log.info("Should fetch google doc at '%s'", url)
		doc = gdp.GDocExtractor(url)



		attempts = 0

		mainPage = None
		while 1:
			attempts += 1
			try:
				mainPage, resources = doc.extract()
			except TypeError:
				self.log.critical('Extracting item failed!')
				for line in traceback.format_exc().strip().split("\n"):
					self.log.critical(line.strip())


				url = gdp.trimGDocUrl(url)
				if not url.endswith("/pub"):
					url = url+"/pub"
				self.log.info("Attempting to access as plain content instead.")
				url = self.urlClean(url)
				self.putNewUrl(url)
				return
			if mainPage:
				break
			if attempts > 3:
				raise DownloadException

		self.processGdocResources(resources)

		self.processGdocPage(url, mainPage)

	def retreiveGoogleFile(self, url):


		self.log.info("Should fetch google file at '%s'", url)
		doc = gdp.GFileExtractor(url)

		attempts = 0

		while 1:
			attempts += 1
			try:
				content, fName, mType = doc.extract()
			except TypeError:
				self.log.critical('Extracting item failed!')
				for line in traceback.format_exc().strip().split("\n"):
					self.log.critical(line.strip())

				if not url.endswith("/pub"):
					url = url+"/pub"

				self.log.info("Attempting to access as plain content instead.")
				url = self.urlClean(url)
				url = gdp.trimGDocUrl(url)
				self.putNewUrl(url)
				return
			if content:
				break
			if attempts > 3:
				raise DownloadException


			self.log.error("No content? Retrying!")

		self.dispatchContent(url, content, fName, mType)


	def extractGoogleDriveFolder(self, driveUrl):
		'''
		Extract all the relevant links from a google drive directory, and push them into
		the queued URL queue.

		'''

		docReferences, pgTitle = gdp.GDocExtractor.getDriveFileUrls(driveUrl)
		# print('docReferences', docReferences)
		for dummy_title, url in docReferences:
			url = gdp.trimGDocUrl(url)
			self.putNewUrl(url)

		self.log.info("Generating google drive disambiguation page!")
		soup = gdp.makeDriveDisambiguation(docReferences, pgTitle)
		# print(disamb)

		soup = self.relink(soup)

		disamb = soup.prettify()

		self.updateDbEntry(url=driveUrl, title=pgTitle, contents=disamb, mimetype='text/html', dlstate=2)


		self.log.info("Found %s items in google drive directory", len(docReferences))



	def putNewUrl(self, url, baseUrl=None, istext=True):
		if not url.lower().startswith("http"):
			if baseUrl:
				# If we have a base-url to extract the scheme from, we pull that out, concatenate
				# it onto the rest of the url segments, and then unsplit that back into a full URL
				scheme = urllib.parse.urlsplit(baseUrl.lower()).scheme
				rest = urllib.parse.urlsplit(baseUrl.lower())[1:]
				params = (scheme, ) + rest

				# self.log.info("Had to add scheme (%s) to URL: '%s'", scheme, url)
				url = urllib.parse.urlunsplit(params)

			elif self.IGNORE_MALFORMED_URLS:
				self.log.error("Skipping a malformed URL!")
				self.log.error("Bad URL: '%s'", url)
				return
			else:
				raise ValueError("Url isn't a url: '%s'" % url)
		if gdp.isGdocUrl(url) or gdp.isGFileUrl(url):
			if gdp.trimGDocUrl(url) != url:
				raise ValueError("Invalid link crept through! Link: '%s'" % url)


		if not url.lower().startswith('http'):
			raise ValueError("Failure adding scheme to URL: '%s'" % url)

		if not self.checkDomain(url) and istext:
			raise ValueError("Invalid url somehow got through: '%s'" % url)

		if '/view/export?format=zip' in url:
			raise ValueError("Wat?")
		self.newLinkQueue.put((url, istext))





	########################################################################################################################
	#
	#	########    ###     ######  ##    ##    ########  ####  ######  ########     ###    ########  ######  ##     ## ######## ########
	#	   ##      ## ##   ##    ## ##   ##     ##     ##  ##  ##    ## ##     ##   ## ##      ##    ##    ## ##     ## ##       ##     ##
	#	   ##     ##   ##  ##       ##  ##      ##     ##  ##  ##       ##     ##  ##   ##     ##    ##       ##     ## ##       ##     ##
	#	   ##    ##     ##  ######  #####       ##     ##  ##   ######  ########  ##     ##    ##    ##       ######### ######   ########
	#	   ##    #########       ## ##  ##      ##     ##  ##        ## ##        #########    ##    ##       ##     ## ##       ##   ##
	#	   ##    ##     ## ##    ## ##   ##     ##     ##  ##  ##    ## ##        ##     ##    ##    ##    ## ##     ## ##       ##    ##
	#	   ##    ##     ##  ######  ##    ##    ########  ####  ######  ##        ##     ##    ##     ######  ##     ## ######## ##     ##
	#
	########################################################################################################################

	# This is the main function that's called by the task management system.
	# Retreive remote content at `url`, call the appropriate handler for the
	# transferred content (e.g. is it an image/html page/binary file)
	def dispatchUrlRequest(self, url):

		url = self.urlClean(url)
		# Snip off leading slashes that have shown up a few times.
		if url.startswith("//"):
			url = 'http://'+url[2:]

		# print('Dispatch URL', url)

		netloc = urllib.parse.urlsplit(url.lower()).netloc

		isGdoc, realUrl = gdp.isGdocUrl(url)
		isGfile, fileUrl = gdp.isGFileUrl(url)
		if 'drive.google.com' in netloc:
			self.log.info("Google Drive content!")
			self.extractGoogleDriveFolder(url)
		elif isGdoc:
			self.log.info("Google Docs content!")
			self.retreiveGoogleDoc(realUrl)

		elif isGfile:
			self.log.info("Google File content!")
			self.retreiveGoogleFile(realUrl)

		else:
			self.retreivePlainResource(url)

	########################################################################################################################
	#
	#	########  ########   #######   ######  ########  ######   ######      ######   #######  ##    ## ######## ########   #######  ##
	#	##     ## ##     ## ##     ## ##    ## ##       ##    ## ##    ##    ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##
	#	##     ## ##     ## ##     ## ##       ##       ##       ##          ##       ##     ## ####  ##    ##    ##     ## ##     ## ##
	#	########  ########  ##     ## ##       ######    ######   ######     ##       ##     ## ## ## ##    ##    ########  ##     ## ##
	#	##        ##   ##   ##     ## ##       ##             ##       ##    ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##
	#	##        ##    ##  ##     ## ##    ## ##       ##    ## ##    ##    ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##
	#	##        ##     ##  #######   ######  ########  ######   ######      ######   #######  ##    ##    ##    ##     ##  #######  ########
	#
	########################################################################################################################

	def queueLoop(self):
		self.log.info("Fetch thread starting")

		# Timeouts is used to track when queues are empty
		# Since I have multiple threads, and there are known
		# situations where we can be certain that there will be
		# only one request (such as at startup), we need to
		# have a mechanism for retrying fetches from a queue a few
		# times before concluding there is nothing left to do
		timeouts = 0
		while runStatus.run:
			try:
				url = self.getToDo()
				if url:

					try:
						self.dispatchUrlRequest(url)
					except urllib.error.URLError:
						content = "DOWNLOAD FAILED"
						content += "<br>"
						content += traceback.format_exc()
						self.upsert(url, dlstate=-1, contents=content)
					except DownloadException:
						content = "DOWNLOAD FAILED"
						content += "<br>"
						content += traceback.format_exc()
						self.upsert(url, dlstate=-1, contents=content)


				else:
					timeouts += 1
					time.sleep(1)
					self.log.info("Fetch task waiting.")

				if timeouts > 5:
					break

			except Exception:
				traceback.print_exc()
		self.log.info("Fetch thread exiting!")

	def crawl(self):

		self.resetStuckItems()

		if hasattr(self, 'preFlight'):
			self.preFlight()

		haveUrls = set()
		if isinstance(self.startUrl, (list, set)):
			for url in self.startUrl:
				self.log.info("Start URL: '%s'", url)
				self.upsert(url, dlstate=0)
		else:
			self.upsert(self.startUrl, dlstate=0)

		with ThreadPoolExecutor(max_workers=self.threads) as executor:

			processes = []
			for dummy_x in range(self.threads):
				self.log.info("Starting child-thread!")
				processes.append(executor.submit(self.queueLoop))


			while runStatus.run:
				try:
					got = self.newLinkQueue.get_nowait()
					if not got:
						continue
					if len(got) == 2:
						url, istext = got
						if not url in haveUrls:

							if url.lower().startswith('http'):
								self.log.info("New URL: '%s'", url)

								# Only reset the downloadstate for content, not
								# resources
								if istext:
									self.upsert(url, istext=istext, dlstate=0)
								else:
									self.upsert(url, istext=istext)
								haveUrls.add(url)
							else:
								raise ValueError("Invalid URL added: '%s'", got)
					else:
						raise ValueError("Data from queue is not a 2-tuple? '%s'" % got)

				except queue.Empty:
					time.sleep(0.01)




				if not any([proc.running() for proc in processes]):
					self.log.info("All threads stopped. Main thread exiting.")
					break
			if not runStatus.run:
				self.log.warn("Execution stopped because of user-interrupt!")

		self.log.info("Crawler scanned a total of '%s' pages", len(haveUrls))
		self.log.info("Queue Feeder thread exiting!")



	##############################################################################################################################################
	#
	#
	#	 ######   ######  ##     ## ######## ##     ##    ###       ########  ######## ######## #### ##    ## #### ######## ####  #######  ##    ##
	#	##    ## ##    ## ##     ## ##       ###   ###   ## ##      ##     ## ##       ##        ##  ###   ##  ##     ##     ##  ##     ## ###   ##
	#	##       ##       ##     ## ##       #### ####  ##   ##     ##     ## ##       ##        ##  ####  ##  ##     ##     ##  ##     ## ####  ##
	#	 ######  ##       ######### ######   ## ### ## ##     ##    ##     ## ######   ######    ##  ## ## ##  ##     ##     ##  ##     ## ## ## ##
	#	      ## ##       ##     ## ##       ##     ## #########    ##     ## ##       ##        ##  ##  ####  ##     ##     ##  ##     ## ##  ####
	#	##    ## ##    ## ##     ## ##       ##     ## ##     ##    ##     ## ##       ##        ##  ##   ###  ##     ##     ##  ##     ## ##   ###
	#	 ######   ######  ##     ## ######## ##     ## ##     ##    ########  ######## ##       #### ##    ## ####    ##    ####  #######  ##    ##
	#
	#
	##############################################################################################################################################

	def checkInitPrimaryDb(self):
		with self.conn.cursor() as cur:

			cur.execute('''CREATE TABLE IF NOT EXISTS {tableName} (
												dbid      SERIAL PRIMARY KEY,
												src       TEXT NOT NULL,
												dlstate   INTEGER DEFAULT 0,
												url       CITEXT UNIQUE NOT NULL,

												title     text,
												series    CITEXT,
												contents  text,
												istext    boolean DEFAULT TRUE,
												fhash     CITEXT,
												mimetype  CITEXT,
												fspath    text DEFAULT '',
												netloc    CITEXT);'''.format(tableName=self.tableName))



			cur.execute('''CREATE TABLE IF NOT EXISTS {tableName} (
												dbid       SERIAL PRIMARY KEY,
												src        TEXT NOT NULL,
												url        CITEXT NOT NULL,
												change     real NOT NULL,
												title      text,
												changeDate double precision NOT NULL
												);'''.format(tableName=self.changeTableName))


			cur.execute("SELECT relname FROM pg_class;")
			haveIndexes = cur.fetchall()
			haveIndexes = [index[0] for index in haveIndexes]

			indexes = [
				("%s_source_index"     % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (src     );'''  ),
				("%s_istext_index"     % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (istext  );'''  ),
				("%s_dlstate_index"    % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (dlstate );'''  ),
				("%s_url_index"        % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (url     );'''  ),
				("%s_title_index"      % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (title   );'''  ),
				("%s_fhash_index"      % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (fhash   );'''  ),
				("%s_title_coll_index" % self.tableName, self.tableName, '''CREATE INDEX %s ON %s USING BTREE (title COLLATE "en_US" text_pattern_ops);'''  ),


				("%s_date_index"       % self.changeTableName, self.changeTableName, '''CREATE INDEX %s ON %s (changeDate);''' ),
				("%s_src_index"        % self.changeTableName, self.changeTableName, '''CREATE INDEX %s ON %s (src   );'''     ),
				("%s_url_index"        % self.changeTableName, self.changeTableName, '''CREATE INDEX %s ON %s (url   );'''     ),
				("%s_change_index"     % self.changeTableName, self.changeTableName, '''CREATE INDEX %s ON %s (change   );'''  ),
				("%s_netloc_index"     % self.changeTableName, self.changeTableName, '''CREATE INDEX %s ON %s (change   );'''  ),
				("%s_title_trigram"    % self.changeTableName, self.changeTableName, '''CREATE INDEX %s ON %s USING gin (title gin_trgm_ops);'''  ),
			]

		# CREATE INDEX book_series_name_trigram ON book_series USING gin (itemname gin_trgm_ops);
		# CREATE INDEX book_title_trigram ON book_items USING gin (title gin_trgm_ops);

		# ALTER INDEX book_title_trigram RENAME TO book_items_title_trigram;

		# CREATE INDEX  book_items_title_coll_index ON book_items USING BTREE (title COLLATE "en_US" text_pattern_ops);
		# CREATE INDEX  book_items_fhash_index ON book_items (fhash);

		# CREATE INDEX title_collate_index ON book_items USING BTREE (title COLLATE "en_US" text_pattern_ops);
		# EXPLAIN ANALYZE SELECT COUNT(*) FROM book_items WHERE title LIKE 's%';


			for name, table, nameFormat in indexes:
				if not name.lower() in haveIndexes:
					cur.execute(nameFormat % (name, table))

		self.conn.commit()
		self.log.info("Retreived page database created")

		self.validKwargs = ['dbid', 'src', 'dlstate', 'url', 'title', 'series', 'contents', 'istext', 'fhash', 'mimetype', 'fspath']


		self.table = sql.Table(self.tableName.lower())

		self.cols = (
				self.table.dbid,
				self.table.src,
				self.table.dlstate,
				self.table.url,
				self.table.netloc,
				self.table.title,
				self.table.series,
				self.table.contents,
				self.table.istext,
				self.table.fhash,
				self.table.mimetype,
				self.table.fspath
			)


		self.colMap = {
				"dbid"       : self.table.dbid,
				"src"        : self.table.src,
				"dlstate"    : self.table.dlstate,
				"url"        : self.table.url,
				"netloc"        : self.table.netloc,
				"title"      : self.table.title,
				"series"     : self.table.series,
				"contents"   : self.table.contents,
				"istext"     : self.table.istext,
				"fhash"      : self.table.fhash,
				"mimetype"   : self.table.mimetype,
				"fspath"     : self.table.fspath
			}


	##############################################################################################################################################
	#
	#
	#	########  ########     ######## ##     ## ##    ##  ######  ######## ####  #######  ##    ##  ######
	#	##     ## ##     ##    ##       ##     ## ###   ## ##    ##    ##     ##  ##     ## ###   ## ##    ##
	#	##     ## ##     ##    ##       ##     ## ####  ## ##          ##     ##  ##     ## ####  ## ##
	#	##     ## ########     ######   ##     ## ## ## ## ##          ##     ##  ##     ## ## ## ##  ######
	#	##     ## ##     ##    ##       ##     ## ##  #### ##          ##     ##  ##     ## ##  ####       ##
	#	##     ## ##     ##    ##       ##     ## ##   ### ##    ##    ##     ##  ##     ## ##   ### ##    ##
	#	########  ########     ##        #######  ##    ##  ######     ##    ####  #######  ##    ##  ######
	#
	#
	##############################################################################################################################################


	def keyToCol(self, key):
		key = key.lower()
		if not key in self.colMap:
			raise ValueError("Invalid column name '%s'" % key)
		return self.colMap[key]


	def sqlBuildConditional(self, **kwargs):
		operators = []

		# Short circuit and return none (so the resulting where clause is all items) if no kwargs are passed.
		if not kwargs:
			return None

		for key, val in kwargs.items():
			operators.append((self.keyToCol(key) == val))

		# This is ugly as hell, but it functionally returns x & y & z ... for an array of [x, y, z]
		# And allows variable length arrays.
		conditional = functools.reduce(opclass.and_, operators)
		return conditional


	def sqlBuildInsertArgs(self, returning=None, **kwargs):

		cols = [self.table.src]
		vals = [self.tableKey]

		if 'url' in kwargs:

			cols.append(self.table.netloc)
			vals.append(urllib.parse.urlparse(kwargs['url']).netloc.lower())

		for key, val in kwargs.items():
			key = key.lower()

			if key not in self.colMap:
				raise ValueError("Invalid column name for insert! '%s'" % key)
			cols.append(self.colMap[key])
			vals.append(val)

		query = self.table.insert(columns=cols, values=[vals], returning=returning)
		query, params = tuple(query)

		return query, params


	# Insert new item into DB.
	# MASSIVELY faster if you set commit=False (it doesn't flush the write to disk), but that can open a transaction which locks the DB.
	# Only pass commit=False if the calling code can gaurantee it'll call commit() itself within a reasonable timeframe.
	def insertIntoDb(self, commit=True, **kwargs):
		query, queryArguments = self.sqlBuildInsertArgs(returning=[self.table.dbid], **kwargs)

		if self.QUERY_DEBUG:
			print("Query = ", query)
			print("Args = ", queryArguments)

		with self.conn.cursor() as cur:
			with transaction(cur, commit=commit):
				cur.execute(query, queryArguments)
				ret = cur.fetchone()

		if self.QUERY_DEBUG:
			print("Query ret = ", ret)

		return ret[0]


	def generateUpdateQuery(self, **kwargs):

		cols = []
		vals = []

		# By default, take ownership of any pages we're operating on by setting it's src key to us
		if not 'src' in kwargs:
			cols.append(self.table.src)
			vals.append(self.tableKey)

		if 'url' in kwargs:
			cols.append(self.table.netloc)
			vals.append(urllib.parse.urlparse(kwargs['url']).netloc.lower())

		if "dbid" in kwargs:
			where = (self.table.dbid == kwargs.pop('dbid'))
		elif "url" in kwargs:
			where = (self.table.url == kwargs.pop('url'))
		else:
			raise ValueError("GenerateUpdateQuery must be passed a single unique column identifier (either dbId or url)")

		# Extract and insert the netloc if needed.
		if 'url' in kwargs:
			print("Urlparse!")
			cols.append(self.table.netloc)
			vals.append(urllib.parse.urlparse(kwargs['url']).netloc.lower())


		for key, val in kwargs.items():
			key = key.lower()

			if key not in self.colMap:
				raise ValueError("Invalid column name for insert! '%s'" % key)
			cols.append(self.colMap[key])
			vals.append(val)

		query = self.table.update(columns=cols, values=vals, where=where)
		query, params = tuple(query)

		return query, params



	# Update entry with key sourceUrl with values **kwargs
	# kwarg names are checked for validity, and to prevent possiblity of sql injection.
	def updateDbEntry(self, commit=True, **kwargs):


		query, queryArguments = self.generateUpdateQuery(**kwargs)

		if self.QUERY_DEBUG:
			print("Query = ", query)
			print("Args = ", queryArguments)

		with self.conn.cursor() as cur:
			with transaction(cur, commit=commit):
				cur.execute(query, queryArguments)

		self.insertDelta(**kwargs)


	def deleteDbEntry(self, commit=True, **kwargs):
		if len(kwargs) != 1:
			raise ValueError("deleteDbEntry only supports calling with a single kwarg", kwargs)

		validCols = ["dbid", "url"]


		key, val = kwargs.popitem()
		if key not in validCols:
			raise ValueError("Invalid column key for delete query: %s. Must be either 'dbid' or 'url'" % key)

		where = (self.colMap[key.lower()] == val)

		query = self.table.delete(where=where)

		query, args = tuple(query)


		if self.QUERY_DEBUG:
			print("Query = ", query)
			print("Args = ", args)

		with self.conn.cursor() as cur:
			with transaction(cur, commit=commit):
				cur.execute(query, args)





	def getRowsByValue(self, limitByKey=True, **kwargs):
		if limitByKey and self.tableKey:
			kwargs["src"] = self.tableKey


		where = self.sqlBuildConditional(**kwargs)

		wantCols = (
				self.table.dbid,
				self.table.src,
				self.table.dlstate,
				self.table.url,
				self.table.title,
				self.table.series,
				self.table.contents,
				self.table.istext,
				self.table.fhash,
				self.table.mimetype,
				self.table.fspath
			)

		query = self.table.select(*wantCols, order_by=sql.Desc(self.table.dbid), where=where)

		query, quargs = tuple(query)

		if self.QUERY_DEBUG:
			print("Query = ", query)
			print("args = ", quargs)

		with self.conn.cursor() as cur:

			#wrap queryies in transactions so we don't have hanging db handles.
			with transaction(cur):
				cur.execute(query, quargs)
				rets = cur.fetchall()



		retL = []
		for row in rets:

			keys = ['dbid', 'src', 'dlstate', 'url', 'title', 'series', 'contents', 'istext', 'fhash', 'mimetype', 'fspath']
			retL.append(dict(zip(keys, row)))
		return retL

	def getRowByValue(self, **kwargs):
		rows = self.getRowsByValue(**kwargs)
		if len(rows) == 1:
			return rows.pop()
		if len(rows) == 0:
			return None
		else:
			raise ValueError("Got multiple rows for selection. Wat?")




	def saveFile(self, url, mimetype, fileName, content):


		hadFile = False
		# Yeah, I'm hashing twice in lots of cases. Bite me
		fHash = self.getHash(content)

		with self.conn.cursor() as cur:

			# Look for existing files with the same MD5sum. If there are any, just point the new file at the
			# fsPath of the existing one, rather then creating a new file on-disk.
			with transaction(cur):
				cur.execute("SELECT fspath  FROM {tableName} WHERE fhash=%s;".format(tableName=self.tableName), (fHash, ))
				row = cur.fetchone()
				if row:
					self.log.info("Already downloaded file. Not creating duplicates.")
					hadFile = True
					fqPath = row[0]

			with transaction(cur):

				cur.execute("SELECT dbid, fspath, contents, mimetype  FROM {tableName} WHERE url=%s;".format(tableName=self.tableName), (url, ))
				row = cur.fetchone()
				if not row:
					self.log.critical("Failure when saving file for URL '%s'", url)
					self.log.critical("File name: '%s'", fileName)
					return

				dbid, havePath, haveCtnt, haveMime = row
				# self.log.info('havePath, haveCtnt, haveMime - %s, %s, %s', havePath, haveCtnt, haveMime)

				if not hadFile:
					fqPath = self.getFilenameFromIdName(dbid, fileName)

				newRowDict = {  "dlstate" : 2,
								"series"  : None,
								"contents": len(content),
								"istext"  : False,
								"mimetype": mimetype,
								"fspath"  : fqPath,
								"fhash"   : fHash}


				self.updateDbEntry(url=url, commit=False, **newRowDict)


		if not hadFile:
			try:
				with open(fqPath, "wb") as fp:
					fp.write(content)
			except OSError:
				self.log.error("Error when attempting to save file. ")
				with transaction(cur):
					newRowDict = {"dlstate" : -1}
					self.updateDbEntry(url=url, commit=False, **newRowDict)


	def getToDo(self):
		cur = self.conn.cursor()

		# Retreiving todo items must be atomic, so we lock for that.
		with self.dbLock:
			with transaction(cur):

				cur.execute('''SELECT dbid, url FROM {tableName} WHERE dlstate=%s AND src=%s ORDER BY istext ASC LIMIT 1;'''.format(tableName=self.tableName), (0, self.tableKey))
				row = cur.fetchone()

				# print(row)


				if not row:
					return False
				else:
					dbid, url = row
					cur.execute('UPDATE {tableName} SET dlstate=%s WHERE dbid=%s;'.format(tableName=self.tableName), (1, dbid))

		if not url.startswith("http"):
			raise ValueError("Non HTTP URL in database: '%s'!" % url)
		return url



	def resetStuckItems(self):
		self.log.info("Resetting stuck downloads in DB")
		with self.conn.cursor() as cur:
			cur.execute('''UPDATE {tableName} SET dlState=0 WHERE dlState=1 AND src=%s'''.format(tableName=self.tableName), (self.tableKey, ))
		self.conn.commit()
		self.log.info("Download reset complete")

	# Override to filter items that get
	def changeFilter(self, url, title, changePercentage):
		return False

	def insertChangeStats(self, url, changePercentage, title):

		# Skip title cruft on baka-tsuki
		if self.changeFilter(url, title, changePercentage):
			return

		with self.conn.cursor() as cur:
			query = '''INSERT INTO {changeTable} (src, url, change, title, changeDate) VALUES (%s, %s, %s, %s, %s)'''.format(changeTable=self.changeTableName)
			values = (self.tableKey, url, changePercentage, title, time.time())
			cur.execute(query, values)


	##############################################################################################################################################
	# Higher level DB Interfacing
	##############################################################################################################################################


	def upsert(self, pgUrl, commit=True, **kwargs):
		if 'url' in kwargs and 'drive_web' in kwargs['url']:
			self.log.error('')
			self.log.error('')
			self.log.error("WAT")
			self.log.error('')
			self.log.error(traceback.format_stack())
			self.log.error('')


		if 'url' in kwargs and not kwargs['url'].startswith("http"):
			self.log.error('')
			self.log.error('')
			self.log.error("WAT")
			self.log.error('')
			self.log.error(traceback.format_stack())
			self.log.error('')


		cur = self.conn.cursor()

		# print("Upserting!")

		try:
			with transaction(cur, commit=commit):
				self.insertIntoDb(commit=False, url=pgUrl, **kwargs)

		except psycopg2.IntegrityError:
			if kwargs:
				with transaction(cur, commit=commit):
					self.updateDbEntry(url=pgUrl, **kwargs)
		# print("Upserted")

	def insertDelta(self, **kwargs):

		if 'istext' in kwargs and not kwargs['istext']:
			return

		if not 'contents' in kwargs:
			return

		if 'url' in kwargs:
			old = self.getRowByValue(url=kwargs['url'])
		elif 'dbid' in kwargs:
			old = self.getRowByValue(dbid=kwargs['dbid'])
		else:
			raise ValueError("No identifying info in insertDelta call!")

		if 'title' in kwargs:
			title = kwargs['title']
		else:
			title = old['title']

		if not title:
			title = ''


		item = kwargs['url'] if 'url' in kwargs else kwargs['dbid']
		if not old:
			raise ValueError("Couldn't find original db entry for item '%s'?" % item)


		if old['contents'] == None:
			old['contents'] = ''

		oldStr = str(old['contents'])
		newStr = str(kwargs['contents'])

		# self.log.info("Calculating edit-distance")
		# print("String lengths", len(oldStr), len(newStr))

		lChange = abs(len(oldStr) - len(newStr))
		lTotal = max((len(oldStr), len(newStr)))
		self.log.info("Coarse length change: '%s'", lChange)
		# distance = lv.distance(oldStr, newStr)
		# distance = 0
		# self.log.info("Done")
		# space = min((len(oldStr), len(newStr)))

		if lTotal == 0:
			lTotal = 1

		change = (lChange / lTotal) * 100
		change = min((change, 100))
		self.log.info("Percent change in page contents: %s", change)

		self.insertChangeStats(old['url'], change, title)


	def getHash(self, fCont):

		m = hashlib.md5()
		m.update(fCont)
		return m.hexdigest()


if __name__ == "__main__":
	print("Test mode!")
	domains = fetchRelinkableDomains()
	print(domains)


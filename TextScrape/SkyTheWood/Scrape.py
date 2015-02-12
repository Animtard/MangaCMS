
import logSetup
if __name__ == "__main__":
	print("Initializing logging")
	logSetup.initLogging()

import TextScrape.TextScrapeBase

import readability.readability
import bs4
import webFunctions


class Scrape(TextScrape.TextScrapeBase.TextScraper):
	tableKey = 'stw'
	loggerPath = 'Main.Stw.Scrape'
	pluginName = 'SkyTheWoodScrape'

	wg = webFunctions.WebGetRobust(logPath=loggerPath+".Web")

	threads = 3

	baseUrl = "http://skythewood.blogspot.sg/"
	fileDomains = set(['bp.blogspot.com'])
	startUrl = baseUrl

	# Any url containing any of the words in the `badwords` list will be ignored.
	badwords = [
					'#comment-form',
					'the-imouto-petter.html',
					'/search/label/',
				]

	decompose = [
		{'id'    : 'header'},

		{'class'  : 'column-right-outer'},
		{'class'  : 'column-left-outer'},
		{'class'  : 'tabs-outer'},
		{'class'  : 'header-outer'},
		{'class'  : 'date-header'},
		{'class'  : 'comments'},
		{'class'  : 'blog-pager'},
		{'class'  : 'post-feeds'},
		{'class'  : 'post-footer'},
		{'class'  : 'post-feeds'},
		{'class'  : 'blog-feeds'},
		{'class'  : 'footer-outer'},
		{'class'  : 'quickedit'},
		{'class'  : 'widget-content'},


	]

	# Grab all images, ignoring host domain
	allImages = True

	def extractLinks(self, pageCtnt, url=None):

		# since readability strips tag attributes, we preparse with BS4,
		# parse with readability, and then do reformatting *again* with BS4
		# Yes, this is ridiculous.
		soup = bs4.BeautifulSoup(inPage)

		# Decompose all the parts we don't want
		for key in self.decompose:
			for instance in soup.find_all(True, attrs=key):
				instance.decompose()


		doc = readability.readability.Document(soup.prettify())
		doc.parse()
		content = doc.content()

		soup = bs4.BeautifulSoup(content)

		contents = ''


		# Relink all the links so they work in the reader.
		for aTag in soup.find_all("a"):
			try:
				aTag["href"] = self.convertToReaderUrl(aTag["href"])
			except KeyError:
				continue

		for imtag in soup.find_all("img"):
			try:
				imtag["src"] = self.convertToReaderUrl(imtag["src"])
			except KeyError:
				continue

		# Generate HTML string for /just/ the contents of the <body> tag.
		for item in soup.body.contents:
			if type(item) is bs4.Tag:
				contents += item.prettify()
			elif type(item) is bs4.NavigableString:
				contents += item
			else:
				print("Wat", item)

		title = doc.title()
		title = title.replace("Skythewood translations:", "")
		title = title.strip()

		return title, contents



def test():
	scrp = Scrape()
	scrp.crawl()
	# scrp.retreiveItemFromUrl(scrp.baseUrl)


if __name__ == "__main__":
	test()





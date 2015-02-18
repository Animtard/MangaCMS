
import logSetup
if __name__ == "__main__":
	print("Initializing logging")
	logSetup.initLogging()

import TextScrape.BlogspotScrape

import webFunctions


class Scrape(TextScrape.BlogspotScrape.BlogspotScrape):
	tableKey = 'ecwebnovel'
	loggerPath = 'Main.EcWebNovel.Scrape'
	pluginName = 'EcWebNovelScrape'

	wg = webFunctions.WebGetRobust(logPath=loggerPath+".Web")

	threads = 1

	baseUrl = "http://ecwebnovel.blogspot.ca/"
	startUrl = baseUrl


	tld = set(['com', 'ca', 'fr'])

	# Any url containing any of the words in the `badwords` list will be ignored.
	badwords = [
				"/manga/",
				"/recruitment/",
				"wpmp_switcher=mobile",
				"account/begin_password_reset",
				"/comment-page-",

				# Why do people think they need a fucking comment system?
				'/?replytocom=',
				'#comments',

				# Mask out the PDFs
				"-online-pdf-viewer/",

				# Who the fuck shares shit like this anyways?
				"?share=",

				]


	def decomposeItems(self, soup, toDecompose):
		# Decompose all the parts we don't want
		for key in toDecompose:
			for instance in soup.find_all(True, attrs=key):
				instance.decompose() # This call permutes the tree!

		# Clear out all the iframes
		for instance in soup.find_all('iframe'):
			instance.decompose()

		return soup

	stripTitle = "EC Webnovel:"



def test():
	scrp = Scrape()
	scrp.crawl()
	# scrp.retreiveItemFromUrl(scrp.startUrl)


if __name__ == "__main__":
	test()






import logSetup
if __name__ == "__main__":
	print("Initializing logging")
	logSetup.initLogging()

import TextScrape.WordpressScrape

import webFunctions


class Scrape(TextScrape.WordpressScrape.WordpressScrape):
	tableKey = 'rtdtl'
	loggerPath = 'Main.RaiseTheDead.Scrape'
	pluginName = 'RaiseTheDeadScrape'

	wg = webFunctions.WebGetRobust(logPath=loggerPath+".Web")

	threads = 1

	baseUrl = "https://wartdf.wordpress.com/"
	startUrl = [
		baseUrl,
		# 'http://pastebin.com/C8cU0ZPq',
		# 'http://pastebin.com/Gm4xYe35',
		# 'http://pastebin.com/iGjtwjVR',
		# 'http://pastebin.com/VyPC3Kdn',
		# 'http://pastebin.com/NS6kwFvL',
		# 'http://pastebin.com/raw.php?i=C8cU0ZPq',
		# 'http://pastebin.com/raw.php?i=Gm4xYe35',
		# 'http://pastebin.com/raw.php?i=iGjtwjVR',
		# 'http://pastebin.com/raw.php?i=VyPC3Kdn',
		# 'http://pastebin.com/raw.php?i=NS6kwFvL',
		]

	fileDomains = set(['files.wordpress.com'])

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
				"/feed/",
				]



	decompose = [
		{'id'    :'header'},
		{'class' : 'widget-area'},
		{'id'    : 'footer'},
		{'class' : 'photo-meta'},
		{'class' : 'page-header'},
		{'class' : 'wpcnt'},
		{'class' : 'bit'},
		{'id'    : 'bit'},
		{'id'    : 'author-info'},
		{'id'    : 'secondary'},
		{'id'    : 'colophon'},
		{'id'    : 'branding'},
		{'id'    : 'nav-single'},
		{'id'    : 'likes-other-gravatars'},
		{'id'    : 'sidebar'},
		{'id'    : 'carousel-reblog-box'},
		{'id'    : 'infinite-footer'},
		{'id'    : 'nav-above'},
		{'id'    : 'nav-below'},
		{'id'    : 'jp-post-flair'},
		{'id'    : 'comments'},
		{'class' : 'entry-utility'},
		{'name'  : 'likes-master'},

	]

	stripTitle = 'Raising the Dead |'


def test():
	scrp = Scrape()
	scrp.crawl()
	# scrp.retreiveItemFromUrl(scrp.startUrl)


if __name__ == "__main__":
	test()





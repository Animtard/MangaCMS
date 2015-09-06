
import runStatus
from ScrapePlugins.ZenonLoader.FeedLoader import FeedLoader
from ScrapePlugins.ZenonLoader.ContentLoader import ContentLoader

import ScrapePlugins.RunBase

import time


class Runner(ScrapePlugins.RunBase.ScraperBase):
	loggerPath = "Main.Manga.Ze.Run"

	pluginName = "ZenonLoader"


	def _go(self):

		self.log.info("Checking Dynasty feeds for updates")
		fl = FeedLoader()
		fl.go()
		fl.closeDB()

		time.sleep(3)
		#print "wat", cl

		if not runStatus.run:
			return

		cl = ContentLoader()

		if not runStatus.run:
			return

		cl.go()




if __name__ == "__main__":
	import utilities.testBase as tb

	with tb.testSetup(startObservers=True):

		run = Runner()
		run.go()


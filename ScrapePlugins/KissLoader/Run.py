
import runStatus
from ScrapePlugins.KissLoader.FeedLoader import FeedLoader
from ScrapePlugins.KissLoader.ContentLoader import ContentLoader

import ScrapePlugins.RunBase

import time


class Runner(ScrapePlugins.RunBase.ScraperBase):
	loggerPath = "Main.Ki.Run"

	pluginName = "KissLoader"


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

		todo = cl.retreiveTodoLinksFromDB()

		if not runStatus.run:
			return

		cl.processTodoLinks(todo)
		cl.closeDB()



if __name__ == "__main__":
	import utilities.testBase as tb

	with tb.testSetup():

		run = Runner()
		run.go()




from ScrapePlugins.SkLoader.skFeedLoader import SkFeedLoader
from ScrapePlugins.SkLoader.skContentLoader import SkContentLoader

import ScrapePlugins.RunBase

import time

import runStatus


class Runner(ScrapePlugins.RunBase.ScraperBase):
	loggerPath = "Main.Sk.Run"

	pluginName = "SkLoader"


	def _go(self):

		self.log.info("Checking SK feeds for updates")
		fl = SkFeedLoader()
		fl.go()
		fl.closeDB()

		time.sleep(3)
		#print "wat", cl

		if not runStatus.run:
			return

		cl = SkContentLoader()

		if not runStatus.run:
			return

		todo = cl.retreiveTodoLinksFromDB()

		if not runStatus.run:
			return

		cl.processTodoLinks(todo)
		cl.closeDB()

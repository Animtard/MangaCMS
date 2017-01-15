

if __name__ == "__main__":

	import logSetup
	logSetup.initLogging()

import ScrapePlugins.M.BuMonitor.Run
import ScrapePlugins.M.BtBaseManager.Run
import ScrapePlugins.M.JzLoader.Run

import ScrapePlugins.H.DjMoeLoader.Run
import ScrapePlugins.H.DjMoeLoader.Retag
import ScrapePlugins.H.PururinLoader.Run
import ScrapePlugins.H.FakkuLoader.Run
import ScrapePlugins.H.SadPandaLoader.Run
import ScrapePlugins.H.NHentaiLoader.Run
import ScrapePlugins.H.HBrowseLoader.Run


import ScrapePlugins.M.McLoader.Run
import ScrapePlugins.M.CxLoader.Run
import ScrapePlugins.M.MjLoader.Run
import ScrapePlugins.M.WebtoonLoader.Run            # Yeah. There is webtoon.com. and WebtoonsReader.com. Confusing much?
import ScrapePlugins.M.WebtoonsReader.Run
import ScrapePlugins.M.KissLoader.Run
import ScrapePlugins.M.DynastyLoader.Run
import ScrapePlugins.M.Crunchyroll.Run
import ScrapePlugins.M.IrcGrabber.IrcEnqueueRun
import ScrapePlugins.M.IrcGrabber.BotRunner
import ScrapePlugins.M.Kawaii.Run
import ScrapePlugins.M.ZenonLoader.Run
import ScrapePlugins.M.MangaBox.Run
import ScrapePlugins.M.MangaHere.Run
import ScrapePlugins.M.MangaStreamLoader.Run
import ScrapePlugins.M.YoMangaLoader.Run
import ScrapePlugins.M.SurasPlace.Run
import ScrapePlugins.M.GameOfScanlationLoader.Run

import ScrapePlugins.M.FoolSlide.Modules.CanisMajorRun
import ScrapePlugins.M.FoolSlide.Modules.ChibiMangaRun
import ScrapePlugins.M.FoolSlide.Modules.DokiRun
import ScrapePlugins.M.FoolSlide.Modules.GoMangaCoRun
import ScrapePlugins.M.FoolSlide.Modules.IlluminatiMangaRun
import ScrapePlugins.M.FoolSlide.Modules.JaptemMangaRun
import ScrapePlugins.M.FoolSlide.Modules.MangatopiaRun
import ScrapePlugins.M.FoolSlide.Modules.RoseliaRun
import ScrapePlugins.M.FoolSlide.Modules.S2Run
import ScrapePlugins.M.FoolSlide.Modules.SenseRun
import ScrapePlugins.M.FoolSlide.Modules.ShoujoSenseRun
import ScrapePlugins.M.FoolSlide.Modules.TripleSevenRun
import ScrapePlugins.M.FoolSlide.Modules.TwistedHelRun
import ScrapePlugins.M.FoolSlide.Modules.VortexRun



import ScrapePlugins.M.MangaMadokami.Run
import ScrapePlugins.M.BooksMadokami.Run

# Convenience functions to make intervals clearer.
def days(num):
	return 60*60*24*num
def hours(num):
	return 60*60*num
def minutes(num):
	return 60*num

# Plugins in this dictionary are the active plugins. Comment out a plugin to disable it.
# plugin keys specify when plugins will start, and cannot be duplicates.
# All they do is specify the order in which plugins
# are run, initially, starting after 1-minue*{key} intervals
scrapePlugins = {
	0  : (ScrapePlugins.M.BtBaseManager.Run,                   hours( 1)),
	1  : (ScrapePlugins.M.MangaStreamLoader.Run,               hours( 6)),
	2  : (ScrapePlugins.M.BuMonitor.Run,                       hours( 1)),

	3  : (ScrapePlugins.M.JzLoader.Run,                        hours( 8)),   # Every 8 hours, since I have to scrape a lot of pages, and it's not a high-volume source anyways
	6  : (ScrapePlugins.M.McLoader.Run,                        hours(12)),  # every 12 hours, it's just a single scanlator site.
	8  : (ScrapePlugins.M.IrcGrabber.IrcEnqueueRun,            hours(12)),  # Queue up new items from IRC bots.
	11 : (ScrapePlugins.M.CxLoader.Run,                        hours(12)),  # every 12 hours, it's just a single scanlator site.
	# 12 : (ScrapePlugins.M.MjLoader.Run,                        hours( 1)),
	13 : (ScrapePlugins.M.IrcGrabber.BotRunner,                hours( 1)),  # Irc bot never returns. It runs while the app is live. Rerun interval doesn't matter, as a result.
	15 : (ScrapePlugins.M.MangaHere.Run,                       hours(12)),
	16 : (ScrapePlugins.M.WebtoonLoader.Run,                   hours( 8)),
	17 : (ScrapePlugins.M.DynastyLoader.Run,                   hours( 8)),
	19 : (ScrapePlugins.M.KissLoader.Run,                      hours( 1)),
	21 : (ScrapePlugins.M.Crunchyroll.Run,                     hours( 4)),
	# 23 : (ScrapePlugins.M.WebtoonsReader.Run,                  hours( 6)),  # They claim they're planning on coming back. We'll see.
	25 : (ScrapePlugins.M.Kawaii.Run,                          hours(12)),
	26 : (ScrapePlugins.M.ZenonLoader.Run,                     hours(24)),
	27 : (ScrapePlugins.M.MangaBox.Run,                        hours(12)),
	28 : (ScrapePlugins.M.YoMangaLoader.Run,                   hours(12)),
	29 : (ScrapePlugins.M.GameOfScanlationLoader.Run,          hours(12)),

	18 : (ScrapePlugins.H.HBrowseLoader.Run,                   hours( 1)),
	9  : (ScrapePlugins.H.PururinLoader.Run,                   hours( 1)),
	10 : (ScrapePlugins.H.FakkuLoader.Run,                     hours( 1)),
	20 : (ScrapePlugins.H.NHentaiLoader.Run,                   hours( 1)),
	22 : (ScrapePlugins.H.SadPandaLoader.Run,                  hours(12)),
	4  : (ScrapePlugins.H.DjMoeLoader.Run,                     hours( 1)),
	5  : (ScrapePlugins.H.DjMoeLoader.Retag,                   hours( 1)),

	# FoolSlide modules

	30 : (ScrapePlugins.M.FoolSlide.Modules.CanisMajorRun,      hours(12)),
	31 : (ScrapePlugins.M.FoolSlide.Modules.ChibiMangaRun,      hours(12)),
	32 : (ScrapePlugins.M.FoolSlide.Modules.DokiRun,            hours(12)),
	33 : (ScrapePlugins.M.FoolSlide.Modules.GoMangaCoRun,       hours(12)),
	34 : (ScrapePlugins.M.FoolSlide.Modules.IlluminatiMangaRun, hours(12)),
	35 : (ScrapePlugins.M.FoolSlide.Modules.JaptemMangaRun,     hours(12)),
	36 : (ScrapePlugins.M.FoolSlide.Modules.MangatopiaRun,      hours(12)),
	37 : (ScrapePlugins.M.FoolSlide.Modules.RoseliaRun,         hours(12)),
	38 : (ScrapePlugins.M.FoolSlide.Modules.S2Run,              hours(12)),
	39 : (ScrapePlugins.M.FoolSlide.Modules.SenseRun,           hours(12)),
	40 : (ScrapePlugins.M.FoolSlide.Modules.ShoujoSenseRun,     hours(12)),
	41 : (ScrapePlugins.M.FoolSlide.Modules.TripleSevenRun,     hours(12)),
	42 : (ScrapePlugins.M.FoolSlide.Modules.TwistedHelRun,      hours(12)),
	43 : (ScrapePlugins.M.FoolSlide.Modules.VortexRun,          hours(12)),

	50 : (ScrapePlugins.M.MangaMadokami.Run,                   hours(4)),
	51 : (ScrapePlugins.M.BooksMadokami.Run,                   hours(4)),

}


if __name__ == "__main__":

	# scrapePlugins = {
		# 0 : (TextScrape.BakaTsuki.Run,                       60*60*24*7),  # Every 7 days, because books is slow to update
		# 1 : (TextScrape.JapTem.Run,                          60*60*24*5),
		# 3 : (TextScrape.Guhehe.Run,                          60*60*24*5),
		# 2 : (TextScrape.ReTranslations.Run,                  60*60*24*1)   # There's not much to actually scrape here, and it's google, so I don't mind hitting their servers a bit.
	# }

	print("Test run!")
	import nameTools as nt

	def callGoOnClass(passedModule):
		print("Passed module = ", passedModule)
		print("Calling class = ", passedModule.Runner)
		instance = passedModule.Runner()
		instance.go()
		print("Instance:", instance)


	import signal
	import runStatus

	def signal_handler(dummy_signal, dummy_frame):
		if runStatus.run:
			runStatus.run = False
			print("Telling threads to stop (activePlugins)")
		else:
			print("Multiple keyboard interrupts. Raising")
			raise KeyboardInterrupt


	signal.signal(signal.SIGINT, signal_handler)
	import sys
	import traceback
	print("Starting")
	try:
		if len(sys.argv) > 1 and int(sys.argv[1]) in scrapePlugins:
			plugin, interval = scrapePlugins[int(sys.argv[1])]
			print(plugin, interval)
			callGoOnClass(plugin)
		else:
			print("Loopin!", scrapePlugins)
			for plugin, interval in scrapePlugins.values():
				print(plugin, interval)
				callGoOnClass(plugin)
	except:
		traceback.print_exc()


	print("Complete")

	nt.dirNameProxy.stop()
	sys.exit()

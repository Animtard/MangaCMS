
import logSetup
if __name__ == "__main__":
	logSetup.initLogging()

# import ScrapePlugins.FufufuuLoader.Run
import nameTools as nt
from ScrapePlugins.FufufuuLoader.fufufuDbLoader import FuFuFuuDbLoader
from ScrapePlugins.FufufuuLoader.fufufuContentLoader import FuFuFuuContentLoader
from ScrapePlugins.FufufuuLoader.Retag import Runner

import signal
import runStatus

def signal_handler(dummy_signal, dummy_frame):
	if runStatus.run:
		runStatus.run = False
		print("Telling threads to stop")
	else:
		print("Multiple keyboard interrupts. Raising")
		raise KeyboardInterrupt


def test():

	signal.signal(signal.SIGINT, signal_handler)
	# print(ScrapePlugins.FufufuuLoader.Run)
	# runner = ScrapePlugins.FufufuuLoader.Run.Runner()

	# dbInt = FuFuFuuDbLoader()
	# dbInt.go()
	# clInt = FuFuFuuContentLoader()

	dbInt = Runner()
	dbInt.go()


	# # runner.setup()

	# # dlLink = "http://fufufuu.net/m/12683/heavens-door/"

	# # runner.cl.log.info("Resetting stuck downloads in DB")
	# # runner.cl.conn.execute('UPDATE fufufuu SET downloaded=0, processing=1 WHERE dlLink=?;', (dlLink, ))
	# # runner.cl.conn.commit()
	# # runner.cl.log.info("Download reset complete")

	# # runner.cl.downloadItem({"dlLink" : dlLink})
	# # runner.loadNewFiles()
	# runner.setup()
	# for x in range(0, 450):
	# 	runner.checkFeed(pageOverride=x)
	# #runner.loadNewFiles()

	nt.dirNameProxy.stop()

if __name__ == "__main__":
	test()

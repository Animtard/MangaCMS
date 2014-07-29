
import logSetup
if __name__ == "__main__":
	logSetup.initLogging()



import runStatus
from ScrapePlugins.FakkuLoader.Run import Runner
from ScrapePlugins.FakkuLoader.fkFeedLoader import FakkuFeedLoader
from ScrapePlugins.FakkuLoader.fkContentLoader import FakkuContentLoader
import signal

import os.path

def customHandler(signum, stackframe):
	if runStatus.run:
		runStatus.run = False
		print("Telling threads to stop")
	else:
		print("Multiple keyboard interrupts. Raising")
		raise KeyboardInterrupt

def test():


	loader = FakkuFeedLoader()
	# loader.go()

	for x in range(1, 410):
		feedItems = loader.getItems(pageOverride=x)
		loader.processLinksIntoDB(feedItems)
	# # feedItems = loader.getItemsFromContainer("Ore no Kanojo + H", loader.quoteUrl("http://download.japanzai.com/Ore no Kanojo + H/index.php"))
	# # loader.log.info("Processing feed Items")
	# for item in feedItems:
	# 	print("Item", item)

	# loader.closeDB()

	# runner = Runner()
	# runner.go()


	# cl = FakkuContentLoader()
	# cl.go()


if __name__ == "__main__":
	try:
		test()
	finally:
		import nameTools as nt
		nt.dirNameProxy.stop()


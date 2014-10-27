

print("Utilities Startup")
import runStatus
runStatus.preloadDicts = False

import logSetup
logSetup.initLogging()

import signal
import sys
import os.path
import utilities.dedupDir
import utilities.approxFileSorter
import utilities.autoOrganize as autOrg
import utilities.cleanDb
import deduplicator.remoteInterface

def printHelp():

	print("################################### ")
	print("##   System maintenance script   ## ")
	print("################################### ")
	print("")
	print("*********************************************************")
	print("Organizing Tools")
	print("*********************************************************")
	print("	organize {dirPath}")
	print("		Run auto-organizing tools against {dirPath}")
	print()
	print("	rename {dirPath}")
	print("		Rename directories in {dirPath} to match MangaUpdates naming")
	print()
	print("	dirs-clean {target-path} {del-dir}")
	print("		Find duplicates in each subdir of {target-path}, and remove them.")
	print("		Functions on a per-directory basis, so only duplicates in the same folder will be considered")
	print("		Does not currently use phashing.")
	print("		'Deleted' files are actually moved to {del-dir}, to allow checking before actual deletion.")
	print("		The moved files are named with the entire file-path, with the '/' being replaced with ';'.")
	print()
	print("	dir-clean {target-path} {del-dir}")
	print("		Find duplicates in {target-path}, and remove them.")
	print("		Functions on a per-directory basis, so only duplicates in the same folder will be considered")
	print("		Does not currently use phashing.")
	print("		'Deleted' files are actually moved to {del-dir}, to allow checking before actual deletion.")
	print("		The moved files are named with the entire file-path, with the '/' being replaced with ';'.")
	print("	")
	print("	dirs-restore {target-path}")
	print("		Reverses the action of 'dirs-clean'. {target-path} is the directory specified as ")
	print("		{del-dir} when running 'dirs-clean' ")
	print("	")
	print("	purge-dir {target-path}")
	print("		Processes the output of 'dirs-clean'. {target-path} is the directory specified as ")
	print("		{del-dir} when running 'dirs-clean'. ")
	print("		Each item in {del-dir} is re-confirmed to be a complete duplicate, and then truly deleted. ")
	print("	")
	print("	sort-dir-contents {target-path}")
	print("		Scan the contents of {target-path}, and try to infer the series for each file in said folders.")
	print("		If file doesn't match the series for the folder, and does match a known, valid folder, prompt")
	print("		to move to valid folder.")
	print("	")
	print("	move-unlinked {src-path} {to-path}")
	print("		Scan the contents of {src-path}, and try to infer the series for each subdirectory.")
	print("		If a subdir has no matching series, move it to {to-path}")
	print("	")
	print("*********************************************************")
	print("Miscellaneous Tools")
	print("*********************************************************")

	print("	lookup {name}")
	print("		Lookup {name} in the MangaUpdates name synonym lookup table, print the results.")
	print()

	print("*********************************************************")
	print("Database Maintenance")
	print("*********************************************************")
	print("	reset-missing")
	print("		Reset downloads where the file is missing, and the download is not tagged as deduplicated.")
	print("	")
	print("	clear-bad-dedup")
	print("		Remove deduplicated tag from any files where the file exists.")
	print("	")
	print("	fix-bt-links")
	print("		Fix links for Batoto that point to batoto.com, rather then bato.to.")
	print("	")
	print("	cross-sync")
	print("		Sync name lookup table with seen series.")
	print("	")
	print("	update-bu-lut")
	print("		Regernate lookup strings for MangaUpdates table (needed if the `prepFilenameForMatching` call in nameTools is modified).")
	print("	")
	print("	fix-bad-series")
	print("		Consolidate series names to MangaUpdates standard naming.")
	print("	")



	print("*********************************************************")
	print("Remote deduper interface")
	print("*********************************************************")
	print("phash-clean {targetDir} {removeDir} {scanEnv}")
	print("		Find duplcates on the path {targetDir}, and move them to {removeDir}")
	print("		Duplicate search is done using the set of phashes contained within ")
	print("		{scanEnv}. ")
	print("		Requires deduper server interface to be running.")

	return


def parseOneArgCall(cmd):


	mainArg = sys.argv[1]

	print ("Passed arg", mainArg)


	pc = utilities.cleanDb.PathCleaner()
	pc.openDB()

	if mainArg.lower() == "reset-missing":
		pc.resetMissingDownloads()
	elif mainArg.lower() == "clear-bad-dedup":
		pc.clearInvalidDedupTags()
	elif mainArg.lower() == "fix-bt-links":
		pc.patchBatotoLinks()
	elif mainArg.lower() == "cross-sync":
		pc.crossSyncNames()
	elif mainArg.lower() == "update-bu-lut":
		pc.regenerateNameMappings()
	elif mainArg.lower() == "fix-bad-series":
		pc.consolidateSeriesNaming()
	elif mainArg.lower() == "fix-djm":
		pc.fixDjMItems()
	elif mainArg.lower() == "import-djm":
		if not len(sys.argv) == 3:
			print("You must specify a path to import from!")
			return
		sourcePath = sys.argv[2]
		pc.importDjMItems(sourcePath)
	else:
		print("Unknown arg!")

	pc.closeDB()

def parseTwoArgCall(cmd, val):
	if cmd == "organize":
		if not os.path.exists(val):
			print("Passed path '%s' does not exist!" % val)
			return
		autOrg.organizeFolder(val)
		return

	elif cmd == "rename":
		if not os.path.exists(val):
			print("Passed path '%s' does not exist!" % val)
			return
		autOrg.renameSeriesToMatchMangaUpdates(val)
		return

	elif cmd == "lookup":
		print("Passed name = '%s'" % val)
		import nameTools as nt
		haveLookup = nt.haveCanonicalMangaUpdatesName(val)
		if not haveLookup:
			print("Item not found in MangaUpdates name synonym table")
			print("Processed item as searched = '%s'" % nt.prepFilenameForMatching(val))
		else:
			print("Item found in lookup table!")
			print("Canonical name = '%s'" % nt.getCanonicalMangaUpdatesName(val) )


	elif cmd == "purge-dir":
		if not os.path.exists(val):
			print("Passed path '%s' does not exist!" % val)
			return
		utilities.dedupDir.purgeDedupTemps(val)
		return

	elif cmd == "dirs-restore":
		if not os.path.exists(val):
			print("Passed path '%s' does not exist!" % val)
			return
		utilities.dedupDir.runRestoreDeduper(val)
		return

	elif cmd == "sort-dir-contents":
		if not os.path.exists(val):
			print("Passed path '%s' does not exist!" % val)
			return
		utilities.approxFileSorter.scanDirectories(val)
		return


	else:
		print("Did not understand command!")
		print("Sys.argv = ", sys.argv)

def parseThreeArgCall(cmd, arg1, arg2):
	if cmd == "dirs-clean":
		if not os.path.exists(arg1):
			print("Passed path '%s' does not exist!" % arg1)
			return
		elif not os.path.exists(arg2):
			print("Passed path '%s' does not exist!" % arg2)
			return
		utilities.dedupDir.runDeduper(arg1, arg2)
		return
	elif cmd == "dir-clean":
		if not os.path.exists(arg1):
			print("Passed path '%s' does not exist!" % arg1)
			return
		if not os.path.exists(arg2):
			print("Passed path '%s' does not exist!" % arg2)
			return
		utilities.dedupDir.runSingleDirDeduper(arg1, arg2)
		return

	elif cmd == "move-unlinked":
		if not os.path.exists(arg1):
			print("Passed path '%s' does not exist!" % arg1)
			return
		if not os.path.exists(arg2):
			print("Passed path '%s' does not exist!" % arg2)
			return
		utilities.dedupDir.moveUnlinkable(arg1, arg2)
		return


	elif cmd == "h-fix":
		if not os.path.exists(arg2):
			print("Passed path '%s' does not exist!" % arg2)
			return

		cleaner = utilities.cleanDb.HCleaner(arg1)
		cleaner.resetMissingDownloads(arg2)
		return


	else:
		print("Did not understand command!")
		print("Sys.argv = ", sys.argv)

def parseFourArgCall(cmd, arg1, arg2, arg3):
	if cmd == "phash-clean":
		if not os.path.exists(arg1):
			print("Passed path '%s' does not exist!" % arg1)
			return
		if not os.path.exists(arg2):
			print("Passed path '%s' does not exist!" % arg2)
			return
		if not os.path.exists(arg3):
			print("Passed path '%s' does not exist!" % arg3)
			return
		deduplicator.remoteInterface.pClean(arg1, arg2, arg3)
		return

def customHandler(dummy_signum, dummy_stackframe):
	if runStatus.run:
		runStatus.run = False
		print("Telling threads to stop")
	else:
		print("Multiple keyboard interrupts. Raising")
		raise KeyboardInterrupt


def parseCommandLine():
	signal.signal(signal.SIGINT, customHandler)
	if len(sys.argv) == 2:
		cmd = sys.argv[1].lower()
		parseOneArgCall(cmd)

	elif len(sys.argv) == 3:
		cmd = sys.argv[1].lower()
		val = sys.argv[2]
		parseTwoArgCall(cmd, val)

	elif len(sys.argv) == 4:

		cmd = sys.argv[1].lower()
		arg1 = sys.argv[2]
		arg2 = sys.argv[3]
		parseThreeArgCall(cmd, arg1, arg2)

	elif len(sys.argv) == 5:

		cmd = sys.argv[1].lower()
		arg1 = sys.argv[2]
		arg2 = sys.argv[3]
		arg3 = sys.argv[4]
		parseFourArgCall(cmd, arg1, arg2, arg3)

	else:
		printHelp()

if __name__ == "__main__":
	print("Command line parse")
	parseCommandLine()


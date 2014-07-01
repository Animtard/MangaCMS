
End-User setup (README):

replace all instances of "SOMETHING" with your own directory paths.
Add your username + password for each site.


# Note: Paths have to be absolute.
pickedDir   = r"/SOMETHING/MP"
newDir      = r"/SOMETHING/MN"
baseDir     = r"/SOMETHING/Manga/"

#
fufuDir     = r"/SOMETHING/H/Fufufuu"
djMoeDir    = r"/SOMETHING/H/DjMoe"

# Paths for database and web content
dbName      = '/SOMETHING/MangaCMS/links.db'
webCtntPath = '/SOMETHING/MangaCMS/ctnt'


# Path to the directory of images that get auto-removed from archives on download.
badImageDir  = r"/SOMETHING/MangaCMS/removeImages"

# This is the path to the deduplication tool database API python file.
# You only need to set this if you want to use the on-the-fly duplicate
# removal, which is complex and not fully finished at this time.
# You must have https://github.com/fake-name/IntraArchiveDeduplicator somewhere,
# and have allowed it to build a database of the extant local files for it to
# be of any use.
dedupApiFile = '/SOMETHING/Deduper/dbApi.py'

# Folders to scan for folders to use as download paths.
# Directories are scanned by sorted keys
mangaFolders = {
	1 : {
			"dir" : pickedDir,
			"interval" : 5,
			"lastScan" : 0
		},
	2 : {
			"dir" : newDir,
			"interval" : 5,
			"lastScan" : 0
		},
	10 : {
			"dir" : baseDir,
			"interval" : 45,
			"lastScan" : 0
		}
}

# Manga Updates
buSettings = {
	"login"         : "username",
	"passWd"        : "password",
}

# Starkana.com
skSettings = {

	"login"         : "username",
	"passWd"        : "password",

	"dirs" : {
		"dlDir"         : pickedDir,
		"mnDir"         : newDir,
		"mDlDir"        : baseDir
		}

}

mbSettings = {

	"dirs" : {
		"dlDir"         : pickedDir,
		"mnDir"         : newDir,
		"mDlDir"        : baseDir
		}

}



fuSettings = {
	"dlDir" :  fufuDir,
	"retag" : 60*60*24*31			# 1 month
}

djSettings = {
	"dlDir" :  djMoeDir,
	"retag" : 60*60*24*31			# 1 month
}

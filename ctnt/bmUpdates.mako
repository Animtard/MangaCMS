## -*- coding: utf-8 -*-
<!DOCTYPE html>

<%startTime = time.time()%>
<%namespace name="tableGenerators" file="gentable.mako"/>
<%namespace name="sideBar" file="gensidebar.mako"/>

<html>
<head>
	<title>WAT WAT IN THE BATT</title>
	<link rel="stylesheet" href="style.css">

	<script type="text/javascript" src="/js/jquery-2.1.0.min.js"></script>

	<script type="text/javascript">
		$(document).ready(function() {
		// Tooltip only Text
		$('.showTT').hover(function(){
			// Hover over code
			var title = $(this).attr('data-item');
			$(this).data('tipText', title).removeAttr('title');
			$('<p class="tooltip"></p>')
			.html(title)
			.appendTo('body')
			.fadeIn('slow');
		}, function() {
			// Hover out code
			$(this).attr('title', $(this).data('tipText'));
			$('.tooltip').remove();
		}).mousemove(function(e) {
			var mousex = e.pageX + 20; //Get X coordinates
			var mousey = e.pageY + 10; //Get Y coordinates
			$('.tooltip')
			.css({ top: mousey, left: mousex })
		});
		});
	</script>


</head>

<%!
# Module level!
import time
import datetime
from babel.dates import format_timedelta
import os.path
import urllib.parse

from operator import itemgetter

import nameTools as nt

import unicodedata

import statusManager as sm

colours = {
	# Download Status
	"hasUnread"       : "FF9999",
	"upToDate"        : "99FF99",
	"notInMT"         : "9999FF",


	"failed"          : "000000",
	"moved"           : "FFFF99",
	"queued"          : "FF77FF",
	"created-dir"     : "FFE4B2",
	"not checked"     : "FFFFFF",

	# Categories

	"valid category"  : "FFFFFF",
	"bad category"    : "999999"}



def getNotInDBItems(cur):

	monitorItems = {}
	# cur.execute('SELECT IDs,addDate,seriesName,items,lastUpdated FROM MtMonitoredIDs;')
	# monitored = cur.fetchall()

	# for item in monitored:
	# 	nameClean = nt.sanitizeString(item[2])

	# 	monitorItems[nameClean] = item

	return monitorItems


%>





<%

# ------------------------------------------------------------------------
# This is the top of the main
# page generation section.
# Execution begins here
# ------------------------------------------------------------------------

cur = sqlCon.cursor()

mtItems = getNotInDBItems(cur)

# mtId,
# mtTags,
# mtList,
# buName,
# buId,
# buTags,
# buList,
# readingProgress,
# availProgress,
# rating,
# lastChanged
print("Querying")
cur.execute('SELECT mtId,buId,availProgress,readingProgress,buName,buList FROM MangaSeries WHERE buId IS NOT NULL;')
buItems = cur.fetchall()
print("Query complete")


inMTcount = 0
badLinks = 0

items = {}
tableTopology = ("mtId", "mangaID", "currentChapter", "readChapter", "seriesName", "listName")
for item in buItems:

	item = dict(zip(tableTopology, item))

	seriesName = item["seriesName"]

	if seriesName == None or item["listName"] == None:
		badLinks += 1
		continue

	listName = item["listName"]
	if listName in items:
		items[item["listName"]].append(item)
	else:
		items[item["listName"]] = [item]





	cleanedName = nt.cleanName(seriesName)



	if item["mtId"]:
		inMTcount += 1


# cur.execute('SELECT COUNT(DISTINCT baseName) FROM links WHERE isMp=1;')
# mpDistinct = cur.fetchall()[0][0]

# cur.execute('SELECT COUNT(DISTINCT seriesName) FROM MtMonitoredIDs;')
# monitoredDistinct = cur.fetchall()[0][0]

reSortTop = ["Win", "Fascinating", "Interesting", "Tablet search"]
reSortTop.reverse()
reSortBottom = ["Interesting and Untranslated", "Vaguely Interesting", "Novels of interest", "Good H", "Interesting H", "Meh H", "Complete"]

keys = list(sorted(items.keys()))   # Sort, and then move the "Complete" item to the list end so it displays there instead

for val in reSortBottom:
	for item in keys:
		if val.lower() in item.lower().replace(chr(160), " "):  # lower-case, and replace the non-breaking space with a normal space
			break
	keys.remove(item)
	keys.append(item)

for val in reSortTop:
	for item in keys:
		if val.lower() in item.lower().replace(chr(160), " "):  # lower-case, and replace the non-breaking space with a normal space
			break
	keys.remove(item)
	keys.insert(0, item)


showInMT = True
showNotInMT = True
showOutOfDate = True
showUpToDate = True

showRatingFound  = True
showRatingMissing = True

if "filter" in request.params:
	if request.params["filter"] == ["notMP"]:
		showInMT = False

	elif request.params["filter"] == ["inMP"]:
		showNotInMT = False

if "readStatus" in request.params:
	if request.params["readStatus"] == ["upToDate"]:
		showOutOfDate = False

	elif request.params["readStatus"] == ["outOfDate"]:
		showUpToDate = False

if "hasRating" in request.params:
	if request.params["hasRating"] == ["True"]:
		showRatingMissing = False

	elif request.params["hasRating"] == ["False"]:
		showRatingFound = False

# if "updateMU" in request.params:
# 	if request.params["updateMU"] == ["True"]:

# 		if not flags.buMonRunning:
# 			flags.buDeferredCaller()

# nt.dirNameProxy = nt.()  # dirListFunc() is provided by the resource

running, lastRun, lastRunTime = sm.getStatus(cur, "MtMonitor")
delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(lastRun)
mtMonRunLast = "%s" % delta
mtMonRunLast = mtMonRunLast.split(".")[0]

# mtMonRunLast = format_timedelta(delta, locale='en_US')

# for item in nt.dirNameProxy:



%>

<body>

<div>

	${sideBar.getSideBar(sqlCon)}
	<div class="maindiv">

		<div class="subdiv buMonId" style="padding: 5px;">
			<h3>Baka-Manga Updates</h3>
			<div>
				<div class="" style="white-space:nowrap; display: inline-block;">
					Filter items:
					<ul style="width: 100px;">
						<li> <a href="bmUpdates?filter=All">All Items</a></li>
						<li> <a href="bmUpdates?filter=notMP">Only not in MP</a></li>
						<li> <a href="bmUpdates?filter=inMP">Only in MP</a></li>

					</ul>
				</div>
				<div class="" style="white-space:nowrap; display: inline-block; margin-left: 10px;">
					Filter read status:
					<ul style="width: 100px;">

						<li> <a href="bmUpdates?readStatus=alldate">All read status</a></li>
						<li> <a href="bmUpdates?readStatus=upToDate">Up to date</a></li>
						<li> <a href="bmUpdates?readStatus=outOfDate">Out of date</a></li>
					</ul>
				</div>
				<div class="" style="white-space:nowrap; display: inline-block; margin-left: 10px; vertical-align:top">
					Filter Rating state:
					<ul style="width: 100px;">
						<li> <a href="bmUpdates">All rating state</a></li>
						<li> <a href="bmUpdates?hasRating=True">Has rating</a></li>
						<li> <a href="bmUpdates?hasRating=False">No Rating</a></li>
					</ul>
				</div>
				<div class="" style="white-space:nowrap; display: inline-block; margin-left: 10px; vertical-align:top">

					MT Monitor:
					<ul style="width: 100px;">

						<li>Last Update: ${mtMonRunLast}</li>
						<li> <a href="bmUpdates?updateMU=True">Force Update</a></li>
					</ul>
				</div>
				<div class="" style="white-space:nowrap; display: inline-block; margin-left: 80px; vertical-align:top">
					<table>
						<tr>
 							<td>Items in MT: </td>
							<td>${inMTcount}</td>
						</tr>
						<tr>
							<td>Items not in MT: </td>
							<td>${len(buItems) - inMTcount}</td>
						</tr>
						<tr>
							<td>Partial Rows: </td>
							<td>${badLinks}</td>
						</tr>
					</table>
				</div>

				<hr>
			% for key in keys:
				<div>
					<div style="margin-top: 10px;">
						<%
						inMtCnt = 0
						notMtCnt = 0
						for item in items[key]:
							if nt.cleanName(item["seriesName"]) in mtItems:
								inMtCnt += 1
							else:
								notMtCnt += 1

						%>
						<div style="display:inline;"><h4 style="display:inline;">List: ${key}</h4></div>
						<div style="display:inline; width:400px;">&nbsp;</div>
						<div style="display:inline;"> - ${len(items[key])} Item${"s" if len(items[key]) > 1 else ""}, In MT: ${inMtCnt}, Not in MT: ${notMtCnt}</div>
					</div>
					${genBmUpdateTable(items[key])}
				</div>
			% endfor
		</div>

	</div>
<div>


<%def name="makeTooltipTable(name, cleanedName, folderName)">
<ul>
	<li>Name: '${name | h}'</li>
	<li>Cleaned Name: '${cleanedName | h}'</li>
	<li>DirSort Name: '${folderName | h}'</li>
	% if folderName in nt.dirNameProxy:
		<li>Dir: '${nt.dirNameProxy[folderName]["fqPath"] | h}'</li>
	% endif
</ul>

</%def>

<%def name="genBmUpdateTable(tblData)">
	<table border="1px">
		<tr>
				<th class="padded" width="55">Bu ID</th>
				<th class="padded" width="300">Full Name</th>
				<th class="padded" width="300">Cleaned Name</th>
				<th class="padded" width="30">Rating</th>
				<th class="padded" width="30">MT It</th>
				<th class="padded" width="30">MU It</th>
				<th class="padded" width="35">In MT?</th>
				<th class="padded" width="50">Latest Chapter</th>
				<th class="padded" width="60">Read-To Chapter</th>
					</tr>

		% for dataDict in tblData:
			<%
				name = dataDict["seriesName"]
				cleanedName = nt.cleanName(dataDict["seriesName"])
				folderName = nt.dirNameProxy.filterNameThroughDB(cleanedName)
				folderName = folderName.lower()

				 # = nt.dirNameProxy.filterNameThroughDB(cleanedName)




				if folderName in nt.dirNameProxy:
					itemInfo = nt.dirNameProxy[folderName]
					if not itemInfo["rating"]:
						haveRating = "Unrated"
						if not showRatingMissing:
							continue
					if itemInfo["rating"]:
						haveRating = "Rated"
						if not showRatingFound:
							continue
					linkUrl = "<a href='/reader/{dictKey}/{seriesName}'>".format(dictKey=itemInfo["sourceDict"], seriesName=urllib.parse.quote(itemInfo["dirKey"]))
					rating = itemInfo["rating"]


				else:
					if not showRatingMissing:
						continue
					itemInfo = None
					rating = None
					linkUrl = None

					haveRating = "No Dir Found"

				# Funky short-circuiting stuff
				if cleanedName in mtItems and not showInMT:
					continue
				if not cleanedName in mtItems and not showNotInMT:
					continue

				if (dataDict["currentChapter"] > 1) and not showOutOfDate:
					continue
				if (dataDict["currentChapter"] == -1) and not showUpToDate:
					continue



			%>
			<tr>
				<td class="padded">${dataDict["mangaID"]}</td>
				<td class="padded">${name}</td>
				<td class="padded">${"" if linkUrl==None else linkUrl}${cleanedName} ${"" if not linkUrl else "</a>"}</td>

				% if haveRating == "Unrated":
					<td bgcolor="${colours["hasUnread"]}"  class="padded showTT" data-item="${makeTooltipTable(name, cleanedName, folderName)}">NR</td>
				% elif haveRating == "No Dir Found":
					<td bgcolor="${colours["notInMT"]}"  class="padded showTT" data-item="${makeTooltipTable(name, cleanedName, folderName)}">NDF</td>
				% else:
					<td class="padded showTT" data-item="${makeTooltipTable(name, cleanedName, folderName)}">${rating}</td>
				%endif


				% if dataDict["mtId"]:

					<td class="padded"><a href="http://www.mangatraders.com/manga/series/${dataDict["mtId"]}">MT</a></td>
				% else:
					<td class="padded"><a href="http://www.mangatraders.com/search/?term=${dataDict["seriesName"].replace(":", "")}&Submit=Submit&searchSeries=1">MT</a></td>
				% endif

				<td class="padded"><a href="http://www.mangaupdates.com/series.html?id=${dataDict["mangaID"]}">BU</a></td>

				% if dataDict["mtId"]:
					<td bgcolor="${colours["upToDate"]}" class="padded">Y</td>
				% else:
					<td bgcolor="${colours["notInMT"]}" class="padded">N</td>
				% endif

				% if dataDict["currentChapter"] == -1:
					% if dataDict["readChapter"] == -1:
						<td bgcolor="${colours["upToDate"]}" class="padded">✓</td>
					% else:
						<td bgcolor="${colours["upToDate"]}" class="padded">${dataDict["readChapter"]}</td>
					% endif
				% else:
					<td bgcolor="${colours["hasUnread"]}" class="padded">${dataDict["currentChapter"]}</td>
				% endif

				% if dataDict["readChapter"] == -1:
					<td class="padded">Finished</td>
				% else:
					<td class="padded">${dataDict["readChapter"]}</td>
				% endif
			</tr>
		% endfor

	</table>
</%def>



<%
stopTime = time.time()
timeDelta = stopTime - startTime
%>

<p>This page rendered in ${timeDelta} seconds.</p>

</body>
</html>
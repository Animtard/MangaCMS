﻿## -*- coding: utf-8 -*-
<!DOCTYPE html>

<%namespace name="ut" file="utilities.mako"/>
<%namespace name="ap" file="activePlugins.mako"/>

<%!
# Module level!

import re
import psycopg2
import psycopg2.extras
import time
import datetime
from babel.dates import format_timedelta
import os.path
import urllib.parse
import settings
import nameTools as nt
import uuid
import time
import sql
import sql.operators as sqlo

def compactDateStr(dateStr):
	dateStr = dateStr.replace("months", "mo")
	dateStr = dateStr.replace("month", "mo")
	dateStr = dateStr.replace("weeks", "w")
	dateStr = dateStr.replace("week", "w")
	dateStr = dateStr.replace("days", "d")
	dateStr = dateStr.replace("day", "d")
	dateStr = dateStr.replace("hours", "hr")
	dateStr = dateStr.replace("hour", "hr")
	dateStr = dateStr.replace("minutes", "m")
	dateStr = dateStr.replace("seconds", "s")
	dateStr = dateStr.replace("years", "yrs")
	dateStr = dateStr.replace("year", "yr")
	return dateStr

def fSizeToStr(fSize):

	fStr = fSize/1.0e6
	fStr = "%0.2f M" % fStr
	return fStr


# The two main content tables
mangaTable = sql.Table("mangaitems")
hentaiTable = sql.Table("hentaiitems")

mangaCols = (
		mangaTable.dbid,
		mangaTable.dlstate,
		mangaTable.sourcesite,
		mangaTable.sourceurl,
		mangaTable.retreivaltime,
		mangaTable.sourceid,
		mangaTable.seriesname,
		mangaTable.filename,
		mangaTable.originname,
		mangaTable.downloadpath,
		mangaTable.flags,
		mangaTable.tags,
		mangaTable.note
	)

hentaiCols = (
		hentaiTable.dbid,
		hentaiTable.dlstate,
		hentaiTable.sourcesite,
		hentaiTable.sourceurl,
		hentaiTable.retreivaltime,
		hentaiTable.sourceid,
		hentaiTable.seriesname,
		hentaiTable.filename,
		hentaiTable.originname,
		hentaiTable.downloadpath,
		hentaiTable.flags,
		hentaiTable.tags,
		hentaiTable.note
	)


# and the series table
seriesTable = sql.Table("mangaseries")


seriesCols = (
		seriesTable.dbId,
		seriesTable.buName,
		seriesTable.buId,
		seriesTable.buTags,
		seriesTable.buList,
		seriesTable.readingProgress,
		seriesTable.availProgress,
		seriesTable.rating,
		seriesTable.lastChanged
	)






# You must import utilities.mako for this to work!
# It relies on monkey-patching the sql.From class which is done in utilities.mako
def buildQuery(srcTbl, cols, **kwargs):

	# tableKey=None, tagsFilter=None, seriesFilter=None, seriesName=None):

	query = srcTbl.select(*cols, order_by = sql.Desc(srcTbl.retreivaltime))

	if "tableKey" in kwargs and kwargs['tableKey']:
		if type(kwargs['tableKey']) is str:
			query.addOr(srcTbl.sourcesite, kwargs['tableKey'])
		elif type(kwargs['tableKey']) is list or type(kwargs['tableKey']) is tuple:
			for key in kwargs['tableKey']:
				query.addOr(srcTbl.sourcesite, key)
		else:
			raise ValueError("Invalid table-key type! Type: '%s'" % type(kwargs['tableKey']))

	if "tagsFilter" in kwargs and kwargs['tagsFilter']:
		for tag in kwargs['tagsFilter']:
			query.addOrLike(srcTbl.tags, key)

	if "seriesFilter" in kwargs and kwargs['seriesFilter']:
		for key in kwargs['seriesFilter']:
			query.addAndLike(srcTbl.seriesName, key)

	if "seriesName" in kwargs and kwargs['seriesName']:
		addAnd(query, srcTbl.seriesname, kwargs['seriesName'])

	if "offset" in kwargs and kwargs['offset']:
		query.offset = int(kwargs['offset'])

	if "limit" in kwargs and kwargs['limit']:
		query.limit = int(kwargs['limit'])

	return query


colours = {
	# Download Status
	"failed"          : "000000",
	"no match"        : "FF9999",
	"moved"           : "FFFF99",
	"Done"            : "99FF99",
	"Uploaded"        : "90e0FF",
	"working"         : "9999FF",
	"queued"          : "FF77FF",
	"new dir"         : "FFE4B2",
	"error"           : "FF0000",

	# Categories

	"valid cat"  : "FFFFFF",
	"picked"    : "999999"
	}


%>


###############################################################################################################################################################################################################
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
###############################################################################################################################################################################################################


<%def name="fetchMangaItems(flags='', limit=100, offset=0, distinct=False, tableKey=None, seriesName=None, getErrored=False)">
	<%
		start = time.time()

		if distinct and seriesName:
			raise ValueError("Cannot filter for distinct on a single series!")

		if flags:
			raise ValueError("TODO: Implement flag filtering!")


		query = buildQuery(mangaTable, mangaCols, tableKey=tableKey, seriesName=seriesName)

		if getErrored:
			if query.where:
				query.where &= mangaTable.dlstate < 1
			else:
				query.where  = mangaTable.dlstate < 1

		else:
			if query.where:
				query.where &= mangaTable.dlstate < 3
			else:
				query.where  = mangaTable.dlstate < 3



		anonCur = sqlCon.cursor()
		anonCur.execute("BEGIN;")

		cur = sqlCon.cursor(name='test-cursor-1')
		cur.arraysize = 250


		query, params = tuple(query)
		print(query)
		print(params)
		cur.execute(query, params)

		if not limit:
			retRows = cur.fetchall()
		else:
			seenItems = []
			rowsBuf = cur.fetchmany()

			rowsRead = 0

			while len(seenItems) < offset:
				if not rowsBuf:
					rowsBuf = cur.fetchmany()
				if not rowsBuf:
					break
				row = rowsBuf.pop(0)
				rowsRead += 1
				if row[6] not in seenItems or not distinct:
					seenItems.append(row[6])

			retRows = []

			while len(seenItems) < offset+limit:
				if not rowsBuf:
					rowsBuf = cur.fetchmany()
				if not rowsBuf:
					break
				row = rowsBuf.pop(0)
				rowsRead += 1
				if row[6] not in seenItems or not distinct:
					retRows.append(row)
					seenItems.append(row[6])

		cur.close()
		anonCur.execute("COMMIT;")

		return retRows
	%>

</%def>


<%def name="renderRow(row)">

	<%

	dbId,              \
	dlState,           \
	sourceSite,        \
	sourceUrl,         \
	retreivalTime,     \
	sourceId,          \
	sourceSeriesName,  \
	fileName,          \
	originName,        \
	downloadPath,      \
	flags,             \
	tags,              \
	note = row

	dlState = int(dlState)

	if sourceSeriesName == None:
		sourceSeriesName = "NONE"
		seriesName = "NOT YET DETERMINED"
	else:
		seriesName = nt.getCanonicalMangaUpdatesName(sourceSeriesName)

	# cleanedName = nt.prepFilenameForMatching(sourceSeriesName)
	itemInfo = nt.dirNameProxy[sourceSeriesName]
	if itemInfo["rating"]:
		rating = itemInfo["rating"]
	else:
		rating = ""

	# clamp times to now, if we have items that are in the future.
	# Work around for some time-zone fuckups in the MangaBaby Scraper.
	if retreivalTime > time.time():
		retreivalTime = time.time()

	addDate = time.strftime('%y-%m-%d %H:%M', time.localtime(retreivalTime))

	if not flags:
		flags = ""
	if not tags:
		tags = ""

	if dlState == 2:
		statusColour = colours["Done"]
	elif dlState == 3:
		statusColour = colours["Uploaded"]
	elif dlState == 1:
		statusColour = colours["working"]
	elif dlState == 0:
		statusColour = colours["queued"]
	else:
		statusColour = colours["error"]


	if downloadPath and fileName:
		filePath = os.path.join(downloadPath, fileName)
		if "=0=" in downloadPath:
			if os.path.exists(filePath):
				locationColour = colours["no match"]
			else:
				locationColour = colours["moved"]
		elif settings.pickedDir in downloadPath:
			locationColour = colours["picked"]
		elif "newdir" in flags:
			locationColour = colours["new dir"]
		else:
			locationColour = colours["valid cat"]
	else:
		if dlState == 0:
			locationColour = colours["queued"]
		elif dlState == 3:
			locationColour = colours["valid cat"]
		elif dlState == 1:
			locationColour = colours["working"]
		else:
			locationColour = colours["failed"]
		filePath = "N.A."

	toolTip  = filePath.replace('"', "") + "<br>"
	toolTip += "Original series name: " + sourceSeriesName.replace('"', "") + "<br>"
	toolTip += "Proper MangaUpdates name: " + seriesName.replace('"', "") + "<br>"
	toolTip += "cleanedName: " + itemInfo["dirKey"] + "<br>"
	toolTip += "itemInfo: " + str(itemInfo).replace('"', "") + "<br>"
	toolTip += "rowId: " + str(dbId) + "<br>"
	toolTip += "sourceUrl: " + sourceUrl + "<br>"
	toolTip += "dlState: " + str(dlState) + "<br>"
	toolTip += "tags: " + str(tags) + "<br>"
	toolTip += "Source: " + str(sourceSite) + "<br>"
	if os.path.exists(filePath):
		toolTip += "File found."
	else:
		toolTip += "File is missing!"

	cellId = None
	if dlState < 0:
		cellId = uuid.uuid1(0).hex
	%>
	<tr class="${sourceSite}_row">
		<td>${ut.timeAgo(retreivalTime)}</td>
		<td bgcolor=${statusColour} class="showTT" title="${toolTip}" ${'onclick="event_%s()"' % cellId if cellId else ''}>
			%if dlState==3:
				<center>↑</center>
			%elif dlState < 0:
				<script>

					function ajaxCallback(reqData, statusStr, jqXHR)
					{
						console.log("Ajax request succeeded");
						console.log(reqData);
						console.log(statusStr);

						var status = $.parseJSON(reqData);
						console.log(status)
						if (status.Status == "Success")
						{

							alert("Succeeded!\n"+status.Message)
							// TODO Make this change the page locally, change the cell colours and stuff.
						}
						else
						{
							alert("ERROR!\n"+status.Message)
						}

					};


					function ${"event_%s()" % cellId}
					{
						var reset = window.confirm("Reset download state for item ${dbId}");
						if (reset == true)
						{
							var ret = ({});
							ret["reset-download"] = "${dbId}";
							$.ajax("/api", {"data": ret, success: ajaxCallback});
						}



					}
				</script>
			%endif
		</td>
		<td bgcolor=${locationColour} class="showTT" title="${toolTip}"></td>
		<td>${ut.createReaderLink(seriesName.title(), itemInfo)}</td>
		<td>${"<strike>" if "deleted" in tags else ""}${originName}${"</strike>" if "deleted" in tags else ""}</td>
		<td>${rating}</td>
		<td>${addDate}</td>
	</tr>


</%def>



<%def name="genMangaTable(flags        = '',
							limit      = 100,
							offset     = 0,
							distinct   = False,
							tableKey   = None,
							seriesName = None,
							getErrored = False)">


	<%


	with sqlCon.cursor() as cur:

		try:
			# ret = cur.execute(query, params)

			tblCtntArr = fetchMangaItems(flags, limit, offset, distinct, tableKey, seriesName, getErrored)

		# Catches are needed because if you don't issue a `rollback;`
		# future queries will fail until the rollback is issued.
		except psycopg2.InternalError:
			cur.execute("rollback;")
			raise
		except psycopg2.ProgrammingError:
			cur.execute("rollback;")
			raise


	print("Have data. Rendering.")
	%>

	<table border="1px" style="width: 100%;">
		<tr>
				<th class="uncoloured" style="width: 40px; min-width: 40px;">Date</th>
				<th class="uncoloured" style="width: 20px; min-width: 20px;">St</th>
				<th class="uncoloured" style="width: 20px; min-width: 20px;">Lo</th>
				<th class="uncoloured" style="width: 250px; min-width: 200px;">Series</th>
				<th class="uncoloured">BaseName</th>
				<th class="uncoloured" style="width: 45px; min-width: 45px;">Rating</th>
				<th class="uncoloured" style="width: 105px; min-width: 105px;">DLTime</th>
		</tr>

		% for row in tblCtntArr:
			${renderRow(row)}
		% endfor

	</table>
</%def>


###############################################################################################################################################################################################################
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
###############################################################################################################################################################################################################

<%!


def buildWhereQuery(tableKey=None, tagsFilter=None, seriesFilter=None, seriesName=None):

	# print("Building where query. tags=", tagsFilter, "series=", seriesFilter, "tableKey", tableKey)
	if tableKey == None:
		whereItems = []
		queryAdditionalArgs = []

	elif type(tableKey) is str:
		whereItems = ["sourceSite=%s"]
		queryAdditionalArgs = [tableKey]

	elif type(tableKey) is list or type(tableKey) is tuple:
		items = []
		queryAdditionalArgs = []
		for key in tableKey:
			items.append("sourceSite=%s")
			queryAdditionalArgs.append(key)

		selectStr = " OR ".join(items)    # Convert down to a single string
		selectStr = "(" + selectStr + ")" # and wrap it in parenthesis to make the OR work
		whereItems = [selectStr]
	else:
		raise ValueError("Invalid table-key type")

	tagsFilterArr = []
	if tagsFilter != None:
		for tag in tagsFilter:
			tagsFilterArr.append(" tags LIKE %s ")
			queryAdditionalArgs.append("%{s}%".format(s=tag.lower()))

	if tagsFilterArr:
		whereItems.append(" AND ".join(tagsFilterArr))

	seriesFilterArr = []
	if seriesFilter != None:
		for series in seriesFilter:
			seriesFilterArr.append(" seriesName LIKE %s ")
			series = nt.getCanonicalMangaUpdatesName(series)
			queryAdditionalArgs.append("%{s}%".format(s=series))

	seriesNameArr = []
	if seriesName != None:
		seriesFilterArr.append(" seriesName=%s ")
		series = nt.getCanonicalMangaUpdatesName(seriesName)
		queryAdditionalArgs.append("{s}".format(s=series))

	if seriesFilterArr:
		whereItems.append(" AND ".join(seriesFilterArr))
	if seriesNameArr:
		whereItems.append(" AND ".join(seriesNameArr))

	if whereItems:
		whereStr = " WHERE %s " % (" AND ".join(whereItems))
	else:
		whereStr = ""

	# print("tableKey, tagsFilter, seriesFilter", tableKey, tagsFilter, seriesFilter, whereItems)
	# print("Query", whereStr, queryAdditionalArgs)
	return whereStr, queryAdditionalArgs


%>

<%def name="genPronTable(siteSource=None, limit=100, offset=0, tagsFilter=None, seriesFilter=None, getErrored=False)">
	<table border="1px">
		<tr>

			<th class="uncoloured" width="5%">Date</th>
			<th class="uncoloured" width="3%">St</th>
			<th class="uncoloured" width="18%">Path</th>
			<th class="uncoloured" width="25%">FileName</th>
			<th class="uncoloured" width="30%">Tags</th>
			<th class="uncoloured" width="8%">Size</th>
			<th class="uncoloured" width="8%">DLTime</th>


		</tr>

	<%

	print("Table rendering begun")
	offset = offset * limit

	query = buildQuery(hentaiTable, hentaiCols,
		tableKey=siteSource,
		tagsFilter=tagsFilter,
		seriesFilter=seriesFilter,
		limit = limit,
		offset = offset)

	if getErrored:
		if query.where:
			query.where &= hentaiTable.dlState <= 0
		else:
			query.where  = hentaiTable.dlState <= 0








	with sqlCon.cursor() as cur:

		query, params = tuple(query)
		print(query)
		print(params)
		cur.execute(query, params)
		tblCtntArr = cur.fetchall()

		# print("Query")
		# ret = cur.execute('''SELECT 	dbId,
		# 								sourceSite,
		# 								dlState,
		# 								sourceUrl,
		# 								retreivalTime,
		# 								sourceId,
		# 								seriesName,
		# 								fileName,
		# 								originName,
		# 								downloadPath,
		# 								flags,
		# 								tags,
		# 								note
		# 							FROM HentaiItems
		# 							{query}
		# 							ORDER BY retreivalTime
		# 							DESC LIMIT %s
		# 							OFFSET %s;'''.format(query = whereStr), params)

		# tblCtntArr = cur.fetchall()
		# print("Queried")

	%>

	% for row in tblCtntArr:
		<%

		dbId,          \
		dlState,       \
		sourceSite,    \
		sourceUrl,     \
		retreivalTime, \
		sourceId,      \
		seriesName,    \
		fileName,      \
		originName,    \
		downloadPath,  \
		flags,         \
		tags,          \
		note = row

		dlState = int(dlState)

		# % for rowid, addDate, working, downloaded, dlName, dlLink, itemTags, dlPath, fName in tblCtntArr:

		addDate = time.strftime('%y-%m-%d %H:%M', time.localtime(retreivalTime))

		if not downloadPath and not fileName:
			fSize = -2
			filePath = "NA"

		else:
			try:
				filePath = os.path.join(downloadPath, fileName)
				if os.path.exists(filePath):
					fSize = os.path.getsize(filePath)
				else:
					fSize = -2
			except OSError:
				fSize = -1

		if  dlState == 2 and fSize < 0:
			statusColour = colours["failed"]
		elif dlState == 2:
			statusColour = colours["Done"]
		elif dlState == 1:
			statusColour = colours["working"]
		elif dlState == 0:
			statusColour = colours["queued"]
		else:
			statusColour = colours["failed"]

		if fSize == -2:
			fSizeStr = "No File"
		elif fSize < 0:
			fSizeStr = "Unk Err %s" % fSize

		else:
			fSizeStr = fSizeToStr(fSize)


		if not tags:
			tags = ""

		if seriesName and "»" in seriesName:
			seriesNames = seriesName.split("»")
		else:
			seriesNames = [str(seriesName)]



		%>
		<tr class="${sourceSite}_row">

			<td>${ut.timeAgo(retreivalTime)}</td>
			<td bgcolor=${statusColour} class="showTT" title="${dbId}, ${filePath}"></td>
			<td>
			## Messy hack that prevents the "»" from being drawn anywhere but *inbetween* tags in the path
				% for i, seriesName in enumerate(seriesNames):
					${'»'*bool(i)}
					<a href="/itemsPron?bySeries=${seriesName.strip()|u}">${seriesName}</a>
				% endfor
			</td>



			% if fSize <= 0:
				<td>${"<strike>" if "deleted" in tags else ""}${originName}${"</strike>" if "deleted" in tags else ""}</td>
			% else:
				<td><a href="/pron/read/${dbId}">${originName}</a></td>
			% endif


			% if tags != None:
				<td>

				% for tag in tags.split():
					<%
					tagname = tag.lower().replace("artist-", "") \
								.replace("scanlator-", "") \
								.replace("scanlators-", "") \
								.replace("parody-", "") \
								.replace("group-", "") \
								.replace("character-", "") \
								.replace("convention-", "") \
								.strip()
					highlight = False
					if not request.remote_addr in settings.noHighlightAddresses:
						for toHighlighTag in settings.tagHighlight:
							if toHighlighTag in tagname:
								highlight = True
					%>
					${"<b>" if highlight else ""}
					<a href="/itemsPron?byTag=${tagname|u}">${tag}</a>
					${"</b>" if highlight else ""}
				% endfor
				</td>
			% else:
				<td>(No Tags)</td>
			% endif

			% if fSize <= 0:
				<td bgcolor=${colours["no match"]}>${fSizeStr}</td>
			% else:
				<td>${fSizeStr}</td>
			% endif

			<td>${addDate}</td>

		</tr>
	% endfor

	</table>
</%def>


###############################################################################################################################################################################################################
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
###############################################################################################################################################################################################################



<%def name="genMangaSeriesTable(ignoreList=None, tagsFilter=None, seriesFilter=None, sortKey=None)">
	<table border="1px">
		<tr>

			<th class="uncoloured" width="5%">Last Update</th>
			<th class="uncoloured" width="2.5%">MuID</th>
			<th class="uncoloured" width="40%">Mu Name</th>
			<th class="uncoloured" width="5%">Rating</th>
			<th class="uncoloured" width="5%">Edit</th>


		</tr>



	<%

	whereStr, queryAdditionalArgs = buildWhereQuery(tagsFilter, seriesFilter)
	params = tuple(queryAdditionalArgs)


	if sortKey == "update":
		sortKey = "ORDER BY lastChanged DESC"
	elif sortKey == "buName":
		sortKey = "ORDER BY buName ASC"
	elif sortKey == "aggregate":
		sortKey = ""
	else:
		sortKey = "ORDER BY buName ASC"


	with sqlCon.cursor() as cur:
		query = '''SELECT 			dbId,
									buName,
									buId,
									buTags,
									buList,
									readingProgress,
									availProgress,
									rating,
									lastChanged
									FROM MangaSeries
									{query}
									{orderBy};'''.format(query=whereStr, orderBy=sortKey)

		# print ("Query = ", query)
		ret = cur.execute(query, params)
		tblCtntArr = cur.fetchall()

	ratingShow = "all"

	if "rated" in request.params:
		if request.params["rated"] == "unrated":
			ratingShow = "unrated"
		elif request.params["rated"] == "rated":
			ratingShow = "rated"

	def getSortKey(inArr):
		buName = inArr[1]
		return buName.lower()


	if not sortKey:
		# print("Aggregate sort")
		tblCtntArr.sort(key=getSortKey)


	%>

	% for row in tblCtntArr:


		<%
		dbId,            \
		buName,          \
		buId,            \
		buTags,          \
		buList,          \
		readingProgress, \
		availProgress,   \
		rating,          \
		lastChanged = row



		cleanedBuName = None

		if buName != None:
			cleanedBuName = nt.sanitizeString(buName)


		if buList in ignoreList:
			continue

		rating = ""


		buInfo = nt.dirNameProxy[cleanedBuName]
		if buInfo["item"] != None:
			rating = buInfo["rating"]

			# print("buInfo", buInfo)
		else:
			buInfo = None

		if ratingShow == "unrated" and rating != "":
			continue
		elif ratingShow == "rated" and rating == "":
			continue


		%>
		<tr id='rowid_${dbId}'>
			<td>${ut.timeAgo(lastChanged)}</td>
			<td>
				<span id="view">
					% if buId == None:
						<form method="post" action="http://www.mangaupdates.com/series.html" id="muSearchForm_${dbId}" target="_blank">
							<input type="hidden" name="act" value="series"/>
							<input type="hidden" name="session" value=""/>
							<input type="hidden" name="stype" value="Title">


							<a href="javascript: searchMUForItem('muSearchForm_${dbId}')">Search</a>
						</form>
					% else:
						${ut.idToLink(buId=buId)}
					% endif
				</span>
				<span id="edit" style="display:none"> <input type="text" name="buId" originalValue='${"" if buId == None else buId}' value='${"" if buId == None else buId}' size=5/> </span>
			</td>

			<td>
				<span id="view"> ${ut.createReaderLink(buName, buInfo)} </span>
				<span id="edit" style="display:none"> <input type="text" name="buName" originalValue='${"" if buName == None else buName}' value='${"" if buName == None else buName}' size=35/> </span>
			</td>
			<td> ${rating} </td>
			<td>
			<a href="#" id='buttonid_${dbId}' onclick="ToggleEdit('${dbId}');return false;">Edit</a>
			</td>

		</tr>
	% endfor

	</table>
</%def>


###############################################################################################################################################################################################################
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
###############################################################################################################################################################################################################



<%def name="genLegendTable(pron=False, hideSource=False)">
	<div class="legend">

		<table border="1px" style="width: 100%;">
			<colgroup>
				% for x in range(len(colours)):
					<col style="width: ${int(100/len(colours))}%" />
				% endfor
			</colgroup>
			<tr>
				% for key, value in colours.items():
					<td class="uncoloured legend">${key.title()}</td>
				% endfor
			</tr>
			<tr>
				% for key, value in colours.items():
					<td bgcolor="${value}"> &nbsp;</td>
				% endfor
			</tr>
		</table>
		<%

		rows = []
		if not hideSource:
			if not pron:
				for item in [item for item in ap.attr.sidebarItemList if item['type'] == "Manga"]:
					rows.append((item["name"], '{}_row'.format(item['dictKey'])))

			else:
				for item in [item for item in ap.attr.sidebarItemList if item['type'] == "Porn"]:
					rows.append((item["name"], '{}_row'.format(item['dictKey'])))
		%>
		<div>
			% for name, row in rows:
				<table border="1px" style="display:inline-block;">
						<tr class="${row}">
							<td style='padding-left: 5px; padding-right: 5px; width: 67px;'>From</td>
						</tr>
						<tr class="${row}">
							<td style='padding-left: 5px; padding-right: 5px; width: 67px;'>${name}</td>
						</tr>
				</table>
			% endfor
		</div>
	</div>

</%def>

## -*- coding: utf-8 -*-
<!DOCTYPE html>
<%!
# Module level!


import datetime
from babel.dates import format_timedelta

import statusManager as sm
import nameTools as nt

FAILED = -1
QUEUED = 0
DLING  = 1
DNLDED = 2

%>

<%namespace name="ut" file="utilities.mako"/>
<%namespace name="ap" file="activePlugins.mako"/>


<%def name="getSideBar(sqlConnection)">

	<%

	cur = sqlConnection.cursor()
	cur.execute("ROLLBACK;")

	# Counting crap is now driven by commit/update/delete hooks
	ret = cur.execute('SELECT sourceSite, dlState, quantity FROM MangaItemCounts;')
	rets = cur.fetchall()

	statusDict = {}
	for srcId, state, num in rets:
		if not srcId in statusDict:
			statusDict[srcId] = {}
		if not state in statusDict[srcId]:
			statusDict[srcId][state] = num
		else:
			statusDict[srcId][state] += num
		# print("row", srcId, state, num)
	# print("statusDict", statusDict)
	%>

	<div class="statusdiv">
		<div class="statediv navId">
			<strong>Navigation:</strong><br />
			<ul>
				<li><a href="/">Index</a>
				<hr>
				<hr>
				<li><a href="/reader2/browse/">Manga Reader</a>
				<hr>
				<li>${ut.createReaderLink("Random Manga", nt.dirNameProxy.random())}
				<hr>
				<hr>
				<li><a href="/bmUpdates">Baka Manga</a>
				<li><a href="/dirListing">Dir Listing</a>
				<hr>
				<li><a href="/seriesMon">Series Monitor</a>
				<hr>
				<li><a href="/itemsManga?distinct=True"><b>All Mangos</b></a>
				% for item in [item for item in ap.attr.sidebarItemList if item['type'] == "Manga"]:
					<li><a href="/itemsManga?sourceSite=${item["dictKey"]}&distinct=True">${item["name"]}</a>
				% endfor

				<hr>
				<hr>
				<li><a href="/itemsPron"><b>All Pron</b></a>
				% for item in [item for item in ap.attr.sidebarItemList if item['type'] == "Porn"]:
					<li><a href="/itemsPron?sourceSite=${item["dictKey"]}">${item["name"]}</a>
				% endfor
				<!-- <li><a href="/tagsFu">Fu Tags</a> -->
			</ul>
		</div>
		<br>

		<div class="statediv">
			<strong>Status:</strong>
		</div>

		% for item in ap.attr.sidebarItemList:
			<%
			if not item["renderSideBar"]:
				continue
			if not item["dbKey"]:
				continue
			vals = sm.getStatus(cur, item["dbKey"])
			if vals:
				running, runStart, lastRunDuration = vals[0]
				runStart = ut.timeAgo(runStart)
			else:
				running, runStart, lastRunDuration = False, "Never!", None

			if running:
				runState = "<b>Running</b>"
			else:
				runState = "Not Running"
			%>
			<div class="statediv ${item['cssClass']}">
				<strong>${item["name"]}</strong><br />
				${runStart}<br />
				${runState}

				% if item["dictKey"] != None:
					% if item["dictKey"] in statusDict:
						<ul>
							<li>Have: ${statusDict[item["dictKey"]][DNLDED]}</li>
							<li>DLing: ${statusDict[item["dictKey"]][DLING]}</li>
							<li>Want: ${statusDict[item["dictKey"]][QUEUED]}</li>
							<li>Failed: ${statusDict[item["dictKey"]][FAILED]}</li>
						</ul>
					% else:
						<b>WARN: No lookup dict built yet!</b>
					% endif
				% endif

			</div>
		% endfor
	</div>

</%def>

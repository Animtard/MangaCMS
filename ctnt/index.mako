## -*- coding: utf-8 -*-
<!DOCTYPE html>


<%namespace name="tableGenerators" file="gentable.mako"/>
<%namespace name="sideBar"         file="gensidebar.mako"/>
<%namespace name="ut"              file="utilities.mako"/>
<%namespace name="ap"              file="activePlugins.mako"/>

<html>
<head>
	<title>WAT WAT IN THE BATT</title>

	${ut.headerBase()}

	<script type="text/javascript">
		$(document).ready(function() {
		// Tooltip only Text
		$('.showTT').hover(function(){
			// Hover over code
			var title = $(this).attr('title');
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

<%
startTime = time.time()
print("Rendering begun")
%>



<%!
import time
import datetime
from babel.dates import format_timedelta
import os.path

%>
<body>


<div>
	${sideBar.getSideBar(sqlCon)}
	<div class="maindiv">

		<div class="subdiv skId">
			<div class="contentdiv">
				<h3>Manga (distinct)</h3>
				${tableGenerators.genLegendTable()}
				<%
				print("Calling tablegen")
				%>
				${tableGenerators.genMangaTable(distinct=True, limit=200)}
			</div>
		</div>

		<div class="subdiv fuFuId">
			<div class="contentdiv">
				<h3>Porn!</h3>
				${tableGenerators.genLegendTable(pron=True)}
				${tableGenerators.genPronTable()}
			</div>
		</div>

	</div>
</div>

<h2>
Shit to do:
</h2>
<p>
<b>General</b>
<ul>
	<li>Queue whole of any new series on batoto when a rating is found that's >= "++"</li>
	<li>scrape mangacow</li>
	<li>itemsManga page isn't using activePlugins.mako</li>
	<li>Also the itemsPron page.</li>
	<li>proxy for name lookups.</li>
	<li>Prevent full base dir refresh on directory rename.</li>
	<li>Trigger full series download if a series is seen by a scraper, and the local directory is both found, and rated above a threshold</li>
	<li>Deduper - enable the ability to check for duplicates using phash as well. (Partial - Needs ability to search by hamming distance to work properly)</li>
	<li>add ability to sort directory by rating.</li>
	<li>Modularize the side-bar in the manga browser, so the plugins can each provide their own lookup interface if they present the correct API (should be automatically discovered, ideally).</li>
	<li>Ability to disable bulk-downloading.</li>
	<li>Add failed item introspection table.</li>
	<br>
</ul>
</p>
<p>
<b>Reader</b>
<ul>
bu readstate in sidebar.
	<li>Add ability to rename directories to reader</li>
	<li>Add current page position bar when popup menus are visible.</li>
	<li>Make zoom mode a bit more intelligent (e.g. look at aspect ratio to guess zoom mode).</li>
	<li>Trigger directory cache update if a non-existent directory access is attempted</li>
</ul>
</p>

<p>
<b>File System Organization</b>
<ul>
	<li>Coerce directory structure to match MangaUpdates naming.</li>
	<li>Scrape ALL MangaUpdates metadata, and use that to group series when different sources use different naming schemes. (WIP)</li>
	<li>Automatically organize and sort directories so each series only has one directory. Aggregate multiple directories so they're named in accord with MangaUpdates
	naming approach. Note <b> this makes MangaUpdates the final authority on what to refer to series as. Deal with it</b></li>

</ul>
</p>
<p>

<b>Complete:</b>
<ul>
	<li><strike>Deduper - Check that local duplicate of file found via DB still exists before deleting new downloads.</strike></li>
	<li><strike>Scrape Fakku</strike></li>
	<li><strike>optimise name cleaning.</strike> Spent some time profiling. Not worth the effort (not much room for improvement).</li>
	<li><strike>optimize optimize optimize! 1 second for home rendering.</strike> (~0.5 seconds! Woot!)</li>
	<li><strike>mangafox if they dont resize.</strike> Never mind. they took down all their Manga because licensing reasons, apparently?</li>
	<li><strike>clean ! from matching system.</strike> (Was already done)</li>
	<li><strike>split porn/nonporn again?</strike></li>
	<li><strike>Fix BU Watcher login issues.</strike> Cookies are the fucking bane of my existence.</li>
	<li><strike>Add planned routes to look into the various tables (can I share code across the various query mechanisms?) (Mostly complete)</strike>(I'm calling this complete, since I only have two table-generator calls ATM)</li>
	<li><strike>Scrape download.japanzai.com</strike></li>
	<li><strike>Fix rating change facility being broken by the new reader</strike></li>
	<li><strike>Finish reader redesign</strike></li>
	<li><strike>Fix presetting of item rating field.</strike> (Accidentally fixed, I think? Not sure how, but it's now working.)</li>
	<li><strike>reader shits itself on unicode urls.</strike></li>
	<li><strike>Allow arbitrarily nested folders in reader. (added in new reader)</strike></li>
	<li><strike>Prefferentially rescan MangaUpdates series that got releases today (e.g. scan https://www.mangaupdates.com/releases.html).</strike></li>
	<li><strike>also pururin.com</strike></li>
	<li><strike>pagechange buttons for porn broken in some instances.</strike></li>
	<li><strike>MangaUpdates name lookup passthrouth in nametools.</strike></li>
	<li><strike>fukkit, scrape batoto.</strike></li>
	<li><strike>Add legend key for what row colours mean (easy).</strike></li>
	<li><strike>Add better time-stamp granularity to Starkana Scraper.</strike> (I think?)</li>
	<li><strike>MangaBaby.com scraper</strike></li>
	<li><strike>Flatten any found duplicate directories, when they span more then one of the manga-folders.</strike></li>
	<li><strike>FIX NATURAL SORTING</strike></li>
	<li><strike>Make series monitoring tool for MT update periodically</strike></li>
	<li><strike>Automated tag update mechanism!</strike></li>
	<li><strike>Commit hooks to track the number of items in the mangaTable, without the massive overhead `SELECT COUNT(*)` has on SQLite (this should be fun and educational in terms of SQL).</strike></li>
	<li><strike>Generalize the image-cleaner to remove all annoying batoto/starkana/whatever images from downloaded archives. Possibly make it possible to run in batch mode? It should have a local directory of "bad" images that are scanned on start, and compare using hashes (or full on bitwise?).</strike></li>
	<li><strike>Scrape perveden.com</strike> Fuck them, they watermark their shit. Never mind.</li>
</ul>
</p>

<%
stopTime = time.time()
timeDelta = stopTime - startTime
%>

<p>This page rendered in ${timeDelta} seconds.</p>

</body>
</html>
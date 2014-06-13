## -*- coding: utf-8 -*-
<!DOCTYPE html>
<%startTime = time.time()%>

<%namespace name="tableGenerators" file="/gentable.mako"/>
<%namespace name="sideBar" file="/gensidebar.mako"/>


<%!
# Module level!
import time
import datetime
from babel.dates import format_timedelta
import os.path
import os


import magic
from operator import itemgetter

import nameTools as nt
import unicodedata
import traceback
import settings
import urllib.parse

styles = ["mtMainId", "mtSubId", "djMoeId", "fuFuId"]

def dequoteDict(inDict):
	ret = {}
	for key in inDict.keys():
		ret[key] = urllib.parse.unquote_plus(inDict[key])
	return ret

%>




<%def name="showMangaItems(filePath, keyUrls)">



	<html style='html: -ms-content-zooming: none; /* Disables zooming */'>
		<head>
			<meta charset="utf8">
			<meta name="viewport" content="width=device-width; initial-scale=1.0; maximum-scale=1.0; user-scalable=0; width=device-width;">

			<meta name="mobile-web-app-capable" content="yes">
			<meta name="apple-mobile-web-app-capable" content="yes">
			<meta name="apple-mobile-web-app-status-bar-style" content="black">

			<title>Reader (${filePath.split("/")[-1]})</title>

			<script src="/js/jquery-2.1.1.js"></script>
			<script src="/comicbook/js/comicbook.js"></script>
			<link rel="stylesheet" href="/nozoom.css">
			<link rel="stylesheet" href="/comicbook/comicbook.css">
			<link rel="shortcut icon" sizes="196x196" href="/comicbook/img/icon_196.png">
			<link rel="apple-touch-icon" sizes="196x196" href="/comicbook/img/icon_196.png">
			<link rel="apple-touch-icon-precomposed" sizes="196x196" href="/comicbook/img/icon_196.png">


		</head>
		<body>
			<div style="line-height: 0;" id="canvas_container"></div>
			<!-- <div id="canvas_container"></div> -->
			<!-- <canvas id="comic"></canvas> -->


			<script>

				var book = new ComicBook('canvas_container', [


					${", ".join(keyUrls)}


				], {

				});

				book.draw();

				$(window).on('resize', function () {
					book.draw();
				});
			</script>
		</body>
	</html>


</%def>



<%def name="invalidKey()">

	<html>
		<head>
			<title>WAT WAT IN THE READER</title>
			<link rel="stylesheet" href="/style.css">
			<script type="text/javascript" src="/js/jquery-2.1.0.min.js"></script>

		</head>



		<body>


			<div>
				${sideBar.getSideBar(sqlCon)}
				<div class="maindiv">
					<div class="contentdiv subdiv uncoloured">
						<h3>Reader!</h3>
						${invalidKeyContent()}
					</div>
				</div>
			<div>

		</body>
	</html>


</%def>



<%def name="invalidKeyContent()">

						<div class="errorPattern">
							<h3>Invalid Manga file specified!</h3>
							Are you trying to do something naughty?<br>

							<pre>${request.matchdict}</pre>
							<pre>${request.path}</pre>

							<a href="/reader/">Back</a>
						</div>

</%def>



<%def name="badFileError(itemPath)">

	<html>
		<head>
			<title>WAT WAT IN THE READER</title>
			<link rel="stylesheet" href="/style.css">
			<script type="text/javascript" src="/js/jquery-2.1.0.min.js"></script>

		</head>



		<body>


			<div>
				${sideBar.getSideBar(sqlCon)}
				<div class="maindiv">
					<div class="contentdiv subdiv uncoloured">
						<h3>Reader!</h3>

						<div class="errorPattern">
							<h3>Specified file is damaged?</h3>
							<pre>${traceback.format_exc()}</pre><br>
						</div>

						<div class="errorPattern">
							<h3>File info:</h3>
							<p>Exists = ${os.path.exists(itemPath)}</p>
							<p>Magic file-type = ${magic.from_file(itemPath).decode()}</p>
						</div>
						<a href="/reader/">Back</a>
					</div>
				</div>
			<div>

		</body>
	</html>

</%def>


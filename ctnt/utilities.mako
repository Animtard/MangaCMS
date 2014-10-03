
<%!
# Module level!
import time
import datetime
import os.path


import re
import urllib.parse
import nameTools as nt




import sql

class ProceduralSelect(sql.Select):
	def addAnd(self, col, param):
		if not self.__where:
			self.__where = (col == param)
		else:
			self.__where &= (col == param)


	def addOr(self, col, param):
		if not self.__where:
			self.__where = (col == param)
		else:
			self.__where |= (col == param)

	def addAndLike(self, col, param):
		if not self.__where:
			self.__where = sqlo.Like(col, param)
		else:
			self.__where &= sqlo.Like(col, param)

	def addOrLike(self, col, param):
		if not self.__where:
			self.__where = sqlo.Like(col, param)
		else:
			self.__where |= sqlo.Like(col, param)


# Modify the sql.From class to use our derived ProceduralSelect class,
# that lets one add parameters proceedurally.
class From(sql.From):

	def select(self, *args, **kwargs):
		return ProceduralSelect(args, from_=self, **kwargs)


# Monkey-patch in the modified From
# This is HORRIBLE, and I should FEEL BAD!
# (It does work, though)
sql.From=From





%>






<%def name="timeAgo(inTimeStamp)">
	<%
	if inTimeStamp == None:
		return "NaN"
	delta = int(time.time() - inTimeStamp)
	if delta < 60:
		return "{delta} s".format(delta=delta)
	delta = delta // 60
	if delta < 60:
		return "{delta} m".format(delta=delta)
	delta = delta // 60
	if delta < 24:
		return "{delta} h".format(delta=delta)
	delta = delta // 24
	if delta < 999:
		return "{delta} d".format(delta=delta)
	delta = delta // 365
	return "{delta} y".format(delta=delta)



	%>
</%def>



<%def name="idToLink(buId=None, mtId=None)">
	<%

	if mtId:
		return "<a href='http://www.mangatraders.com/manga/series/{id}'>{id}</a>".format(id=mtId)
	elif buId:
		return "<a href='http://www.mangaupdates.com/series.html?id={id}'>{id}</a>".format(id=buId)
	else:
		return ""

	%>
</%def>




<%def name="createReaderLink(itemName, itemInfo)">
	<%

	if itemInfo == None or itemInfo["item"] == None:
		if itemName:
			return itemName
		else:
			return ""

	return "<a href='/reader2/browse/0/%s'>%s</a>" % (urllib.parse.quote(itemInfo["dirKey"].encode("utf-8")), itemName)

	%>
</%def>




<%def name="getCss()">

	<link rel="stylesheet" href="/style.mako.css">
</%def>



<%def name="headerBase()">
	${getCss()}
	<script type="text/javascript" src="/js/jquery-2.1.0.min.js"></script>
	<script>

		function searchMUForItem(formId)
		{

			var form=document.getElementById(formId);
			form.submit();
		}

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

</%def>


<%def name="nameToBuSearch(seriesName, linkText='Manga Updates')">
	<%
		# Add hash to the function name to allow multiple functions on the same page to coexist.
		# Will probably collide if multiple instances of the same link target exist, but at that point, who cares? They're the same link target, so
		# therefore, the same search anyways.

		itemHash = abs(hash(seriesName))

		buLink = '<a href="javascript: searchMUForItem_%d()">%s</a>' % (itemHash, linkText)
		buLink += '<script>function searchMUForItem_%d(){ var form=document.getElementById("muSearchForm"); form.submit(); }</script>' % itemHash
		return buLink
	%>
</%def>

<%def name="nameToMtSearch(seriesName, linkText='Manga Traders')">
	<%
		link = '<a href="http://www.mangatraders.com/search/?term=%s&Submit=Submit&searchSeries=1">%s</a>' % (urllib.parse.quote(seriesName), linkText)
		return link
	%>
</%def>


<%def name="getItemInfo(seriesName)">
	<%
	with sqlCon.cursor() as cur:
		ret = cur.execute("SELECT buId,buTags,buGenre,buList,readingProgress,availProgress  FROM MangaSeries WHERE buName=%s;", (seriesName, ))
		rets = cur.fetchall()
	if not rets:
		buId, buTags, buGenre, buList, readProgress, availProgress = None, None, None, None, None, None
	else:
		buId, buTags, buGenre, buList, readProgress, availProgress = rets[0]
	# print("Looked up item %s, ret=%s" % (seriesName, buId))

	if buId:
		haveBu = True
		buLink = '<a href="http://www.mangaupdates.com/series.html?id=%s">Manga Updates</a>' % buId
	else:
		haveBu = False
		buLink = nameToBuSearch(seriesName)

	return (buId, haveBu, buLink, buTags, buGenre, buList, readProgress, availProgress)
	%>
</%def>





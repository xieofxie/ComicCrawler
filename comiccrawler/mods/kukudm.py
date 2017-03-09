#! python3
"""
http://www.kukudm.com/comiclist/2055/index.htm

"""

import re,execjs

from ..core import Episode
from urllib.parse import urljoin

domain = ["www.kukudm.com"]
name = "kukudm"

def get_title(html,url):
	title = re.search("<title>(.+?)漫画在线_在线漫画",html).group(1)
	print(title)
	return title

def get_episodes(html, url):
	#so it is different from chrome!!
	#print(html)
	s = []
	for match in re.finditer("<A href='/comiclist/(.+?)' target='_blank'>(.+?)</A>",html):
		ep_url,title = match.groups()
		s.append(Episode(title,urljoin('http://www.kukudm.com/comiclist/',ep_url)))
		#print(ep_url)
	return s

def get_images(html,url):
	#print(html)
	#http://n.kukudm.com/newkuku/2016/04/17/极黑 EP181修正/0-0010ED.jpg
	#document.write("<IMG SRC='"+m201304d+"newkuku/2016/04/17/ 极黑 EP181修正/0-0010ED.jpg'><span style='display:none'><img src='"+m201304d+"newkuku/2016/04/17/极黑 EP181修正/0-0020DR.jpg'></span>");
	pic = 'http://n.kukudm.com/'+re.search("document.write[(]\"<IMG SRC='\"[+]m(.+?)d[+]\"(.+?)'><span",html).group(2)
	print(pic)
	return pic

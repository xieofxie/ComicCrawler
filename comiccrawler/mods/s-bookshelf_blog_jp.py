#! python3

"""this is s-bookshelf.blog.jp module for comiccrawler

Ex:
	http://s-bookshelf.blog.jp/archives/cat_1078018.html

"""

import re

from urllib.parse import urljoin

from ..core import Episode

domain = ["s-bookshelf.blog.jp"]
name = "s-bookshelf.blog.jp"

def get_title(html, url):
	return re.search(r'<h1>([^<]*)</h1>', html).group(1).strip()

def get_episodes(html, url):
	titles = []
	for match in re.finditer(r"<h1 itemprop=\"name\">([^<]+)<", html):
		title = match.groups()[0]
		titles.append(title)
	urls = []
	for match in re.finditer(r"<a href=\"([^\"]+)\" itemprop=\"url\"><img", html):
		url = match.groups()[0]
		urls.append(url)
	arr = zip(titles, urls)
	return [Episode(title, url) for title, url in arr]
	
def get_images(html, url):
	ret = []
	for match in re.finditer(r"<a ([^>]+)>", html):
		m = re.search(r"href=\"([^\"]+)\" title=\"[^\"]+\" target=\"_blank\"", match.group(1))
		if not m:
			m = re.search(r"target=\"_blank\" title=\"[^\"]+\" href=\"([^\"]+)\"", match.group(1))
		if m:
			ret.append(m.group(1))
	return ret

def get_next_page(html, url):
	print('get_next_page', url)
	match = re.search(r"現在の表示ページ\"><span>\d+</span></li><li><a href=\"([^\"]+)", html)
	if match:
		print(match.group(1))
		return urljoin(url, match.group(1))

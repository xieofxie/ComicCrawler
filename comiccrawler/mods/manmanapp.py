#! python3

"""this is manmanapp module for comiccrawler

Ex:
	http://m.manmanapp.com/comic-581.html

"""

import re,requests
from html import unescape
from urllib.parse import urljoin
from ..core import Episode

domain = ["m.manmanapp.com"]
name = "漫漫"

def get_title(html, url):
	name = re.search('<li class="title">([^<]+)<', html).group(1)
	author = re.search('<li class="author">作者：<[^<]+>(.+)</a></li>', html).group(1)
	return name + '_' + author

def get_episodes(html, url):
	id = re.search('{id:(\d+)',html).group(1)
	url = "http://m.manmanapp.com/works/comic-list-ajax.html"
	data = {'id':int(id),'sort':1}
	page = 1
	s = []
	while True:
		data['page'] = page
		r = requests.post(url,data).json()
		if r['code'] != 1:
			break
		for item in r['data']:
			title = item['title']
			link = 'http://m.manmanapp.com/comic/detail-'+item['id']+'.html'
			s.append(Episode(title,link))
		page += 1
	return s	

def get_images(html, url):
	return re.findall('<li><img data-original="([^"]+)" src=', html)
#! python3

"""
http://www.ccdm1.com/manhua/20616/
"""

import re
import chardet
import sys, locale, os, codecs
from urllib.parse import urljoin, urlencode

from node_vm2 import VM, eval

from ..core import Episode, grabhtml

domain = ["ccdm1.com"]
name = "CC漫画网"

def get_title(html, url):
	return re.search(r'<h1>([^<]*)', html).group(1)

def get_list(html, cid):
	ep_re = r'href="(/manhua/{}/\d+\.html)" title="([^"]+)"'.format(cid)
	arr = []
	try:
		comment_pos = html.index('class="comment-bar"')
	except ValueError:
		comment_pos = len(html)

	for match in re.finditer(ep_re, html):
		if match.start() >= comment_pos:
			break
		ep_url, title = match.groups()
		arr.append((title, ep_url))
	return arr

def get_episodes(html, url):
	episodes = None
	cid = re.search(r"[mM]anhua/(\d+)", url).group(1)
	episodes = get_list(html, cid)
	episodes = [Episode(v[0].strip(), urljoin(url, v[1])) for v in episodes]
	return episodes[::-1]
	
#https://stackoverflow.com/questions/492483/
def print_utf8(*args, **kwargs):
	if False:
		print(sys.stdout.encoding)
		print(sys.stdout.isatty())
		print(locale.getpreferredencoding())
		print(sys.getfilesystemencoding())
	stdout_old = sys.stdout
	sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
	print(*args, **kwargs)
	sys.stdout = stdout_old

def get_images(html, url):
	#print(html.encode('gbk','ignore').decode('gbk'))
	js = re.search(r'<script type="text/javascript">(var cInfo =[^;]+;)',html).group(1)
	with VM(js) as vm:
		files = vm.run("cInfo.fs")
	#http://www.ccdm1.com/Public/manhuadao/js/configs.js?v=0731
	server = 'http://ccimg1.61mh.com'
	images = ["{server}{file}".format(server=server, file=i) for i in files]
	return images

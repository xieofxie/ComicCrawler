#! python3

"""Comic Crawler."""

VERSION = "20140709"

import re
from safeprint import safeprint

import urllib.request
import urllib.parse
import urllib.error

from safeprint import safeprint

INIT = 0
ANALYZED = 1
DOWNLOADING = 2
PAUSE = 3
FINISHED = 4
ERROR = 5
INTERRUPT = 6
UPDATE = 7
ANALYZING = 8

from queue import Queue
messageBucket = Queue()
def _evtcallback(msg, *args):
	"""Message collector"""
	
	messageBucket.put((msg, args))
	
def getext(byte):
	"""Test the file type according byte stream with imghdr
	
	imghdr issue: http://bugs.python.org/issue16512
	"""
	
	import imghdr
	r = imghdr.what("", byte)
	if r:
		if r.lower() == "jpeg":
			return "jpg"
		return r.lower()
	
	h = byte
	if h[:2] == b"\xff\xd8":
		return "jpg"
	
	if h[:3] == b"CWS" or h[:3] == b"FWS":
		return "swf"

	if h[:4] == b"8BPS":
		return "psd"

	if h[:7] == b"Rar!\x1a\x07\x00":
		return "rar"
		
	return None
			
def createdir(path):
	"""Create folder of filepath. 
	
	This function can handle sub-folder like 
	"this_doesnt_exist\sure_this_doesnt_exist_either\I_want_to_create_this"
	
	"""
	import os, re
	
	path = os.path.normpath(path)
	
	dirpath = re.split(r"[\\/]+", path)
	create = ""
	for d in dirpath:
		if not d:
			continue
		create += d + os.sep
		if not os.path.exists(create):
			os.mkdir(create)

def safefilepath(s):
	"""Return a safe directory name. Return string."""

	return re.sub("[/\\\?\|<>:\"\*]","_",s).strip()
	
def safeurl(url):
	"""Return a safe url, quote the unicode characters."""
	
	base = re.search("(https?://[^/]+)", url).group(1)
	path = url.replace(base, "")
	def u(match):
		return urllib.parse.quote(match.group())
	path = re.sub("[\u0080-\uffff]+", u, path)
	return base + path
	
def grabhtml(url, hd={}, encode=None):
	"""Get html source of given url. Return String."""
	
	url = safeurl(url)
	req = urllib.request.Request(url,headers=hd)
	rs = urllib.request.urlopen(req, timeout=20)
	ot = rs.read()
	
	if not encode:
		try:
			encode = re.search(r"<meta charset=[\"']?([^\"'>]+)[\"']?").group(1)
			return ot.decode(encode, "replace")
		except Exception:
			pass
		try:
			encode = re.search("charset=([^\"'>]+)",ot.decode("utf-8","replace")).group(1)
			return ot.decode(encode, "replace")
		except Exception:
			return ot.decode("utf-8", "replace")
	else:
		return ot.decode(encode,"replace")

def grabimg(url, hd={}):
	"""Return byte stream."""
	
	url = safeurl(url)
	req = urllib.request.Request(url, headers=hd)
	rs = urllib.request.urlopen(req, timeout=20)
	return rs.read()

class Mission:
	"""Mission data class. Contains a mission's information."""
	
	def __init__(self):
		"""Use title, url, episodelist, state, downloader, lock"""
		from threading import Lock
		
		self.title = ""
		self.url = ""
		self.episodelist = []
		self.state = INIT
		self.downloader = None
		self.lock = Lock()
		self.update = False
		
	def state_(self, state=None):
		"""Call this method to make a MISSION_STATE_CHANGE message"""
		
		if not state:
			return self.state
		self.state = state
		_evtcallback("MISSION_STATE_CHANGE", self)
			
	def __getstate__(self):
		"""pickle"""
	
		state = self.__dict__.copy()
		del state["downloader"]
		del state["lock"]
		return state
		
	def __setstate__(self, state):
		"""unpickle"""
		from threading import Lock
		
		self.__dict__.update(state)
		self.lock = Lock()
		
	def setTitle(self, title):
		"""set new title"""
		
		self.title = title
		_evtcallback("MISSION_TITLE_CHANGE", self)
		
	def set(self, **kwargs):
		"""Set new attribute, may replace setTitle later."""
		
		for key, value in kwargs.items():
			if key in self:
				setattr(self, key, value)

class Episode:
	"""Episode data class. Contains a book's information."""
	
	def __init__(self):
		"""init"""
		
		self.title = ""
		self.firstpageurl = ""
		self.currentpageurl = ""
		self.currentpagenumber = 0
		self.skip = False
		self.complete = False
		self.error = False
		self.errorpages = 0
		self.totalpages = 0

		
class Worker:
	"""wrap Thread class
	
	Inherit this class so you can run as thread.
	It will auto reset after stopping. So it could start again.
	"""
	
	def __init__(self, callback=None):
		"""init"""
		
		if callable(callback):
			self.callback = callback
		self.running = False
		self._stop = False
		self.threading = None
		
	def callback(self, *args, **kwargs):
		pass
		
	def worker(self):
		"""should be overwrite"""
		
		# after doing something?
		self.callback()
		
		# reset it if you want to reuse the worker
		self.reset()
		
	def start(self):
		"""call this method and self.worker will run in new thread"""
	
		import threading
		if self.running:
			return False
		self.running = True
		self.threading = threading.Thread(target=self.worker)
		self.threading.start()
		
	def reset(self):
		"""reset state so you can start it again"""
		
		self.running = False
		self._stop = False
		self.threading = None
	
	def stop(self):
		"""Warning! stop() won't block. 
		
		you should use join() to ensure the thread was killed.
		"""
		
		self._stop = True
		
	def pausecallback(self):
		"""Hook to stop worker thread.
		
		you should call this method in worker when meeting a break point.
		"""		
		
		if self._stop:
			raise InterruptError
			
	def join(self):
		"""thread join method."""
		
		self.threading.join()

		
class DownloadWorker(Worker):
	"""The main core of Comic Crawler"""

	def __init__(self, mission=None, savepath=".", callback=None):
		"""set the mission"""
		
		super().__init__(callback)
		self.mission = mission
		self.savepath = savepath
	
	def worker(self):
		"""download worker"""
		
		try:
			self.mission.lock.acquire()
			self.download(self.mission, self.savepath)
		except Exception as er:
			self.mission.state = ERROR
			self.callback(self.mission, er)
		else:
			self.mission.state = ANALYZED
			self.callback(self.mission)
		finally:
			self.mission.lock.release()

	def download(self, mission, savepath):
		"""Start mission download. This method will call cls.crawlpage()
		for each episode.
		
		"""
		
		safeprint("total {} episode.".format(len(mission.episodelist)))
		for ep in mission.episodelist:
			if ep.skip or ep.complete:
				continue
				
			# deside wether to generate Episode folder, or it will put every 
			# image file in one folder. Ex. pixiv.net
			if ("noepfolder" in mission.downloader.__dict__ and 
					mission.downloader.noepfolder):
				efd = "{}\\{}\\".format(savepath, safefilepath(mission.title))
				fexp = safefilepath(ep.title) + "_{:03}"
			else:
				efd = "{}\\{}\\{}\\".format(savepath, safefilepath(mission.title), safefilepath(ep.title))
				fexp = "{:03}"
			createdir(efd)
			
			safeprint("Downloading ep {}".format(ep.title))
			try:
				self.crawlpage(ep, efd, mission, fexp)
			except LastPageError:
				safeprint("Episode download complete!")
				print("")
				ep.complete = True
				_evtcallback("DOWNLOAD_EP_COMPLETE", mission, ep)
				"""
			except InterruptError:
				safeprint("Download interrupted.")
				mission.state_(PAUSE)
				self.crawler.save()
				break
				"""
		else:
			safeprint("Mission complete!")
			mission.state_(FINISHED)
			mission.update = False

	def crawlpage(self, ep, savepath, mission, fexp):
		"""Crawl all pages of an episode.
		
		Grab image into savepath. To exit the method, raise LastPageError.
		
		Should define error handler for grabimg failed. Note the error by
		setting episode.errorpages, episode.currentpagenumber, episode.
		totalpages, episode.currentpageurl.
		
		"""
		import time
		
		downloader = mission.downloader
		
		if not ep.currentpagenumber:
			ep.currentpagenumber = 1
		if not ep.currentpageurl:
			ep.currentpageurl = ep.firstpageurl
			
		imgurls = None
		if "getimgurls" in downloader.__dict__:
			# we can get all img urls from first page
			errorcount = 0
			while not imgurls:
				try:
					html = grabhtml(ep.firstpageurl, hd=downloader.header)
					imgurls = downloader.getimgurls(html, url=ep.firstpageurl)
				except Exception as er:
					safeprint("get imgurls failed: {}".format(er))
					errorcount += 1
					if errorcount >= 10:
						raise TooManyRetryError
					if "errorhandler" in downloader.__dict__:
						downloader.errorhandler(er, ep)
					self.pausecallback()
					
					time.sleep(5)
					
		ep.imgurls = imgurls
		
		# some file already in directory
		import os
		createdir(savepath)
		downloadedlist = [ i.rpartition(".")[0] for i in os.listdir(savepath) ]
		
		# crawl all pages
		errorcount = 0
		while True:
			safeprint("Crawling {} {} page {}...".format(mission.title, 
					ep.title, ep.currentpagenumber))
			try:
				if not imgurls:
					# getimgurl method
					html = grabhtml(ep.currentpageurl, hd=downloader.header)
					
					imgurl = downloader.getimgurl(html, 
							page=ep.currentpagenumber, url=ep.currentpageurl)
					nextpageurl = downloader.getnextpageurl(ep.currentpagenumber, 
							html, url=ep.currentpageurl)
					try:
						imgurl, header = imgurl
					except Exception:
						header = downloader.header
				else:
					# getimgurls method
					imgurl = imgurls[ep.currentpagenumber - 1]
					header = downloader.header
					nextpageurl = ep.currentpagenumber < len(imgurls)
				
				# generate file name
				fn = fexp.format(ep.currentpagenumber)
				
				# file already exist
				if fn in downloadedlist:
					raise FileExistError
					
				safeprint("Downloading image: {}".format(imgurl))
				oi = grabimg(imgurl,hd=header)
				
				# check image type
				ext = getext(oi)
				if not ext:
					raise Exception("Invalid image type.")
					
			except FileExistError:
				safeprint("...page {} already exist".format(
						ep.currentpagenumber))
						
			except Exception as er:
				safeprint("Crawl page error: {}".format(er or type(er)))
				errorcount += 1
				if errorcount >= 10:
					# self.crawler.missionque.drop((mission, ))
					raise TooManyRetryError
				self.pausecallback()
				
				if not downloader.errorhandler(er, ep):
					time.sleep(5)
				continue
				
			else:
				# everything is ok, save image
				with open(savepath + fn + "." + ext, "wb") as f:
					f.write(oi)
				
			# call pause
			self.pausecallback()
				
			if not nextpageurl:
				ep.complete = True
				raise LastPageError
			ep.currentpageurl = nextpageurl
			ep.currentpagenumber += 1
			errorcount = 0
			print("")
	
class AnalyzeWorker(Worker):
	"""Analyze the mission.url, also the core of Comic Crawler"""

	def __init__(self, mission=None, callback=None):
		"""set mission"""
		
		super().__init__(callback)
		self.mission = mission
	
	def worker(self):
		"""analyze worker"""
		
		try:
			self.mission.lock.acquire()
			self.analyze(self.mission)
		except Exception as er:
			self.mission.state = ERROR
			self.callback(self.mission, er)
		else:
			self.mission.state = ANALYZED
			self.callback(self.mission)
		finally:
			self.mission.lock.release()

	def analyze(self, mission):
		"""Analyze mission url."""
		
		# if mission.state in (ANALYZED, INIT):
			# return
		safeprint("start analyzing {}".format(mission.url))
		mission.state_(ANALYZING)

		downloader = mission.downloader
		html = grabhtml(mission.url, hd=downloader.header)
		print("getting title")
		mission.title = downloader.gettitle(html, url=mission.url)
		print("getting episode list")
		epList = downloader.getepisodelist(html, url=mission.url)
		if not mission.episodelist:
			# new mission
			mission.episodelist = epList
		else:
			# re-analyze
			for ep in epList:
				for oep in mission.episodelist:
					if oep.firstpageurl == ep.firstpageurl and oep.complete:
						break
				else:
					mission.episodelist.append(ep)
					mission.update = True
			if not mission.update:
				mission.state_(FINISHED)
				return
		
		if not mission.episodelist:
			raise Exception("get episode list failed!")
		
		safeprint("analyzed succeed!")
		if mission.update:
			mission.state_(UPDATE)
		else:
			mission.state = ANALYZED

# bunch of errors, may pack them later
class InterruptError(Exception): pass

class FileExistError(Exception): pass
			
class LastPageError(Exception): pass
		
class TooManyRetryError(Exception): pass


class FreeQue:
	"""Mission queue data class."""

	q = []	# the list which save the missions
	
	def empty(self):
		"""return true if list is empty"""
		return not self.q
	
	def put(self, item):
		"""append item"""
		self.q.append(item)
		_evtcallback("MISSIONQUE_ARRANGE", self)
		
	def lift(self, items, reverse=False):
		"""Move items to the top."""
		a = [ i for i in self.q if i in items ]
		b = [ i for i in self.q if i not in items ]
		if not reverse:
			self.q = a + b
		else:
			self.q = b + a
		_evtcallback("MISSIONQUE_ARRANGE", self)
	
	def drop(self, items):
		"""Move items to the bottom."""
		self.lift(items, reverse=True)
		
	def remove(self, items):
		"""Delete specify items."""
		self.q = [ i for i in self.q if i not in items]
		_evtcallback("MISSIONQUE_ARRANGE", self)
		_evtcallback("MESSAGE", "Deleted {} mission(s)".format(len(items)))

	def take(self, n=1):
		"""Return a list containing n valid missions. If n <= 1 return a valid 
		mission.
		"""
		if n <= 1:
			for i in self.q:
				if i.state != FINISHED:
					return i
			return None
		else:
			s = []
			for i in self.q:
				if i.state != FINISHED:
					s.append(i)
				if len(s) == n:
					return s
			return s or None
			
	def cleanfinished(self):
		"""delete fished missions"""
		self.q = [ i for i in self.q if i.state is not FINISHED ]
		_evtcallback("MISSIONQUE_ARRANGE", self)
		
	def printList(self):
		"""print mission list"""
		for m in self.q:
			print(m.title)
			
	def getList(self):
		"""return title list"""
		return [m.title for m in self.q]
		
	def load(self, path):
		"""unpickle list from file"""
		import pickle
		try:
			f = open(path, "rb")
		except FileNotFoundError:
			print("no lib file")
			return
		self.q = pickle.load(f)
		_evtcallback("MISSIONQUE_ARRANGE", self)
		
	def save(self, path):
		"""pickle list to file"""
		import pickle
		f = open(path, "wb")
		pickle.dump(self.q, f)

		
class ConfigManager:
	"""Load config for other classes"""

	def __init__(self, path):
		"""set config file path"""
		import configparser as cp
		self.path = path
		self.config = cp.ConfigParser(interpolation=None)
		
		self.load()
		
	def get(self):
		"""return config"""
		return self.config
		
	def load(self):
		"""read config from file
		
		There's a utf-8 issue with configparser:
		http://bugs.python.org/issue14311
		"""
		self.config.read(self.path, "utf-8-sig")
		
	def save(self):
		with open(self.path, "w", encoding="utf-8") as f:
			self.config.write(f)
		
	@classmethod
	def apply(cls, config, dict, overwrite=False):
		"""ConfigManager.apply(dict1, dict2, overwrite)
		
		copy dict2 into dict1
		"""
		for key, value in dict.items():
			if not overwrite and key in config:
				continue
			config[key] = value
		return

class DownloadManager(DownloadWorker):
	"""DownloadManager class. Maintain the mission list."""
	
	def __init__(self, controller):
		"""set controller"""
	
		super().__init__()
		self.controller = controller
		self.missionque = FreeQue()
		self.skippagewhenfailed = False
		
		self.loadconfig()
		self.load()
	
	def loadconfig(self):
		"""Load config from controller. Set default"""
		
		manager = self.controller.configManager
		self.setting = manager.get()["DEFAULT"]
		default = {
			"savepath": "download",
			"runafterdownload": ""
		}
		manager.apply(self.setting, default)
		
	def addmission(self, mission):
		"""add mission"""
		
		self.missionque.put(mission)
		self.removeLibDuplicate(mission)
	
	def worker(self):
		"""overwrite, take mission from missionlist and download."""
		
		while True:
			mission = self.missionque.take()
			if mission is None:
				self.stop()
				safeprint("All download complete!")
				break
				
			try:
				mission.lock.acquire()
				mission.state_(DOWNLOADING)
				self.download(mission, self.setting["savepath"])
			except InterruptError:
				print("kill download worker")
				mission.state_(PAUSE)
			except TooManyRetryError:
				safeprint("Too many retry")
				mission.state_(PAUSE)
				self.missionque.drop((mission,))
			except Exception as er:
				import traceback
				er_message = traceback.format_exc()
				print("worker terminate!\n{}".format(er_message))
				self.stop()
				mission.state_(ERROR)
				_evtcallback("WORKER_TERMINATED", mission, er, er_message)
			else:
				command = self.setting["runafterdownload"]
				if not command:
					continue
				try:
					import subprocess
					subprocess.call((command, "{}/{}".format(self.setting["savepath"], safefilepath(mission.title))))
				except Exception as er:
					safeprint("failed to run process: {}".format(er))
			finally:
				mission.lock.release()
				
			if self._stop:
				# safeprint("Download worker killed.")
				break
		self.reset()
		return

	def start(self):
		"""overwrite, add missionque check."""
		
		if self.missionque.empty():
			safeprint("Misison que is empty.")
			return

		super().start()
		
	def save(self):
		"""Save mission que."""
		
		try:
			self.missionque.save("save.dat")
		except Exception as er:
			_evtcallback("DAT_SAVE_FAILED", er)
		else:
			print("Session saved success.")
		
	def load(self):
		"""load mission que"""
		
		try:
			self.missionque.load("save.dat")
		except Exception as er:
			_evtcallback("DAT_LOAD_FAILED", er)
		else:
			for m in self.missionque.q:
				m.downloader = self.controller.moduleManager.getDownloader(m.url)
			print("Session loaded success.")
		self.removeLibDuplicate()
		
	def removeLibDuplicate(self):
		"""replace duplicate with library one"""
		
		if "library" not in vars(self.controller):
			return False
			
		library = self.controller.library
		mqlen = len(self.missionque.q)
		for i in range(mqlen):
			for lm in library.libraryList.q:
				if self.missionque.q[i].url == lm.url:
					self.missionque.q[i] = lm
					break
		

		
class Library(AnalyzeWorker):
	""" Library"""
	
	def __init__(self, controller):
		"""init"""
	
		super().__init__()
		self.controller = controller
		self.libraryList = FreeQue()
		
		self.load()
		self.controller.downloadManager.removeLibDuplicate()
		self.checkUpdate()
		
	def load(self):
		"""load libraryList"""
		
		self.libraryList.load("library.dat")
		for m in self.libraryList.q:
			m.downloader = self.controller.moduleManager.getDownloader(m.url)
			
	def save(self):
		"""save library list"""
		
		self.libraryList.save("library.dat")
		
	def add(self, mission):
		"""add mission"""
		
		# check duplicate
		for m in self.libraryList.q[:]:
			if m.url == mission.url:
				# duplicate
				return False
		self.libraryList.put(mission)
		
	def remove(self, *missions):
		"""remove missions"""
		
		self.libraryList.remove(missions)
		
	def worker(self):
		"""overwrite, take mission from libraryList and analyze"""
		
		try:
			for m in self.libraryList.q:
				if m.state == DOWNLOADING:
					continue
				try:
					m.lock.acquire()
					self.analyze(m)
				except Exception as er:
					safeprint("analyze failed!\n", er)
				else:
					if m.update:
						self.libraryList.lift((m, ))
				finally:
					m.lock.release()
				self.pausecallback()
		except Exception as er:
			safeprint("check update interrupt!\n", er)
		self.reset()
			
	def checkUpdate(self):
		"""start analyze worker"""
		
		self.start()

	def sendToDownloadManager(self):
		"""send to controller"""
		
		for m in self.libraryList.q:
			if m.update:
				self.controller.downloadManager.addmission(m)

		
class ModuleManager:
	"""Import all the downloader module.
	
	DLModuleManger will automatic import all modules in the same directory 
	which prefixed with filename "cc_".
	
	"""
	
	def __init__(self, controller):
		import importlib, os
		self.controller = controller
		self.dlHolder = {}
		modsfile = [mod.replace(".py","") for mod in os.listdir() if re.search("^cc_.+\.py$", mod)]
		mods = [importlib.import_module(mod) for mod in modsfile]
		for d in mods:
			for dm in d.domain:
				self.dlHolder[dm] = d
		self.mods = mods
		
		self.loadconfig()
		
	def loadconfig(self):
		"""Load setting.ini and set up module.
		"""
	
		config = self.controller.configManager.get()
		for d in self.mods:
			if "loadconfig" in d.__dict__:
				d.loadconfig(config)
		
	def getdlHolder(self):
		"""Return downloader dictionary."""
		return [key for key in self.dlHolder]
		
	def validUrl(self,url):
		"""Return if the url is valid and in downloaders domain."""
		
		if self.getDownloader(url):
			return True
		return False
		
	def getDownloader(self, url):
		"""Return the downloader mod of spect url or return None"""
		
		dm = re.search("https?://([^/]+?)(:\d+)?/", url)
		if dm is None:
			return None
		dm = dm.group(1)
		for d in self.dlHolder:
			if d in dm:
				return self.dlHolder[d]
		return None
		
		
class Controller:
	"""workflow logic"""
	
	def __init__(self):
		self.loadClasses()
		self.view()
		self.unloadClasses()
	
	def loadClasses(self):
		self.configManager = ConfigManager("setting.ini")
		self.moduleManager = ModuleManager(self)
		self.downloadManager = DownloadManager(self)
		self.library = Library(self)
		
		self.configManager.save()
		self.downloadManager.removeLibDuplicate()
		
	def unloadClasses(self):
		if self.library.running:
			self.library.stop()
			self.library.join()
		self.library.save()
		
		if self.downloadManager.running:
			self.downloadManager.stop()
			self.downloadManager.join()
		self.downloadManager.save()
		
		self.configManager.save()
		
	def view(self):
		safeprint("Valid domains: " + " ".join(self.moduleManager.getdlHolder()))
		safeprint("Library list: " + " ".join(self.library.libraryList.getList()))
		safeprint("This is Comic Crawler version " + VERSION + "\n"
			" - Paste an url and press enter to start download.\n"
			" - or use Ctrl+Z to exit.")
			
		while self.getInput():
			pass
			
	def getInput(self):
		try:
			u = input(">>> ")
		except EOFError:
			return False
		command = None
		if not u.startswith("http"):
			command, sep, u = u.partition(" ")
		if command == "lib":
			self.iLib(u)
		elif command == "show":
			self.iShowList(u)
		else:
			self.iNewMission(u)
		return True

	def iShowList(self, u):
		for m in self.downloadManager.missionque.q:
			safeprint(m.title, m.url, m.state)
				
	def iLib(self, u):
		command, sep, u = u.partition(" ")
		if command == "add":
			self.iLibAdd(u)
		elif command == "remove":
			self.iLibRemove(u)
		else:
			self.iLibShow(command)
			
	def iLibShow(self, u):
		safeprint(" ".join(self.library.libraryList.getList()))
		
	def iAddUrl(self, url):
		downloader = self.moduleManager.getDownloader(url)
		if not downloader:
			print("Unknown url: {}\n".format(url))
			return
		# construct a mission
		m = Mission()
		m.url = url
		m.downloader = downloader
		print("Analyzing url: {}".format(m.url))
		AnalyzeWorker(m, self.iAnalyzeFinished).start()
		
	def iAnalyzeFinished(self, mission, error=None):
		if error:
			print("Analyze Failed! " + error)
		else:
			self.iAddMission(mission)
		
	def iAddMission(self, mission):
		self.downloadManager.addmission(mission)
		_evtcallback("MESSAGE", "Queued mission: " + mission.title)
		
		
	def iStart(self):
		self.downloadManager.start()
		
	def iStop(self):
		self.downloadManager.stop()
		
	def iClean(self):
		self.downloadManager.missionque.cleanfinished()
		
	def iReloadConfig(self):
		self.configManager.load()
		self.moduleManager.loadconfig()
		self.downloadManager.loadconfig()
		
	def iRemoveMission(self, *args):
		self.downloadManager.missionque.remove(args)
		
	def iLift(self, *args):
		self.downloadManager.missionque.lift(args)
		
	def iDrop(self, *args):
		self.downloadManager.missionque.drop(args)
		
	def iAddToLib(self, mission):
		self.library.add(mission)
		
	def iLibRemove(self, *args):
		self.library.remove(*args)
		
	def iLibCheckUpdate(self):
		self.library.checkUpdate()
		
	def iLibDownloadUpdate(self):
		self.library.sendToDownloadManager()
		
if __name__ == "__main__":
	Controller()
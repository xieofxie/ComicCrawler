#! python3

import worker

from .my_json import JSONObject

class MyWorker(worker.UserWorker, JSONObject):
	def __init__(self):
		super().__init__()
		self.json_exclude |= set(("thread",))

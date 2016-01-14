#! python3

"""MyWorker class"""

import worker

from .my_json import JSONObject

class MyWorker(worker.UserWorker, JSONObject):
	"""Inherit UserWorker and JSONObject"""
	def __init__(self):
		"""Add thread to json_exclude"""
		worker.UserWorker.__init__(self)
		JSONObject.__init__(self)
		self.json_exclude |= set(("thread",))

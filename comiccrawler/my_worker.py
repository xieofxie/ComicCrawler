#! python3

"""MyWorker class"""

import worker

from .my_json import JSONObject

class MyWorker(worker.UserWorker, JSONObject):
	"""Inherit UserWorker and JSONObject"""
	def __init__(self):
		"""Add thread to json_exclude"""
		super().__init__()
		self.json_exclude |= set(("thread",))

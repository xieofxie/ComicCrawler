#! python3

import worker

class MyWorker(worker.UserWorker, my_json.JSONObject):
	def __init__(self):
		super().__init__()
		self.json_exclude |= set(("thread",))

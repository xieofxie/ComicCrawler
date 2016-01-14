#! python3

import json

def shallow(dict, exclude=None):
	"""Return a shallow copy of a dict.

	Arguments:
	exclude - A list of key name which should not to copy. (default: None)
	"""
	new_dict = {}
	for key in dict:
		if not exclude or key not in exclude:
			new_dict[key] = dict[key]
	return new_dict

class JSONObject:
	def __init__(self):
		self.json_exclude = set()

class Encoder(json.JSONEncoder):
	"""Encode Mission, Episode to json."""

	def default(self, object):
		if isinstance(object, JSONObject):
			return shallow(vars(object), object.json_exclude)
		return super().default(object)

def loads(s):
	return json.loads(s)

def dumps(object):
	return json.dumps(object, cls=Encoder, indent=4, ensure_ascii=False)

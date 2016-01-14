#! python3

"""This is a json module to provide an interface to make object JSON-decodeable"""

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
	"""Inherit this class and put unwant keys into json_exclude"""
	def __init__(self):
		self.json_exclude = set()

class Encoder(json.JSONEncoder):
	"""Custom encoder"""
	def default(self, object):
		"""Handle json_exclude"""
		if hasattr(object, "json_exclude"):
			return shallow(vars(object), object.json_exclude)
		return super().default(object)

def loads(s):
	"""Load string. Return dict"""
	return json.loads(s)

def dumps(object):
	"""Load object. Return json string"""
	return json.dumps(object, cls=Encoder, indent=4, ensure_ascii=False)

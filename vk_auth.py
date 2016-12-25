#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
py3 = sys.version_info[0] == 3

import getpass
if py3:
	from html.parser import HTMLParser
else:
	from HTMLParser import HTMLParser

if py3:
	from urllib.request import build_opener
else:
	from urllib2 import build_opener

if py3:
	from urllib.request import HTTPCookieProcessor
else:
	from urllib2 import HTTPCookieProcessor

if py3:
	from urllib.request import HTTPRedirectHandler
else:
	from urllib2 import HTTPRedirectHandler

if py3:
	import http.cookiejar as cookiejar
else:
	import cookielib as cookiejar

if py3:
	from urllib.parse import urlencode
else:
	from urllib import urlencode

if py3:
	from urllib.parse import urlparse
else:
	from urlparse import urlparse

api_version = '5.14'

class FormParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.url = None
		self.params = {}
		self.in_form = False
		self.in_comment = False
		self.form_parsed = False
		self.method = "GET"
		self.comment = ""
		self.comment_parsed = False

	def handle_starttag(self, tag, attrs):
		tag = tag.lower()
		attrs = dict((name.lower(), value) for name, value in attrs)
		if not self.comment_parsed and tag == "div":
			if "class" in attrs:
				if attrs["class"] == "fi_row":
					self.in_comment = True
					return
		if tag == "form":
			if self.form_parsed:
				raise RuntimeError("Second form on page")
			if self.in_form:
				raise RuntimeError("Already in form")
			self.in_form = True
		if not self.in_form:
			return
		if tag == "form":
			self.url = attrs["action"]
			if "method" in attrs:
				self.method = attrs["method"].upper()
		elif tag == "input" and "type" in attrs and "name" in attrs:
			if attrs["type"] in ["hidden", "text", "password"]:
				self.params[attrs["name"]] = attrs["value"] if "value" in attrs else ""

	def handle_data(self, data):
		if len(data) > 1 and self.in_comment:
			#print("КОММЕНТ: " + data)
			self.comment += data

	def handle_endtag(self, tag):
		tag = tag.lower()
		if tag == "div" and self.in_comment:
			self.in_comment = False
			self.comment_parsed = True
			return
		if tag == "form":
			if not self.in_form:
				raise RuntimeError("Unexpected end of <form>")
			self.in_form = False
			self.form_parsed = True

def auth(email, password, client_id, scope):
	def split_key_value(kv_pair):
		kv = kv_pair.split("=")
		return kv[0], kv[1]

	# Authorization form
	def auth_user(email, password, client_id, scope, opener):
		url = "http://oauth.vk.com/oauth/authorize?" + \
			"redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
			"client_id=%s&scope=%s&display=mobile&v=%s" % (client_id, ",".join(scope), api_version)
		print("============ URL1: " + url)
		response = opener.open(url)
		doc = response.read()
		if py3:
			doc = doc.decode("utf-8")
		file = open("doc1.html", "w")
		file.write(doc)
		file.close
		parser = FormParser()
		parser.feed(doc)
		parser.close()
		if not parser.form_parsed or parser.url is None or "pass" not in parser.params or \
		  "email" not in parser.params:
			raise RuntimeError("Something wrong")
		parser.params["email"] = email
		parser.params["pass"] = password
		if parser.method == "POST":
			response = opener.open(parser.url, urlencode(parser.params).encode("utf-8"))
		else:
			raise NotImplementedError("Method '%s'" % parser.method)
		doc = response.read()
		if py3:
			doc = doc.decode("utf-8")
		print("============ URL2: " + response.geturl())
		file = open("doc2.html", "w")
		file.write(doc)
		file.close
		parser = FormParser()
		parser.feed(doc)
		parser.close()
		if not parser.form_parsed or parser.url is None:
			raise RuntimeError("Something wrong")
		#parser.params["email"] = email
		parser.params["code"] = getpass.getpass(parser.comment + '..\n')
		if parser.method == "POST":
			urlp = urlparse(response.geturl())
			response = opener.open(urlp.scheme + '://' + urlp.netloc + parser.url, urlencode(parser.params).encode("utf-8"))
		else:
			raise NotImplementedError("Method '%s'" % parser.method)
		doc = response.read()
		if py3:
			try:
				doc = doc.decode("utf-8")
			except:
				doc = doc.decode("windows-1251")
		url = response.geturl()
		print("============ URL3: " + url)
		file = open("doc3.html", "w")
		file.write(doc)
		file.close
		return doc, url

	# Permission request form
	def give_access(doc, url, opener):
		parser = FormParser()
		parser.feed(doc)
		parser.close()
		if not parser.form_parsed or parser.url is None:
			raise RuntimeError("Something wrong")
		if parser.method == "POST":
			urlp = urlparse(url)
			print("============ URL4: " + urlp.scheme + '://' + urlp.netloc + parser.url)
			response = opener.open(urlp.scheme + '://' + urlp.netloc + parser.url, urlencode(parser.params).encode("utf-8"))
		else:
			raise NotImplementedError("Method '%s'" % parser.method)
		return response.geturl()


	if not isinstance(scope, list):
		scope = [scope]
	opener = build_opener(
		HTTPCookieProcessor(cookiejar.CookieJar()),
		HTTPRedirectHandler())
	doc, url = auth_user(email, password, client_id, scope, opener)
	if urlparse(url).path != "/blank.html":
		# Need to give access to requested scope
		url = give_access(doc, url, opener)
	if urlparse(url).path != "/blank.html":
		raise RuntimeError("Expected success here")
	answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
	if "access_token" not in answer or "user_id" not in answer:
		raise RuntimeError("Missing some values in answer")
	return answer["access_token"], answer["user_id"]

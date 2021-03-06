##############################################################################
#                        2011 E2OpenPlugins                                  #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################
import os
import re
from twisted.web import static, resource, http
from urllib import unquote, quote
from Components.config import config
from os import path as os_path, listdir
from Tools.Directories import fileExists

import json

class FileController(resource.Resource):

	def __init__(self, path = ""):
		resource.Resource.__init__(self)

	def render(self, request):
		action = "download"
		if "action" in request.args:
			action = request.args["action"][0]
			
		if "file" in request.args:
			filename = unquote(request.args["file"][0]).decode('utf-8', 'ignore').encode('utf-8')

			if not os.path.exists(filename):
				return "File '%s' not found" % (filename)

			# limit unauthenticated requests to directories /hdd, /media and /mnt.
			# Other directories with sensible information require authentication.
			filename = re.sub("^/+", "/", os.path.realpath(filename))
			for prefix in [ "/hdd/", "/media/", "/mnt/" ]:
				if filename.startswith(prefix):
					break
			else:
				# require authentication for request to eg. /etc
				if not self.isAuthenticated(request):
					return "File '%s' not found" % (filename)

			name = "stream"
			if "name" in request.args:
				name = request.args["name"][0]
			if action == "stream":
				response = "#EXTM3U\n#EXTVLCOPT--http-reconnect=true\n#EXTINF:-1,%s\nhttp://%s:%s/file?action=download&file=%s" % (name, request.getRequestHostname(), config.OpenWebif.port.value, quote(filename))
				request.setHeader("Content-Disposition:", 'attachment;filename="%s.m3u"' % name)
				request.setHeader("Content-Type:", "audio/mpegurl")
				return response
			elif action == "delete":
				request.setResponseCode(http.OK)
				return "TODO: DELETE FILE: %s" % (filename)
			elif action == "download":
				request.setHeader("Content-Disposition:", "attachment;filename=\"%s\"" % (filename.split('/')[-1]))
				rfile = static.File(filename, defaultType = "application/octet-stream")
				return rfile.render(request)
			else: 
				return "wrong action parameter"
		
		if "dir" in request.args:
			path = request.args["dir"][0]

			if "pattern" in request.args:
				pattern = request.args["pattern"][0]
			else:
				pattern = None
				
			directories = []
			files = []	
			if fileExists(path):
				try:
					files = listdir(path)
				except:
					files = []

				files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if os_path.isdir(path + x):
						directories.append(path + x + "/")
						files.remove(x)

				data = []
				data.append({"result": True,"dirs": directories,"files": files})

				request.setHeader("content-type", "text/plain")
				request.write(json.dumps(data))
				request.finish()
				return server.NOT_DONE_YET
			else:
				return "path %s not exits" % (path)
	
	#
	# check if a request is authenticated; needed here for
	# requests to /etc and others, compatibility with iDreamX.
	def isAuthenticated(self, request):
		session = request.getSession().sessionNamespaces
			
		if "logged" in session.keys() and session["logged"]:
			return True
			
		if self.authenticate(request.getUser(), request.getPassword()):
			session["logged"] = True
			return True
		return False

	def authenticate(self, user, passwd):
		from crypt import crypt
		from pwd import getpwnam
		from spwd import getspnam
		cpass = None
		try:
			cpass = getpwnam(user)[1]
		except:
			return False
		if cpass:
			if cpass == 'x' or cpass == '*':
				try:
					cpass = getspnam(user)[1]
				except:
					return False			
			return crypt(passwd, cpass) == cpass
		return False


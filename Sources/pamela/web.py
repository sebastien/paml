#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   01-Jun-2007
# Last mod.         :   13-Feb-2012
# -----------------------------------------------------------------------------
import os, sys, re, subprocess, tempfile
from . import engine
import retro
from retro.contrib.localfiles import LocalFiles
from retro.contrib.cache import SignatureCache
from retro.contrib import proxy

CACHE    = SignatureCache()
COMMANDS = dict(
	sugar="sugar",
	coffee="coffee"
)

try:
	import templating
	HAS_TEMPLATING = templating
except:
	HAS_TEMPLATING = None

def processPamela( pamelaText, path, request ):
	parser = engine.Parser()
	if request.get("as") == "js":
		parser._formatter = engine.JSHTMLFormatter()
		result = parser.parseString(pamelaText, path)
		assign = request.get("assign")
		prefix = ""
		suffix = ""
		if assign:
			if assign == "_": assign = os.path.basename(path).split(".")[0]
			assign = assign.split(".")
			prefix = "var "
			suffix = ";"
			for i,v in enumerate(assign):
				if   i == 0:
					prefix += v + "=("
					suffix  = ")"    + suffix
				else:
					prefix += "{" + v + ":"
					suffix = "}" + suffix
		return prefix + result + suffix, "text/javascript"
	else:
		result = parser.parseString(pamelaText, path)
		return result, "text/html"

def processCleverCSS( text, path, request ):
	import clevercss
	result = clevercss.convert(text)
	return result, "text/css"

def _processCommand( command, text, path, cache=True, tmpsuffix="tmp", tmpprefix="pamela_"):
	timestamp = has_changed = data = None
	is_same   = False
	if cache:
		timestamp     = SignatureCache.mtime(path)
		is_same, data = CACHE.get(path,timestamp)
	if (not is_same) or (not cache):
		if os.path.isdir(path):
			temp_created = True
			fd, path     = tempfile.mkstemp(suffix=tmpsuffix,prefix=tmpprefix)
			os.write(fd, text)
			os.close(fd)
			command = command[:-1] + [path]
		else:
			temp_created = False
		cmd     = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		data    = cmd.stdout.read()
		error   = cmd.stderr.read()
		cmd.wait()
		if temp_created:
			os.unlink(path)
		if not data:
			raise Exception(error)
		if cache:
			CACHE.set(path,timestamp,data)
	return data

def processSugar( text, path, cache=True ):
	if os.path.isdir(path):
		parent_path  = path
	else:
		parent_path  = os.path.dirname(os.path.abspath(path))
	command = [
		COMMANDS["sugar"],"-cljs",
		"-L" + parent_path,
		"-L" + os.path.join(parent_path, "lib", "js"),
		path
	]
	return _processCommand(command, text, path, cache), "text/javascript"

def processCoffeeScript( text, path, cache=True ):
	command = [
		COMMANDS["coffee"],"-cp",
		path
	]
	return _processCommand(command, text, path, cache), "text/javascript"

def getProcessors():
	"""Returns a dictionary with the Retro LocalFiles processors already
	setup."""
	return {"paml":processPamela, "sjs":processSugar, "ccss":processCleverCSS,"coffee":processCoffeeScript}

def getLocalFiles(root=""):
	"""Returns a Retro LocalFile component initialized with the Pamela
	processor."""
	return LocalFiles(root=root,processors=getProcessors(),optsuffix=[".paml",".html"])

def beforeRequest( request ):
	pass

def run( arguments, options={} ):
	files   = getLocalFiles()
	comps   = [files]
	proxies = [x[len("proxy:"):] for x in [x for x in arguments if x.startswith("proxy:")]]
	comps.extend(proxy.createProxies(proxies))
	app     = retro.Application(components=comps)
	#app.onRequest(beforeRequest)
	retro.command(
		arguments,
		app      = app,
		port     = int(options.get("port") or retro.DEFAULT_PORT)
	)

# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	options = {}
	for a in sys.argv[1:]:
		a=a.split("=",1)
		if len(a) == 1: v=True
		else: v=a[1];a=a[0]
		options[a.lower()] = v
	run(sys.argv[1:], options)

# EOF - vim: tw=80 ts=4 sw=4 noet

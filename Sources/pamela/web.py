#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   2007-Jun-01
# Last mod.         :   2015-Feb-25
# -----------------------------------------------------------------------------

import os, sys, re, subprocess, tempfile, hashlib
from   pamela import engine
import retro
from   retro.contrib.localfiles import LocalFiles
from   retro.contrib.cache      import SignatureCache, MemoryCache
from   retro.contrib            import proxy

CACHE         = SignatureCache ()
MEMORY_CACHE  = MemoryCache ()
PROCESSORS    = {}
COMMANDS      = None
PANDOC_HEADER = """
<!DOCTYPE html>
<html><head>
<meta charset="utf-8" />
<link rel="stylesheet" href="http://ffctn.com/doc/css/base.css" />
<link rel="stylesheet" href="http://ffctn.com/doc/css/typography.css" />
<link rel="stylesheet" href="http://ffctn.com/doc/css/texto.css" />
</head><body class='use-base use-texto'><div class='document'>
"""
PANDOC_FOOTER = "</div></body></html>"

def getCommands():
	global COMMANDS
	if not COMMANDS:
		COMMANDS = dict(
			sugar       = os.environ.get("SUGAR",       "sugar"),
			coffee      = os.environ.get("COFFEE",      "coffee"),
			pythoniccss = os.environ.get("PYTHONICCSS", "pythoniccss"),
			pandoc      = os.environ.get("PANDOC",      "pandoc"),
		)
	return COMMANDS

try:
	import templating
	HAS_TEMPLATING = templating
except:
	HAS_TEMPLATING = None

def processPamela( pamelaText, path, request=None ):
	parser = engine.Parser()
	if request and request.get("as") == "js":
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

def processCleverCSS( text, path, request=None ):
	import clevercss
	result = clevercss.convert(text)
	return result, "text/css"

def _processCommand( command, text, path, cache=True, tmpsuffix="tmp", tmpprefix="pamela_"):
	timestamp = has_changed = data = None
	is_same   = False
	data      = None
	if cache:
		if path:
			timestamp     = SignatureCache.mtime(path)
			is_same, data = CACHE.get(path,timestamp)
			cache = CACHE
		else:
			text    = engine.ensure_unicode(text)
			sig     = hashlib.sha256(bytes(u" ".join(command) + text)).hexdigest()
			cache   = MEMORY_CACHE
			is_same = cache.has(sig)
			data    = cache.get(sig)
	if (not is_same) or (not cache):
		if not path or os.path.isdir(path):
			temp_created = True
			fd, path     = tempfile.mkstemp(suffix=tmpsuffix,prefix=tmpprefix)
			os.write(fd, engine.ensure_bytes(text))
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
		if cache is CACHE:
			cache.set(path,timestamp,data)
		elif cache is MEMORY_CACHE:
			cache.set(sig,data)
	return engine.ensure_unicode(data)

def processSugar( text, path, cache=True, includeSource=False ):
	if os.path.isdir(path or "."):
		parent_path  = path or "."
	else:
		parent_path  = os.path.dirname(os.path.abspath(path or "."))
	sugar2 = None
	# try:
	# 	import sugar2
	# except ImportError, e:
	# 	sugar2 = None
	# 	pass
	if sugar2:
		# If Sugar2 is available, we'll use it
		command = sugar2.SugarCommand("sugar2")
		arguments = [
			"-cljs",
			"--cache",
			"--include-source" if includeSource else ""
			"-L" + parent_path,
			"-L" + os.path.join(parent_path, "lib", "sjs"),
			path
		]
		return command.runAsString (arguments), "text/javascript"
	else:
		# Otherwise we fallback to the regular Sugar, which has to be
		# run through popen (so it's slower)
		command = [
			getCommands()["sugar"],
			"-cSljs" if includeSource else "-cljs",
			"-L" + parent_path,
			"-L" + os.path.join(parent_path, "lib", "sjs"),
			path
		]
		return _processCommand(command, text, path, cache), "text/javascript"

def processCoffeeScript( text, path, cache=True ):
	command = [
		getCommands()["coffee"],"-cp",
		path
	]
	return _processCommand(command, text, path, cache), "text/javascript"

def processPandoc( text, path, cache=True ):
	command = [
		getCommands()["pandoc"],
		path
	]
	return PANDOC_HEADER + _processCommand(command, text, path, cache) + PANDOC_FOOTER, "text/html"

def processPythonicCSS( text, path, cache=True ):
	# NOTE: Disabled until memory leaks are fixes
	# import pythoniccss
	# result = pythoniccss.convert(text)
	# return result, "text/css"
	command = [
		getCommands()["pythoniccss"],
		path
	]
	return _processCommand(command, text, path, cache), "text/css"

def getProcessors():
	"""Returns a dictionary with the Retro LocalFiles processors already
	setup."""
	global PROCESSORS
	if not PROCESSORS:
		PROCESSORS = {
			"paml"  : processPamela,
			"sjs"   : processSugar,
			"ccss"  : processCleverCSS,
			"coffee": processCoffeeScript,
			"pcss"  : processPythonicCSS,
			"md"    : processPandoc,
		}
	return PROCESSORS

def getLocalFiles(root=""):
	"""Returns a Retro LocalFile component initialized with the Pamela
	processor."""
	return LocalFiles(root=root,processors=getProcessors(),optsuffix=[".paml",".html"], lastModified=False)

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
	if hasattr(engine.logging, "REPORTER"):
		engine.logging.register(engine.logging.StderrReporter())
	for a in sys.argv[1:]:
		a=a.split("=",1)
		if len(a) == 1: v=True
		else: v=a[1];a=a[0]
		options[a.lower()] = v
	run(sys.argv[1:], options)

# EOF - vim: tw=80 ts=4 sw=4 noet

#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   01-Jun-2007
# Last mod.         :   05-Oct-2010
# -----------------------------------------------------------------------------

import os, sys, re, subprocess, tempfile
import engine
import retro
from retro.contrib.localfiles import LocalFiles
from retro.contrib.cache import SignatureCache
from retro.contrib import proxy

CACHE    = SignatureCache()
COMMANDS = dict(
	sugar="sugar"
)

def processPamela( pamelaText, path ):
	parser = engine.Parser()
	result = parser.parseString(pamelaText, path)
	return result, "text/html"

def processCleverCSS( text, path ):
	import clevercss
	result = clevercss.convert(text)
	return result, "text/css"

def processSugar( sugarText, path, cache=True ):
	timestamp = has_changed = data = None
	is_same   = False
	if cache:
		timestamp     = SignatureCache.mtime(path)
		is_same, data = CACHE.get(path,timestamp)
	if (not is_same) or (not cache):
		modulename  = os.path.splitext(os.path.basename(path))[0]
		parent_path = os.path.dirname(path)
		dirpath    = tempfile.mkdtemp()
		p = dirpath + os.path.sep + modulename + ".sjs"
		f = file(p, "w") ; f.write(sugarText)
		command = "%s -cljs %s %s" % (COMMANDS["sugar"], "-L%s -L%s/lib/sjs" % (parent_path, parent_path), p)
		cmd     = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		data    = cmd.stdout.read()
		error   = cmd.stderr.read()
		cmd.wait() ;
		f.close()
		os.unlink(p)
		if os.path.exists(dirpath): os.rmdir(dirpath)
		if not data:
			raise Exception(error)
		if cache:
			CACHE.set(path,timestamp,data)
	return data, "text/plain"

def getProcessors():
	"""Returns a dictionary with the Retro LocalFiles processors already
	setup."""
	return {"paml":processPamela, "sjs":processSugar, "ccss":processCleverCSS}

def getLocalFiles(root=""):
	"""Returns a Retro LocalFile component initialized with the Pamela
	processor."""
	return LocalFiles(root=root,processors=getProcessors(),optsuffix=[".paml",".html"])

def run( arguments, options={} ):
	files   = getLocalFiles()
	comps   = [files]
	proxies = map(lambda x:x[len("proxy:"):],filter(lambda x:x.startswith("proxy:"),arguments))
	comps.extend(proxy.createProxies(proxies))
	app     = retro.Application(components=comps)
	retro.command(
		arguments,
		app      = app,
		sessions = False,
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

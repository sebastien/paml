#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   01-Jun-2007
# Last mod.         :   12-Jun-2009
# -----------------------------------------------------------------------------

import os, sys, re
import engine
import retro
from retro.contrib.localfiles import LocalFiles
from retro.contrib.cache import Cache
from retro.contrib import proxy

CACHE = Cache()

def processPamela( pamelaText, path ):
	parser = engine.Parser()
	result = parser.parseString(pamelaText)
	return result, "text/html"

def processCleverCSS( text, path ):
	import clevercss
	result = clevercss.convert(text)
	return result, "text/css"

def processSugar( sugarText, path, cache=True ):
	timestamp = has_changed = data = None
	if cache:
		timestamp         = CACHE.filemod(path)
		has_changed, data = CACHE.get(path,timestamp)
	if has_changed or not cache:
		try:
			from sugar import main as sugar
		except Exception, e:
			print "Sugar/LambdaFactory is not available"
			print e
			return sugarText, "text/plain"
		modulename = os.path.splitext(os.path.basename(path))[0]
		data = sugar.sourceToJavaScript(sugarText, modulename)
		if cache:
			CACHE.put(path,timestamp,data)
	return data, "text/plain"

def getProcessors():
	"""Returns a dictionary with the Retro LocalFiles processors already
	setup."""
	return {"paml":processPamela, "sjs":processSugar, "ccss":processCleverCSS}

def getLocalFile():
	"""Returns a Retro LocalFile component initialized with the Pamela
	processor."""
	return LocalFiles(processors=getProcessors())

def run( arguments, options={} ):
	files   = getLocalFile()
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

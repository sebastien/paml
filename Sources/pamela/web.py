#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project           :   Feedback
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   01-Jun-2007
# Last mod.         :   05-Jun-2007
# -----------------------------------------------------------------------------

import os, sys, re
import engine
import railways
from railways.contrib.localfiles import LocalFiles


def processPamela( pamelaText, path ):
	parser = engine.Parser()
	return parser.parseText(pamelaText), "text/html"

def processSugar( sugarText, path ):
	try:
		from sugar import sugar
	except:
		return sugarText, "text/plain"
	return sugar.sourceToJavaScript(path, sugarText)[0], "text/plain"

def run( arguments ):
	files  = LocalFiles(processors={"paml":processPamela, "sjs":processSugar})
	app    = railways.Application(components=(files,))
	railways.run(app=app,sessions=False)

# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	run(sys.argv[1:])

# EOF



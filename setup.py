#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : Pamela
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 06-Dec-2008
# Last mod  : 06-Dec-2008
# -----------------------------------------------------------------------------

import sys ; sys.path.insert(0, "Sources")
from distutils.core import setup
import pamela.engine

SUMMARY     = "Brings the pleasure back to HTML and XML !"
DESCRIPTION = """\
Pamela is a simple HTML/XML shorthand syntax in the same spirit as HAML or SLIP.
It was designed to be faithful to the HTML/XML syntax while reducing the
opportunities for errors (like forgetting to close a block). Pamela also
supports advanced formatting options to get exactly the HTML you want to have.
"""

# ------------------------------------------------------------------------------
#
# SETUP DECLARATION
#
# ------------------------------------------------------------------------------

setup(
    name         = "Pamela",
    version      = pamela.engine.__version__,

    author       = "Sebastien Pierre", author_email = "sebastien@ivy.fr",
    description   = SUMMARY, long_description  = DESCRIPTION,
    license      = "Revised BSD License",
    keywords     = "XML, HTML, syntax, pre-processor, web",
    url          = "http://www.github.com/sebastien/pamela",
    package_dir  = { "": "Sources" },
    packages     = ["pamela"],
    scripts      = ["Scripts/pamela", "Scripts/pamela-web"]
)

# EOF

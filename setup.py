#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : PAML
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 06-Dec-2008
# Last mod  : 06-Dec-2008
# -----------------------------------------------------------------------------

import sys ; sys.path.insert(0, "Sources")
from distutils.core import setup
import paml.engine

SUMMARY     = "A Pythonic transpiler for HTML/XML"
DESCRIPTION = """\
PAML is a simple HTML/XML shorthand syntax in the same spirit as HAML or SLIP.
It was designed to be faithful to the HTML/XML syntax while reducing the
opportunities for errors (like forgetting to close a block). PAML also
supports advanced formatting options to get exactly the HTML you want to have.
"""

# ------------------------------------------------------------------------------
#
# SETUP DECLARATION
#
# ------------------------------------------------------------------------------

setup(
    name         = "paml",
    version      = paml.engine.__version__,
    author       = "Sebastien Pierre", author_email = "sebastien.pierre@gmail.com",
    description   = SUMMARY, long_description  = DESCRIPTION,
    license      = "Revised BSD License",
    keywords     = "XML, HTML, syntax, pre-processor, web",
    url          = "http://www.github.com/sebastien/paml",
    package_dir  = { "": "Sources" },
    packages     = ["paml"],
    scripts      = ["Scripts/paml", "Scripts/paml-web"]
)

# EOF

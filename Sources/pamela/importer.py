#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   09-Jun-2010
# Last mod.         :   09-Jun-2010
# -----------------------------------------------------------------------------

import sys
from xml.dom.minidom import parse, parseString

class XML2Paml:

	def __init__( self ):
		self.indent = 0
		self.result = ""

	
	def extractLines(self, text):
		lines = map(lambda _:_.strip(),text.split("\n"))
		return filter(lambda _:len(_.strip()) > 0, lines)

	def convert( self, node ):
		t = node.nodeType
		if   t == doc.DOCUMENT_NODE:
			for n in node.childNodes:
				self.convert(n)
		elif t == node.COMMENT_NODE:
			map(lambda _:self.output("# " + _), self.extractLines(node.nodeValue))
		elif t == node.TEXT_NODE:
			map(self.output, self.extractLines(node.nodeValue))
		elif t == node.ELEMENT_NODE:
			classes    = ""
			ids        = ""
			attributes = []
			for n,v in node.attributes.items():
				if   n == "class":
					classes = "." + ".".join((map(lambda _:_.strip(),v.split(" "))))
				elif n == "id":
					ids = "#" + (map(lambda _:_.strip(),v.split(" ")))[0]
				else:
					attributes.append("%s=\"%s\"" % (n,v))
			if attributes:
				attributes = "(%s)" % (",".join(attributes))
			else:
				attributes = ""
			self.output("<%s%s%s%s" % ( node.nodeName, ids, classes, attributes) )
			for n in node.childNodes:
				self.indent += 1
				self.convert(n)
				self.indent -= 1
		else:
			pass
		return self.result
	
	def output( self, text ):
		self.result += ("\t" * self.indent) + text + "\n"


def run(doc):
	converter = XML2Paml()
	return converter.convert(doc)


if __name__ == "__main__":
	doc = parse(sys.argv[1])
	sys.stdout.write(run(doc).encode("utf-8"))

# EOF - vim: tw=80 ts=4 sw=4 noet

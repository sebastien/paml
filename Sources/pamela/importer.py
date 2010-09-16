#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   09-Jun-2010
# Last mod.         :   30-Jul-2010
# -----------------------------------------------------------------------------

import sys, xml.parsers.expat
import xml.dom.minidom as minidom

class XML2Paml:

	def __init__( self ):
		self.indent = 0
		self.result = ""

	
	def extractLines(self, text):
		lines = map(lambda _:_.strip(),text.split("\n"))
		return filter(lambda _:len(_.strip()) > 0, lines)

	def convert( self, node, bodyOnly=False ):
		if type(node) in (str,unicode):
			node = minidom.parseString(node)
		t = node.nodeType
		if   t == node.DOCUMENT_NODE:
			if bodyOnly:
				html_node = filter(lambda n:n.nodeType == node.ELEMENT_NODE and n.nodeName.lower() == "html", node.childNodes)
				body_nodes = filter(lambda n:n.nodeType == node.ELEMENT_NODE and n.nodeName.lower() == "body", html_node[0].childNodes)
				if body_nodes:
					for n in body_nodes[0].childNodes:
						self.convert(n)
			else:
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


def run(doc, bodyOnly=False):
	converter = XML2Paml()
	return converter.convert(doc, bodyOnly)

def parseFile(path):
	doc = minidom.parse(sys.argv[1])
	return run(doc)

if __name__ == "__main__":
	sys.stdout.write(parseFile(sys.argv[1]).encode("utf-8"))

# EOF - vim: tw=80 ts=4 sw=4 noet

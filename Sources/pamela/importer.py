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
		lines = [_.strip() for _ in text.split("\n")]
		return [_ for _ in lines if len(_.strip()) > 0]

	def convert( self, node, bodyOnly=False ):
		if type(node) in (str,str):
			node = minidom.parseString(node)
		t = node.nodeType
		if   t == node.DOCUMENT_NODE:
			if bodyOnly:
				html_node = [n for n in node.childNodes if n.nodeType == node.ELEMENT_NODE and n.nodeName.lower() == "html"]
				body_nodes = [n for n in html_node[0].childNodes if n.nodeType == node.ELEMENT_NODE and n.nodeName.lower() == "body"]
				if body_nodes:
					for n in body_nodes[0].childNodes:
						self.convert(n)
			else:
				for n in node.childNodes:
					self.convert(n)
		elif t == node.COMMENT_NODE:
			for line in self.extractLines(node.nodeValue):
				self.output("# " + line)
		elif t == node.TEXT_NODE:
			for line in self.extractLines(node.nodeValue):
				self.output(line)
		elif t == node.ELEMENT_NODE:
			classes    = ""
			ids        = ""
			attributes = []
			for n,v in list(node.attributes.items()):
				if   n == "class":
					classes = "." + ".".join(([_.strip() for _ in v.split(" ")]))
				elif n == "id":
					ids = "#" + ([_.strip() for _ in v.split(" ")])[0]
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

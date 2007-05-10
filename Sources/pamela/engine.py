#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser Gnu Public License
# -----------------------------------------------------------------------------
# Creation date     :   10-May-2007
# Last mod.         :   10-May-2007
# -----------------------------------------------------------------------------

import os, sys, re
from xml.etree import cElementTree as ET

PAMELA_VERSION = "0.1"

# PAMELA GRAMMAR ______________________________________________________________

SYMBOL_NAME    = "[\w\d_-]+"
SYMBOL_ID_CLS  = "(\#%s|\.%s)+" % (SYMBOL_NAME, SYMBOL_NAME)
SYMBOL_ATTR    = "%s(=[^),]+)?" % (SYMBOL_NAME)
SYMBOL_ATTRS   = "\(%s(,%s)+\)" % (SYMBOL_ATTR, SYMBOL_ATTR)
RE_COMMENT     = re.compile("^#.*$")
RE_DECLARATION = re.compile("^@(%s):?" % (SYMBOL_NAME))
RE_ELEMENT     = re.compile("^\<(%s)(%s)?(%s)?\:?" % (
	SYMBOL_NAME,
	SYMBOL_ID_CLS,
	SYMBOL_ATTRS
))
RE_LEADING_TAB = re.compile("^\t*")
RE_LEADING_SPC = re.compile("^ *")

# -----------------------------------------------------------------------------
#
# Writer class
#
# -----------------------------------------------------------------------------

class XMLWriter:
	"""The Writer class implements a simple SAX-like interface to create the
	resulting HTML/XML document. This is not API-compatible with SAX because
	Pamela as slightly differnt information than what SAX offers, which requires
	specific methods."""

	class Element:
		def __init__(self, name, attributes=None):
			self.name=name
			self.attributes=attributes or []
			self.content=[]

	class Declaration(Element):
		def __init__(self, name, attributes=None):
			Node.__init__(self)

	def __init__( self ):
		pass

	def onDocumentStart( self ):
		self._content   = []
		self._nodeStack = []
		self._document = ET.Element("document")

	def onDocumentEnd( self ):
		return ET.dump(self._document)

	def onComment( self, line ):
		line = line.replace("\n", " ").strip()
		comment = ET.Comment(line)
		self._node().append(comment)

	def onTextAdd( self, text ):
		n = self._node()
		if n.text: n.text += text
		else: n.text = text

	def onElementStart( self, name, attributes=None ):
		element = ET.SubElement(self._node(), name)
		self._nodeStack.append(element)

	def onElementEnd( self ):
		self._nodeStack.pop()

	def onDeclarationStart( self, name, attributes=None ):
		element = ET.SubElement(self._node(), "delcaration:" + name)
		self._nodeStack.append(element)

	def onDeclarationEnd( self ):
		self._nodeStack.pop()

	def _node( self ):
		if not self._nodeStack: return self._document
		return self._nodeStack[-1]

# -----------------------------------------------------------------------------
#
# Parser class
#
# -----------------------------------------------------------------------------

class Parser:

	def __init__( self ):
		self._tabsOnly  = True
		self._tabsWidth = 4
		self._elementStack = []
		self._writer = XMLWriter()

	def parseFile( self, path ):
		# FIXME: File exists and is readable
		f = file(path, "r")
		self._writer.onDocumentStart()
		for l in f.readlines():
			self.parseLine(l)
		self._writer.onDocumentEnd()

	def parseLine( self, line ):
		"""Parses the given line of text."""
		indent, line = self._getLineIndent(line)
		# First, we make sure we close the elements that may be outside of the
		# scope of this
		# FIXME: Empty lines may have an indent < than the current element they
		# are bound to
		is_comment     = RE_COMMENT.match(line)
		# Is it a comment ?
		if is_comment:
			# FIXME: Integrate this
			return
			return self._writer.onComment(line)
		self._gotoParentElement(indent)
		# Is it a declaration ?
		is_declaration = RE_DECLARATION.match(line)
		if is_declaration:
			self._elementStack.append(indent)
			declared_name = is_declaration.group(1)
			self._writer.onDeclarationStart(declared_name)
			return
		# Is it an element ?
		is_element = RE_ELEMENT.match(line)
		if is_element:
			self._elementStack.append(indent)
			groups = is_element.groups()
			self._writer.onElementStart(groups[0])
			return
		# Otherwise it's data
		self._writer.onTextAdd(line.replace("\n", " "))

	def parseContentLine( self, line ):
		"""Parses a line that is data/text that is part of an element
		content.""" 

	def _gotoParentElement( self, currentIndent ):
		print "CURRENT INDENT", currentIndent, self._elementStack
		while self._elementStack and self._elementStack[-1] >= currentIndent:
			self._elementStack.pop()
			self._writer.onElementEnd()
		print "-->", self._elementStack

	def _getLineIndent( self, line ):
		"""Returns the line indentation as a number. It takes into account the
		fact that tabs may be requried or not, and also takes into account the
		'tabsWith' property."""
		if self._tabsOnly:
			match = RE_LEADING_TAB.match(line)
			assert match
			return len(match.group()) * self._tabsWidth, line[len(match.group()):]
		else:
			raise Exception("Not implemented")

def run( arguments ):
	input_file = arguments[0]
	parser = Parser()
	parser.parseFile(input_file)

if __name__ == "__main__":
	run(sys.argv[1:])

# EOF


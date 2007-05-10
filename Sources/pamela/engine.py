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
SYMBOL_ATTR    = "(%s)(=('[^']+'|\"[^\"]+\"|([^),]+)))?" % (SYMBOL_NAME)
SYMBOL_ATTRS   = "\(%s(,%s)*\)" % (SYMBOL_ATTR, SYMBOL_ATTR)
RE_ATTRIBUTE   = re.compile(SYMBOL_ATTR)
RE_COMMENT     = re.compile("^#.*$")
RE_EMPTY       = re.compile("^\s*$")
RE_DECLARATION = re.compile("^@(%s):?" % (SYMBOL_NAME))
RE_ELEMENT     = re.compile("^\<(%s(%s)?|%s)(%s)?\:?" % (
	SYMBOL_NAME,
	SYMBOL_ID_CLS,
	SYMBOL_ID_CLS,
	SYMBOL_ATTRS
))
RE_LEADING_TAB = re.compile("\t*")
RE_LEADING_SPC = re.compile("[ ]*")

# -----------------------------------------------------------------------------
#
# Formatting function (borrowed from LambdaFactory modelwriter module)
#
# -----------------------------------------------------------------------------

FORMAT_PREFIX = "\t"
def _format( value, level=-1 ):
	"""Format helper operation. See @format."""
	if type(value) in (list, tuple):
		res = []
		for v in value:
			if v is None: continue
			res.extend(_format(v, level+1))
		return res
	else:
		if value is None: return ""
		assert type(value) in (str, unicode), "Unsupported type: %s" % (value)
		return ["\n".join((level*FORMAT_PREFIX)+v for v in value.split("\n"))]

def format( *values ):
	"""Formats a combination of string ang tuples. Strings are joined by
	newlines, and the content of the inner tuples gets indented."""
	return "\n".join(_format(values))

# -----------------------------------------------------------------------------
#
# Writer class
#
# -----------------------------------------------------------------------------

class Writer:
	"""The Writer class implements a simple SAX-like interface to create the
	resulting HTML/XML document. This is not API-compatible with SAX because
	Pamela as slightly differnt information than what SAX offers, which requires
	specific methods."""

	class Text:
		"""Reprensents a text fragment within the HTML document."""
		def __init__(self, content):
			self.content = content
		def asList(self,inSingleLine=False):
			return self.content

	class Element:
		"""Represents an element within the HTML document."""
		def __init__(self, name, attributes=None,isSingleLine=False):
			self.name=name
			self.attributes=attributes or []
			self.content=[]
			self.isSingleLine=isSingleLine
		def append(self,n):
			self.content.append(n)
		def _attributesAsHTML(self):
			"""Returns the attributes as HTML"""
			r = []
			def escape(v):
				if   v.find('"') == -1: v = '"%s"' % (v)
				elif v.find("'") == -1: v = "'%s'" % (v)
				else: v = '"%s"' % (v.replace('"', '\\"'))
				return v
			for name, value in self.attributes:
				if value is None:
					r.append("%s" % (name))
				else:
					r.append("%s=%s" % (name,escape(value)))
			r = " ".join(r)
			if r: r= " "+r
			return r
		def asList(self,inSingleLine=False):
			"""Formats this element as a list, taking into account the
			'isSingleLine' hint and the 'inSingleLine' rendering attribute."""
			attributes = self._attributesAsHTML()
			if not self.content:
				if self.isSingleLine or inSingleLine:
					return "<%s%s />" % (attributes, self.name)
				else:
					return ["<%s%s />" % (attributes, self.name)]
			else:
				if self.isSingleLine or inSingleLine:
					return "<%s%s>" % (self.name, attributes) \
					+ "".join(c.asList(inSingleLine=True) for c in self.content) \
					+ "</%s>" % (self.name)
				else:
					return [
						"<%s%s>" % (self.name, attributes),
						list(c.asList() for c in self.content),
						"</%s>" % (self.name)
					]

	class Declaration(Element):
		def __init__(self, name, attributes=None):
			Writer.Element.__init__(self,name,attributes)

	def __init__( self ):
		pass

	def onDocumentStart( self ):
		self._content   = []
		self._nodeStack = []
		self._document = self.Element("document")

	def onDocumentEnd( self ):
		r = "".join(format(c.asList()) for c in self._document.content)
		return r

	def onComment( self, line ):
		line = line.replace("\n", " ").strip()
		#comment = ET.Comment(line)
		#self._node().append(comment)

	def onTextAdd( self, text, onSameLine=False ):
		"""Adds the given text fragment to the current element. When
		'onSameLine', it means that the text fragment was on the same line as
		the element, like this:

		>    <title:Here is my title

		as opposed to

		>    <title
		>       Here is my title

		this will trigger (or not) a rendering hint that will tell the current
		element to render as multi or single line."""
		if not onSameLine:
			self._node().isSingleLine = False
		self._node().append(self.Text(text))

	def onElementStart( self, name, attributes=None,isSingleLine=False ):
		element = self.Element(name,attributes=attributes,isSingleLine=isSingleLine)
		self._node().append(element)
		self._nodeStack.append(element)

	def onElementEnd( self ):
		self._nodeStack.pop()

	def onDeclarationStart( self, name, attributes=None ):
		element = self.Declaration(name)
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
		self._tabsOnly   = False
		self._spacesOnly = False
		self._tabsWidth  = 4
		self._elementStack = []
		self._writer = Writer()

	def parseFile( self, path ):
		# FIXME: File exists and is readable
		f = file(path, "r")
		self._writer.onDocumentStart()
		for l in f.readlines():
			self.parseLine(l)
		return self._writer.onDocumentEnd()

	def parseLine( self, line ):
		"""Parses the given line of text."""
		indent, line = self._getLineIndent(line)
		# First, we make sure we close the elements that may be outside of the
		# scope of this
		# FIXME: Empty lines may have an indent < than the current element they
		# are bound to
		is_empty       = RE_EMPTY.match(line)
		if is_empty:
			return
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
			group  = is_element.group()[1:]
			rest   = line[len(is_element.group()):]
			# Element is a single line if it ends with ':'
			if group[-1] == ":": is_single_line = True
			else: is_single_line = False
			name,attributes,hints=self.parsePamelaElement(group)
			self._writer.onElementStart(name, attributes, isSingleLine=is_single_line)
			if rest:
				self._writer.onTextAdd(rest.replace("\n", " "), onSameLine=True)
			return
		# Otherwise it's data
		self._writer.onTextAdd(line.replace("\n", " "))

	def parseContentLine( self, line ):
		"""Parses a line that is data/text that is part of an element
		content.""" 

	def parsePamelaElement( self, element ):
		"""Parses the declaration of a Pamela element, which is like that

		>	(#ID | NAME #ID?) .CLASS* ATTRIBUTES? |HINTS? :?

		where attributes is a command-separated sequence of this, surrounded by
		parens:

		>	NAME=(VALUE|'VALUE'|"VALUE")

		This function returns a tuple (name, id, classes, attributes, hints)
		representing this parsed element."""
		original = element
		if element[-1] == ":": element = element[:-1]
		# We look for the attributes list
		parens_start = element.find("(")
		if parens_start != -1:
			attributes_list = element[parens_start+1:]
			if attributes_list[-1] == ")": attributes_list = attributes_list[:-1]
			attributes = self.parsePamelaAttributes(attributes_list)
			element = element[:parens_start]
		else:
			attributes = []
		# We look for the classes
		classes = element.split(".")
		if len(classes) > 1:
			element = classes[0]
			classes = classes[1:]
			classes = " ".join( classes)
			attributes.append(["class", classes])
		else:
			element = classes[0]
		eid = element.split("#")
		# FIXME: If attributes or ids are already defined, we should look for it
		# and do something appropriate
		if len(eid) > 1:
			assert len(eid) == 2, "More than one id given: %s" % (original)
			attributes.append(["id", eid[1]])
			element = eid[0]
		else:
			element = eid[0]
		return (element, attributes, [])

	def parsePamelaAttributes( self, attributes ):
		result = []
		original = attributes
		while attributes:
			match  = RE_ATTRIBUTE.match(attributes)
			assert match, "Given attributes are malformed: %s" % (attributes)
			name  = match.group(1)
			value = match.group(3)
			if value and value[0] == value[-1] and value[0] in ("'", '"'):
				value = value[1:-1]
			result.append([name, value])
			attributes = attributes[match.end():]
			if attributes:
				assert attributes[0] == ",", "Attributes must be comma-separated: %s" % (attributes)
				attributes = attributes[1:]
				assert attributes, "Trailing comma with no remaining attributes: %s" % (original)
		return result

	def _gotoParentElement( self, currentIndent ):
		while self._elementStack and self._elementStack[-1] >= currentIndent:
			self._elementStack.pop()
			self._writer.onElementEnd()

	def _getLineIndent( self, line ):
		"""Returns the line indentation as a number. It takes into account the
		fact that tabs may be requried or not, and also takes into account the
		'tabsWith' property."""
		tabs = RE_LEADING_TAB.match(line)
		spaces = RE_LEADING_SPC.match(line)
		if self._tabsOnly and spaces:
			raise Exception("Tabs are expected, your lines are indented with spaces")
		if self._spacesOnly and tabs:
			raise Exception("Spaces are expected, your lines are indented with tabs")
		if tabs and len(tabs.group()) > 0:
			return len(tabs.group()) * self._tabsWidth, line[len(tabs.group()):]
		elif spaces and len(spaces.group()) > 0:
			return len(spaces.group()), line[len(spaces.group()):]
		else:
			return 0, line

# -----------------------------------------------------------------------------
#
# Command-line interface
#
# -----------------------------------------------------------------------------

def run( arguments ):
	input_file = arguments[0]
	parser = Parser()
	print parser.parseFile(input_file)

# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	run(sys.argv[1:])

# EOF


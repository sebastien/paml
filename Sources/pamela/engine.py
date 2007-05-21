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
# Last mod.         :   21-May-2007
# -----------------------------------------------------------------------------

import os, sys, re

PAMELA_VERSION = "0.2.5"

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
# Object Model
#
# -----------------------------------------------------------------------------

FORMAT_INDENT = "i"
FORMAT_SINGLE_LINE = "sl"
FORMAT_PRESERVE = "p"
FORMAT_NORMALIZE = "n"
FORMAT_STRIP = "s"
FORMAT_COMPACT = "c"

class Text:
	"""Reprensents a text fragment within the HTML document."""
	def __init__(self, content):
		self.content = content

class Element:
	"""Represents an element within the HTML document."""
	def __init__(self, name, attributes=None,isSingleLine=False):
		self.name=name
		self.attributes=attributes or []
		self.content=[]
		self.isSingleLine=isSingleLine
		self.formatOptions = []
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

class Declaration(Element):
	def __init__(self, name, attributes=None):
		Writer.Element.__init__(self,name,attributes)

# -----------------------------------------------------------------------------
#
# Formatting function (borrowed from LambdaFactory modelwriter module)
#
# -----------------------------------------------------------------------------

class Formatter:
	"""Formats the elements of the Pamela object model."""

	def __init__( self ):
		pass

	def formatContent( self, element ):
		"""Returns a string representing the formatting of the given 'element'
		content."""
		result = []
		for e in element.content:
			if isinstance(e, Element):
				result.append(self.formatElement(e))
			elif isinstance(e, Text):
				result.append(self.formatText(e))
			else:
				raise Exception("Unsupported content type: %s" % (e))
		return "\n".join(result)

	def formatElement( self, element ):
		"""Returns the given element (and its content) as a string formatted
		according to this formatter configuration."""
		attributes = element._attributesAsHTML()
		if element.content:
			start   = "<%s%s>" % (element.name, attributes)
			end     = "</%s>" % (element.name)
			content = self.formatContent(element)
			content = self.indent(content, 2)
			return start + "\n" + content + end
		else:
			return "<%s%s />" % (attributes, self.name)

	def formatText( self, element ):
		"""Returns the given text element properly formatted according to
		this formatted configuration."""
		return element.content

	def indent( self, text, indent, start=True, end=True ):
		"""Indents the given 'text' with the given 'value' (which will be
		converted to either spaces or tabs, depending on the formatter
		parameters.

		If 'start' is True, then the start line will be indented as well,
		otherwise it won't. When 'end' is True, a newline is inserted at
		the end of the resulting text, otherwise not."""
		first_line = True
		result     = []
		prefix     = self.indentToText(indent)
		for line in text.split("\n"):
			if first_line and not start:
				result.append(line)
			else:
				result.append(prefix + line)
			first_line = False
		result = "\n".join(result)
		if end: result += "\n"
		return result

	def indentToText( self, indent ):
		"""Converts the 'indent' value to a string filled with spaces or tabs
		depending on the formatter parameters."""
		return " " * int(indent)



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

	def __init__( self ):
		pass

	def onDocumentStart( self ):
		self._content   = []
		self._nodeStack = []
		self._document  = Element("document")

	def onDocumentEnd( self ):
		return self._document

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
		self._node().append(Text(text))

	def onElementStart( self, name, attributes=None,isSingleLine=False ):
		element = Element(name,attributes=attributes,isSingleLine=isSingleLine)
		self._node().append(element)
		self._nodeStack.append(element)

	def onElementEnd( self ):
		self._nodeStack.pop()

	def onDeclarationStart( self, name, attributes=None ):
		element = Declaration(name)
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
	"""Implements a parser that will turn a Pamela document into an HTML
	document, returned as a string.

	The main methods that you should use are

	- 'parseFile' to parse file identified by the given path
	- 'parseString' to parse a string given as parameter

	You can configure the parser by using the following methods:

	- 'acceptTabsOnly', to tell that the parser will only accept tabs.
	- 'acceptSpacesOnly', to tell that the parser will only accept spaces.
	- 'acceptTabsAndSpaces', to tell that the parser will accept both tabs and
	   spaces.
	- 'tabsWidth', to specify the width of a tab in spaces, which is only used
	   when the parser accepts both tabs and spaces.
	"""

	def __init__( self ):
		self._tabsOnly   = False
		self._spacesOnly = False
		self._tabsWidth  = 4
		self._elementStack = []
		self._writer = Writer()
		self._formatter = Formatter()

	def parseFile( self, path ):
		"""Parses the file with the given  path, and return the corresponding
		HTML document."""
		# FIXME: File exists and is readable
		f = file(path, "r")
		self._writer.onDocumentStart()
		for l in f.readlines():
			self._parseLine(l)
		return self._formatter.formatContent(self._writer.onDocumentEnd())

	def _parseLine( self, line ):
		"""Parses the given line of text.
		This is an internal method that you should not really use directly."""
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
			name,attributes,hints=self._parsePamelaElement(group)
			self._writer.onElementStart(name, attributes, isSingleLine=is_single_line)
			if rest:
				self._writer.onTextAdd(rest.replace("\n", " "), onSameLine=True)
			return
		# Otherwise it's data
		self._writer.onTextAdd(line.replace("\n", " "))

	def _parseContentLine( self, line ):
		"""Parses a line that is data/text that is part of an element
		content.""" 

	def _parsePamelaElement( self, element ):
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
			attributes = self._parsePamelaAttributes(attributes_list)
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

	def _parsePamelaAttributes( self, attributes ):
		"""Parses a string representing Pamela attributes and returns a list of
		couples '[name, value]' representing the attributes."""
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
		"""Finds the parent element that has an identation lower than the given
		'currentIndent'."""
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


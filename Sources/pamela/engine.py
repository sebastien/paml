#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project           :   Pamela
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   10-May-2007
# Last mod.         :   17-Mar-2008
# -----------------------------------------------------------------------------

import os, sys, re

__version__ = "0.3.5"
PAMELA_VERSION = __version__

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

SYMBOL_NAME    = "\??([\w\d_-]+::)?[\w\d_-]+"
SYMBOL_ID_CLS  = "(\#%s|\.%s)+" % (SYMBOL_NAME, SYMBOL_NAME)
SYMBOL_ATTR    = "(%s)(=('[^']+'|\"[^\"]+\"|([^),]+)))?" % (SYMBOL_NAME)
SYMBOL_ATTRS   = "\(%s(,%s)*\)" % (SYMBOL_ATTR, SYMBOL_ATTR)
SYMBOL_CONTENT = "@\w+"
SYMBOL_ELEMENT = "<(%s(%s)?|%s)(%s)?(%s)?\:?" % (
	SYMBOL_NAME,
	SYMBOL_ID_CLS,
	SYMBOL_ID_CLS,
	SYMBOL_ATTRS,
	SYMBOL_CONTENT
)
RE_ATTRIBUTE   = re.compile(SYMBOL_ATTR)
RE_COMMENT     = re.compile("^#.*$")
RE_EMPTY       = re.compile("^\s*$")
RE_DECLARATION = re.compile("^@(%s):?" % (SYMBOL_NAME))
RE_ELEMENT     = re.compile("^%s" % (SYMBOL_ELEMENT))
RE_INLINE      = re.compile("%s" % (SYMBOL_ELEMENT))
RE_LEADING_TAB = re.compile("\t*")
RE_LEADING_SPC = re.compile("[ ]*")
RE_SPACE       = re.compile("[\s\n]")

T_ELEMENT      = "EL"
T_DECLARATION  = "DC"
T_EMBED        = "EM"

# -----------------------------------------------------------------------------
#
# Formatting
#
# -----------------------------------------------------------------------------

FORMAT_INLINE       = "i"
FORMAT_INLINE_BLOCK = "ib"
FORMAT_SINGLE_LINE  = "sl"
FORMAT_PRESERVE     = "p"
FORMAT_NORMALIZE    = "n"
FORMAT_STRIP        = "s"
FORMAT_COMPACT      = "c"
FORMAT_WRAP         = "w"
FORMAT_OPTIONS      = (
	FORMAT_INLINE,
	FORMAT_INLINE_BLOCK,
	FORMAT_SINGLE_LINE,
	FORMAT_PRESERVE,
	FORMAT_NORMALIZE,
	FORMAT_STRIP,
	FORMAT_COMPACT,
)

# Defaults for HTML documents
HTML_DEFAULTS = {
	"script":"i".split(),
	"link":"i".split(),
	"title":"sl n s".split(),
	"h1":"sl n s".split(),
	"h2":"sl n s".split(),
	"h3":"sl n s".split(),
	"h4":"sl n s".split(),
	"p":"n s c w".split(),
	"code":"n s c".split(),
	"pre":"p".split(),
	"div":"ib".split()
}

HTML_EXCEPTIONS = {
	"script":{
		"NOT_EMPTY":" "
	},
	"textarea":{
		"NOT_EMPTY":" "
	},
	"iframe":{
		"NOT_EMPTY":" "
	},
	"div":{
		"NOT_EMPTY":"&nbsp;"
	}
}
# -----------------------------------------------------------------------------
#
# Object Model
#
# -----------------------------------------------------------------------------

class Text:
	"""Reprensents a text fragment within the HTML document."""
	def __init__(self, content):
		self.content = content

class Element:
	"""Represents an element within the HTML document."""

	def __init__(self, name, attributes=None,isInline=False,isPI=False):
		self.name          = name
		self.attributes    = attributes or []
		self.content       = []
		self.isInline      = isInline
		self.isPI          = isPI
		self.formatOptions = []
		if name[0] == "?":
			self.isPI = True
			self.name = name[1:]

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

RE_SPACES = re.compile("\s")

class Formatter:
	"""Formats the elements of the Pamela object model. A formatter really acts
	as a state machine, and keeps track of the various formatting hints bound to
	the Pamela XML/HTML elements to render the document in the most appropriate
	way.
	
	If you instanciate a formatter, you'll have access to the following
	attributes, which can influence the generated text:
	
	 - 'indent=0'
	 - 'indentValue="  "'
	 - 'textWidth=80'
	 - 'defaults=HTML_DEFAULT'

	"""

	def __init__( self ):
		"""Creates a new formatter."""
		self.indent = 0
		self.indentValue = "  "
		self.textWidth = 80
		# FIXME
		self.defaults = {}
		self.defaults = HTML_DEFAULTS
		self.flags    = [[]]

	def setDefaults( self, element, formatOptions=()):
		"""Sets the formatting defaults for the given element name."""
		assert type(element) in (str, unicode)
		assert type(formatOptions) in (list, tuple)
		for f in formatOptions:
			assert f in FORMAT_OPTIONS, "Unknown formatting option: %s" % (f)
		self.defaults[element] = list(formatOptions)

	def getDefaults( self, elementName ):
		"""Gets the formatting defaults for the given element name."""
		return self.defaults.get(elementName) or ()

	def pushFlags( self, *flags ):
		"""Pushes the given flags (as varargs) on the flags queue."""
		self.flags.append([])
		map(self.setFlag, flags)

	def setFlag( self, flag ):
		"""Sets the given flag."""
		if flag == FORMAT_SINGLE_LINE:
			self.setFlags(FORMAT_STRIP, FORMAT_NORMALIZE)
		if flag not in self.flags[-1]:
			self.flags[-1].append(flag)

	def setFlags( self, *flags ):
		"""Set the given flags, given as varargs."""
		map(self.setFlag, flags)

	def popFlags( self ):
		"""Pops the given flags from the flags queue."""
		self.flags.pop()

	def hasFlag( self, flag ):
		"""Tells if the given flag is currently defined."""
		if flag == FORMAT_SINGLE_LINE:
			single_line = self.findFlag(flag)
			preserve    = self.findFlag(FORMAT_PRESERVE)
			if single_line > preserve: return True
			else: return False
		else:
			return self.findFlag(flag) != -1

	def getFlags( self ):
		"""Returns the list of defined flags, by order of definition (last flags
		are more recent."""
		res = []
		for flags in self.flags:
			res.extend(flags)
		return res

	def findFlag( self, flag ):
		"""Finds the level at which the given flag is defined. Returns -1 if it
		is not found."""
		for i in range(0, len(self.flags)):
			j = len(self.flags) - 1 - i
			if flag in self.flags[j]:
				return j
		return -1

	# -------------------------------------------------------------------------
	# MAIN FORMATTING OPERATIONS
	# -------------------------------------------------------------------------

	def format( self, document, indent=0 ):
		"""Formats the given document, starting at the given indentation (0 by
		default)."""
		self.startWriting()
		self.indent = indent
		self._formatContent(document)
		return self.endWriting()

	def _formatContent( self, element ):
		"""Formats the content of the given element. This uses the formatting
		operations defined in this class."""
		text   = []
		# NOTE: In this process we aggregate text elements, which are typically
		# one text element per line. This allows proper formatting
		for e in element.content:
			if isinstance(e, Element):
				if text:
					self.writeText("".join(text))
					text = []
				self._formatElement(e)
			elif isinstance(e, Text):
				text.append(e.content)
			else:
				raise Exception("Unsupported content type: %s" % (e))
		if text:
			text = "".join(text)
			if not element.isInline:
				while text and text[-1] in "\n\t ": text = text[:-1]
			self.writeText(text)

	def _inlineCanSpanOneLine( self, element ):
		"""Tells wether the given element (when considered as an inline) can
		span one single line. It can if only it has inlines that can span
		one line and text without EOLs as content."""
		if isinstance(element, Text):
			return element.content.find("\n") == -1
		else:
			for c in element.content:
				if not self._inlineCanSpanOneLine(c):
					return False
			return True
	
	def _formatElement( self, element ):
		"""Formats the given element and its content, by using the formatting
		operations defined in this class."""
		attributes = element._attributesAsHTML()
		exceptions = HTML_EXCEPTIONS.get(element.name)
		content = element.content
		if exceptions:
			not_empty = exceptions.get("NOT_EMPTY")
			if not_empty != None and not content:
				element.content.append(Text(not_empty))
		# Does this element has any content ?
		if element.content:
			self.pushFlags(*self.getDefaults(element.name))
			if element.isPI:
				assert not attributes, "Processing instruction cannot have attributes"
				start   = "<?%s " % (element.name)
				end     = " ?>"
			else:
				start   = "<%s%s>" % (element.name, attributes)
				end     = "</%s>" % (element.name)
			if self.hasFlag(FORMAT_INLINE):
				if self._inlineCanSpanOneLine(element):
					self.setFlag(FORMAT_SINGLE_LINE)
			# If the element is an inline, we enter the SINGLE_LINE formatting
			# mode, without adding an new line
			if element.isInline:
				self.pushFlags(FORMAT_SINGLE_LINE)
				self.writeTag(start)
				self._formatContent(element)
				self.writeTag(end)
				self.popFlags()
			# Or maybe the element has a SINGLE_LINE flag, in which case we add a
			# newline inbetween
			elif self.hasFlag(FORMAT_SINGLE_LINE):
				self.newLine()
				self.writeTag(start)
				self._formatContent(element)
				self.writeTag(end)
			# Otherwise it's a normal open/closed element
			else:
				self.newLine()
				self.writeTag(start)
				self.newLine()
				self.startIndent()
				self._formatContent(element)
				self.endIndent()
				self.ensureNewLine()
				self.writeTag(end)
			self.popFlags()
		# Otherwise it doesn't have any content
		else:
			text =  "<%s%s />" % (element.name, attributes)
			# And if it's an inline, we don't add a newline
			if not element.isInline: self.newLine()
			self.writeTag(text)

	def formatText( self, text ):
		"""Returns the given text properly formatted according to
		this formatted configuration."""
		if not self.hasFlag(FORMAT_PRESERVE):
			if self.hasFlag(FORMAT_NORMALIZE):
				text = self.normalizeText(text)
			if self.hasFlag(FORMAT_STRIP):
				text = self.stripText(text)
			if not self.hasFlag(FORMAT_SINGLE_LINE):
				compact = self.hasFlag(FORMAT_COMPACT)
				text = self.indentString(text, start=not compact, end=not compact)
		return text

	# -------------------------------------------------------------------------
	# TEXT OUTPUT COMMANDS
	# -------------------------------------------------------------------------

	def _isNewLine( self ):
		"""Tells wether the current line is a new line."""
		if not self._result or not self._result[-1]: return False
		return not self._result or self._result[-1][-1] == "\n"

	def _ensureNewLine( self ):
		"""Ensures that there is a new line."""
		if not self._isNewLine():
			if not  self._result:
				self._result.append("")
			else:
				self._result[-1] = self._result[-1] + "\n"

	def startWriting( self ):
		self._result = []

	def startIndent( self ):
		self.indent += 1

	def endIndent( self ):
		assert self.indent > 0
		self.indent -= 1
		self._ensureNewLine()

	def newLine( self ):
		self._ensureNewLine()

	def ensureNewLine( self ):
		self._ensureNewLine()

	def writeTag( self, tagText ):
		if self._isNewLine():
			self._result.append(self.indentAsSpaces() + tagText)
		else:
			self._result[-1] = self._result[-1] + tagText

	def writeText( self, text ):
		result = self._result
		if self.hasFlag(FORMAT_PRESERVE):
			#print "APPEND ",repr(text)
			result.append(text)
		else:
			if self._isNewLine():
				if self.hasFlag(FORMAT_WRAP):
					#print "WRAP ",repr(self.wrapText(text))
					result.append(self.wrapText(text))
				else:
					#print "INDENT ",repr(self.indentAsSpaces() + text)
					result.append( self.indentAsSpaces() + text)
			elif result:
				offset = len(result[-1])
				if self.hasFlag(FORMAT_WRAP):
					#print "APPEND WRAP ",repr(self.wrapText(text, len(result[-1])))
					result[-1] = result[-1] + self.wrapText(text, len(result[-1]))
				else:
					#print "APPEND ",repr(text)
					result[-1] = result[-1] + text
			else:
				if self.hasFlag(FORMAT_WRAP):
					result.append(self.wrapText(text, len(result[-1])))
				else:
					result.append(text)

	def endWriting( self ):
		res = "".join(self._result)
		del self._result
		return res

	def _iterateOnWords( self, text ):
		"""Splits the given text into words (separated by ' ', '\t' or '\n') and
		returns an iterator on these words.
		
		This function is used by 'wrapText'."""
		offset = 0
		space  = None
		inline = None
		while offset < len(text):
			space  = RE_SPACE.search(text, offset)
			inline = RE_INLINE.search(text, offset)
			if space:
				if inline and inline.start() < space.start():
					end = text.find(">", inline.end()) + 1
					yield text[offset:end]
					offset = end
				else:
					yield text[offset:space.start()]
					offset = space.end()
			else:
				yield text[offset:]
				offset = len(text)
		if space and space.end() == len(text) \
		or inline and inline.end() == len(text):
			yield ""

	def wrapText( self, text, offset=0, textWidth=80, indent=None ):
		"""Wraps the given text at the given 'textWidth', starting at the given
		'offset' with the given optional 'ident'."""
		words = []
		for word in self._iterateOnWords(text):
			words.append(word)
		return " ".join(words)

	# -------------------------------------------------------------------------
	# TEXT MANIPULATION OPERATIONS
	# -------------------------------------------------------------------------

	def indentString( self, text, indent=None, start=True, end=False ):
		"""Indents the given 'text' with the given 'value' (which will be
		converted to either spaces or tabs, depending on the formatter
		parameters.

		If 'start' is True, then the start line will be indented as well,
		otherwise it won't. When 'end' is True, a newline is inserted at
		the end of the resulting text, otherwise not."""
		if indent is None: indent = self.indent
		first_line = True
		result     = []
		prefix     = self.indentAsSpaces(indent)
		lines      = text.split("\n")
		line_i     = 0
		for line in lines:
			if not line and line_i == len(lines)-1:
				continue
			if first_line and not start:
				result.append(line)
			else:
				result.append(prefix + line)
			first_line = False
			line_i += 1
		result = "\n".join(result)
		if end: result += "\n"
		return result

	def indentAsSpaces( self, indent=None, increment=0 ):
		"""Converts the 'indent' value to a string filled with spaces or tabs
		depending on the formatter parameters."""
		if indent is None: indent = self.indent
		return self.indentValue * (indent + increment)

	def normalizeText( self, text ):
		"""Replaces the tabs and eols by spaces, ignoring the value of tabs."""
		return RE_SPACES.sub(" ", text)

	def stripText( self, text ):
		"""Strips leading and trailing spaces or eols from this text"""
		while text and text[0] in '\t\n ':
			text = text[1:]
		while text and text[-1] in '\t\n ':
			text = text[:-1]
		return text

	def reformatText( self, text ):
		"""Reformats a text so that it fits a particular text width."""
		return text

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

	def onTextAdd( self, text ):
		"""Adds the given text fragment to the current element."""
		self._node().append(Text(text))

	def onElementStart( self, name, attributes=None,isInline=False ):
		element = Element(name,attributes=attributes,isInline=isInline)
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
		return self._formatter.format(self._writer.onDocumentEnd())

	def parseText( self, text ):
		"""Parses the given string and returns an HTML document."""
		self._writer.onDocumentStart()
		for line in text.split("\n"):
			self._parseLine(line + "\n")
		return self._formatter.format(self._writer.onDocumentEnd())

	def _isInEmbed( self ):
		"""Tells if the current element is an embed element (like
		CSS,PHP,etc)"""
		return len(self._elementStack) > 0 and self._elementStack[-1][1] == T_EMBED

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
			# FIXME: When you have an empty line followed by content which is
			# text with same or greeater indent, the empty line  should be taken
			# into account. Same for elements with greater indent.
			return
		is_comment     = RE_COMMENT.match(line)
		# Is it a comment ?
		if is_comment and not self._isInEmbed():
			# FIXME: Integrate this
			return
			return self._writer.onComment(line)
		self._gotoParentElement(indent)
		# Is the parent an embedded element ?
		if self._isInEmbed():
			self._writer.onTextAdd(line)
			return
		# Is it a declaration ?
		is_declaration = RE_DECLARATION.match(line)
		if is_declaration:
			self._elementStack.append((indent, T_DECLARATION))
			declared_name = is_declaration.group(1)
			self._writer.onDeclarationStart(declared_name)
			return
		# Is it an element ?
		is_element = RE_ELEMENT.match(line)
		# It may be an inline element, like:
		# <a(href=/about):about> | <a(href=/sitemap):sitemap>
		if is_element:
			closing = line.find(">", is_element.end())
			opening = line.find("<", is_element.end())
			if closing == -1:
				inline_element = False
			elif opening == -1:
				inline_element = True
			elif closing < opening:
				inline_element = True
			else:
				inline_element = False
		else:
			inline_element = False
		if is_element and not inline_element:
			at_index    = is_element.group().rfind("@")
			paren_index = is_element.group().rfind(")")
			# The element is an embedded element, we use this to make sure we
			# don't interpret the content as Pamela
			if at_index > paren_index:
				self._elementStack.append((indent, T_EMBED))
			else:
				self._elementStack.append((indent, T_ELEMENT))
			group  = is_element.group()[1:]
			rest   = line[len(is_element.group()):]
			name,attributes,embed, hints=self._parsePamelaElement(group)
			# Element is a single line if it ends with ':'
			self._writer.onElementStart(name, attributes, isInline=False)
			if group[-1] == ":" and rest:
				self._parseContentLine(rest)
		else:
			# Otherwise it's data
			self._parseContentLine(line)

	def _parseContentLine( self, line ):
		"""Parses a line that is data/text that is part of an element
		content.""" 
		offset = 0
		# We look for elements in the content
		while offset < len(line):
			element = RE_INLINE.search(line, offset)
			if not element:
				break
			closing = line.find(">", element.end())
			# Elements must have a closing
			if closing == -1:
				raise Exception("Unclosed inline tag: '%s'" % (line))
			# We prepend the text from the offset to the eleemnt
			text = line[offset:element.start()]
			if text:
				self._writer.onTextAdd(text)
			# And we append the element itself
			group = element.group()[1:]
			name,attributes,embed, hints=self._parsePamelaElement(group)
			self._writer.onElementStart(name, attributes, isInline=True)
			text = line[element.end():closing]
			if text: self._writer.onTextAdd(text)
			self._writer.onElementEnd()
			offset = closing + 1
		# We add the remaining text
		if offset < len(line):
			text = line[offset:]
			if text: self._writer.onTextAdd(text)

	def _parsePamelaElement( self, element ):
		"""Parses the declaration of a Pamela element, which is like the
		following examples:

		>	html
		>	title:
		>	body#main.body(onclick=load)|c:

		basically, it is what lies between '<' and the ':' (or '\n'), which can
		be summmed up as:

		>	(#ID | NAME #ID?) .CLASS* ATTRIBUTES? |HINTS? :?

		where attributes is a command-separated sequence of this, surrounded by
		parens:

		>	NAME=(VALUE|'VALUE'|"VALUE")

		This function returns a triple (name, attributes, hints)
		representing the parsed element. Attributes are stored as an ordered
		list of couples '(name, value'), hints are given as a list of strings."""
		original = element
		if element[-1] == ":": element = element[:-1]
		# We look for the attributes list
		parens_start = element.find("(")
		at_start     = element.rfind("@")
		if parens_start != -1:
			parens_end = element.rfind(")")
			if at_start < parens_end: at_start = -1
			attributes_list = element[parens_start+1:parens_end-1]
			if attributes_list[-1] == ")": attributes_list = attributes_list[:-1]
			attributes = self._parsePamelaAttributes(attributes_list)
			element = element[:parens_start]
		else:
			attributes = []
		# Useful functions to manage attributes
		def has_attribute( name, attributes ):
			for a in attributes:
				if a[0] == name: return a
			return None
		def set_attribute( name, value, attribtues ):
			for a in attributes:
				if a[0] == name:
					a[1] = value
					return 
			attributes.append([name,value])
		def append_attribute( name, value, attributes, prepend=False ):
			a = has_attribute(name, attributes)
			if a:
				if prepend:
					a[1] = value + " " + a[1]
				else:
					a[1] = a[1] + " " + value
			else:
				set_attribute(name, value, attributes)
		# We look for the classes
		if at_start != -1:
			embed = element[at_start+1:]
			element = element[:at_start]
		else:
			embed = None
		classes = element.split(".")
		if len(classes) > 1:
			element = classes[0]
			classes = classes[1:]
			classes = " ".join( classes)
			append_attribute("class", classes, attributes, prepend=True)
		else:
			element = classes[0]
		eid = element.split("#")
		# FIXME: If attributes or ids are already defined, we should look for it
		# and do something appropriate
		if len(eid) > 1:
			assert len(eid) == 2, "More than one id given: %s" % (original)
			if has_attribute("id", attributes):
				raise Exception("Id already given as element attribute")
			attributes.insert(0,["id", eid[1]])
			element = eid[0]
		else:
			element = eid[0]
		# handle '::' syntax for namespaces
		element = element.replace("::",":")
		return (element, attributes, embed, [])

	def _parsePamelaAttributes( self, attributes ):
		"""Parses a string representing Pamela attributes and returns a list of
		couples '[name, value]' representing the attributes."""
		result = []
		original = attributes
		while attributes:
			match  = RE_ATTRIBUTE.match(attributes)
			assert match, "Given attributes are malformed: %s" % (attributes)
			name  = match.group(1)
			value = match.group(4)
			# handles '::' syntax for namespaces
			name = name.replace("::",":")
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
		while self._elementStack and self._elementStack[-1][0] >= currentIndent:
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
	t = file(input_file, 'r').read()
	return parser.parseFile(input_file)

# -----------------------------------------------------------------------------
#
# Main
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	print run(sys.argv[1:])

# EOF


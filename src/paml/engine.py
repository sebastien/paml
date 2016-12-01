#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   PAML
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                  <sebastien@ffctn.com>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   10-May-2007
# Last mod.         :   01-Dec-2016
# -----------------------------------------------------------------------------

import os, sys, re, string, json, time, glob, tempfile, argparse, types
IS_PYTHON3 = sys.version_info[0] > 2

try:
	import reporter
	logging = reporter.bind("paml")
except:
	import logging

__version__    = "0.8.3"
PAMELA_VERSION = __version__

# TODO: Add an option to start a sugar compilation server and directly query
# it, maybe using ZMQ.

def ensure_unicode( t, encoding="utf8" ):
	if IS_PYTHON3:
		return t if isinstance(t, str) else str(t, encoding)
	else:
		return t if isinstance(t, unicode) else t.decode(encoding)

def ensure_bytes( t, encoding="utf8" ):
	if IS_PYTHON3:
		return t if isinstance(t, bytes) else bytes(t, encoding)
	else:
		return t

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

SYMBOL_NAME    = "\??([\w\d_-]+::)?[\w\d_-]+"
SYMBOL_ID_CLS  = "(\#%s|\.%s)+" % (SYMBOL_NAME, SYMBOL_NAME)
SYMBOL_ATTR    = "(%s)(=('[^']+'|\"[^\"]+\"|([^),]+)))?" % (SYMBOL_NAME)
SYMBOL_ATTRS   = "\(%s(,%s)*\)" % (SYMBOL_ATTR, SYMBOL_ATTR)
SYMBOL_CONTENT = "@\w[\w\d\-_\+]*"
SYMBOL_HINTS   = "\|[a-z](\+[a-z])*"
SYMBOL_ELEMENT = "<(%s(%s)?|%s)(%s)?(%s)?(%s)?\:?" % (
	SYMBOL_NAME,
	SYMBOL_ID_CLS,
	SYMBOL_ID_CLS,
	SYMBOL_ATTRS,
	SYMBOL_HINTS,
	SYMBOL_CONTENT
)
RE_ATTRIBUTE   = re.compile(SYMBOL_ATTR)
RE_COMMENT     = re.compile("^#.*$")
RE_EMPTY       = re.compile("^\s*$")
RE_DECLARATION = re.compile("^@(%s):?" % (SYMBOL_NAME))
RE_ELEMENT     = re.compile("^%s" % (SYMBOL_ELEMENT))
RE_INLINE      = re.compile("%s" % (SYMBOL_ELEMENT))
RE_MACRO       = re.compile("^(\s)*(@\w+(:\w+)?)\s*\(([^\)]+)\)\s*$")
RE_INCLUDE     = re.compile("^(\s)*%include (.+)$")
RE_PI          = re.compile("^(\s)*\<\?.+\?\>\s*$")
RE_LEADING_TAB = re.compile("\t*")
RE_LEADING_SPC = re.compile("[ ]*")
RE_SPACE       = re.compile("[\s\n]")
RE_PROCESSING_INSTRUCTION = re.compile("^\s*\<\?.+\?\>\s*$")

T_ELEMENT      = "EL"
T_DECLARATION  = "DC"
T_EMBED        = "EM"

TAB_WIDTH      = 4

# -----------------------------------------------------------------------------
#
# FORMATTING
#
# -----------------------------------------------------------------------------

# FIXME: This does not work. What we should have is
# - compact: no leading or trailing whitepsace
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
	"script":"sl i".split(),
	"link":"i".split(),
	"title":"sl n".split(),
	"h1":"sl n".split(),
	"h2":"sl n".split(),
	"h3":"sl n".split(),
	"h4":"sl n".split(),
	"p":"n c w".split(),
	"code":"p".split(),
	"pre":"p".split(),
	"div":"ib".split()
}

HTML_EXCEPTIONS = {
	"links":dict(NO_CLOSING=True),
	"br"   :dict(NO_CLOSING=True),
	"img"  :dict(NO_CLOSING=True),
	# FIXME: No idea why there was a no closing, but this is wrong
	#"path" :dict(NO_CLOSING=True),
	"ol":{
		"NOT_EMPTY":" "
	},
	"ul":{
		"NOT_EMPTY":" "
	},
	"a":{
		"NOT_EMPTY":" "
	},
	"script":{
		"NOT_EMPTY":" "
	},
	"span":{
		"NOT_EMPTY":" "
	},
	"li":{
		"NOT_EMPTY":""
	},
	"canvas":{
		"NOT_EMPTY":" "
	},
	"textarea":{
		"NOT_EMPTY":" "
	},
	"iframe":{
		"NOT_EMPTY":" "
	},
	"div":{
		"NOT_EMPTY":" "
	},
	"td":{
		"NOT_EMPTY":"&nbsp;"
	},
	"th":{
		"NOT_EMPTY":"&nbsp;"
	}
}


# -----------------------------------------------------------------------------
#
# MACRO
#
# -----------------------------------------------------------------------------

class Macro:
	"""A collection of macros used by the parser. The `CATALOGUE` can
	be updated live to register more macros."""

	CSS_PATTERNS = (
		"lib/pcss/{0}.pcss",
		"lib/ccss/{0}.ccss",
		"lib/css/{0}.css",
		"lib/css/{0}-*.css",
	)

	JS_PATTERNS = (
		"lib/sjs/{0}.sjs",
		"lib/ts/{0}.ts",
		"lib/js/{0}.js",
		"lib/js/{0}-*.js",
	)

	GMODULE_PATTERNS = (
		"lib/sjs/{0}.sjs",
		"lib/js/{0}.gmodule.js",
		"lib/js/{0}-*.gmodule.js",
	)

	@classmethod
	def Get( cls, name ):
		return cls.CATALOGUE.get(name)

	@classmethod
	def IndentAsString( cls, indent ):
		return "\t" * (indent / TAB_WIDTH) if indent % TAB_WIDTH == 0 else " " * indent

	@staticmethod
	def Require( name, paths=[]):
		"""Globs the given expressions replacing `{0}` with the given `name`,
		returning a list containing the file with the highest version number, or
		the list of matching files in case name contains a `*`.

		For instance:

		```
		>>> Require("select", ["lib/js"])
		(`lib/js/select-0.7.9.js`)
		```

		```
		>>> Require("module-*", ["lib/sjs"])
		(`lib/sjs/module-a.sjs`, `lib/sjs/module-b.sjs`)
		```

		"""
		for p in paths:
			p = p.format(name)
			l = glob.glob(p)
			if not l: continue
			if "*" in name:
				return sorted(l)
			else:
				return (sorted(l)[-1],)
		return None

	@staticmethod
	def RequireExpand( parser, params, indent, patterns, template ):
		"""A helper function that is used by `Require{CSS,JS}`, iterates
		on the hte given parameters, and injecting the template
		when files are found matching the patterns."""
		indent = Macro.IndentAsString(indent)
		for f in params.split(","):
			f = f.strip()
			p = Macro.Require(f, patterns)
			if p:
				# We make the path relative if there file has a different path
				parser_path = parser.path()
				if parser_path != ".":
					# NOTE: We're using dirname as the path is actually the
					# filename
					p = [os.path.relpath(_, os.path.dirname(parser_path)) for _ in p]
				if len(p) > 1:
					p = "+".join([p[0]] + [os.path.basename(_) for _ in p[1:]])
				else:
					p = p[0]
				if isinstance(template, types.FunctionType):
					parser._parseLine(template(indent, p))
				else:
					parser._parseLine(template.format(indent, p))

	def RequireCSS( parser, params, indent ):
		"""The `require:css(name,...)` macro looks for files in the
		paths defined by `CSS_PATTERNS` for the given `name`s and
		replaces them by `<link>` tags."""
		Macro.RequireExpand(
			parser, params, indent,
			Macro.CSS_PATTERNS,
			"{0}<link(rel=stylesheet,type=text/css,href={1})"
		)

	def RequireJS( parser, params, indent ):
		"""The `require:js(name,...)` macro looks for files in the
		paths defined by `JS` for the given `name`s and
		replaces them by `<script>` tags."""
		Macro.RequireExpand(
			parser, params, indent,
			Macro.JS_PATTERNS,
			"{0}<script(type=text/javascript,src={1})"
		)

	def RequireGmodule( parser, params, indent ):
		"""The `require:gmodule(name,...)` macro looks for files in the
		paths defined by `JS` for the given `name`s and
		replaces them by `<script>` tags."""
		# SEE: http://stackoverflow.com/questions/1918996/how-can-i-load-my-own-js-module-with-goog-provide-and-goog-require#2007296
		loaded = []
		def formatter(indent, path, loaded=loaded):
			basename = os.path.basename(path)
			name     = basename.split(".")[0].rsplit("-",1)[0].replace("_", ".")
			# We use `deparse` to list the dependencies
			import deparse
			deps = [_[1] for _ in deparse.list([path]) if _[0] == "js:module"]
			if path.endswith(".sjs"):
				# TODO: Get dependencies
				return "{0}\tgoog.addDependency('../../../{1}',['{2}'],{3});".format(indent, path, name, json.dumps(deps))
			else:
				return "{0}\tgoog.addDependency('../../../{1}',['{2}'],{3});".format(indent, path, name, json.dumps(deps))
		parser._parseLine("{0}<script:".format(Macro.IndentAsString(indent)))
		Macro.RequireExpand(
			parser, params, indent,
			Macro.GMODULE_PATTERNS,
			formatter,
		)

	CATALOGUE = {
		"require:css":RequireCSS,
		"require:js" :RequireJS,
		"require:gmodule" :RequireGmodule,
	}

# -----------------------------------------------------------------------------
#
# OBJECT MODEL
#
# -----------------------------------------------------------------------------

class Text:
	"""Reprensents a text fragment within the HTML document."""

	def __init__(self, content):
		self.content = content

	def contentAsLines( self ):
		return [self.content]

class Element:
	"""Represents an element within the HTML document."""

	def __init__(self, name, attributes=None,isInline=False,isPI=False):
		self.name          = name
		self.attributes    = attributes or []
		self.content       = []
		self.isInline      = isInline
		self.mode          = None
		self.isPI          = isPI
		self.formatOptions = []
		if name[0] == "?":
			self.isPI = True
			self.name = name[1:]

	def setFormat( self, option):
		if option not in self.formatOptions:
			self.formatOptions.append(option)
		return self

	def getFormatFlags( self ):
		return self.formatOptions or []

	def setMode( self, mode):
		self.mode = mode

	def append(self,n):
		self.content.append(n)

	def isTextOnly( self ):
		if len(self.content) == 0:
			return True
		elif len(self.content) == 1 and isinstance(self.content[0], Text) and self.content[0].content.find("\n") == -1:
			return True
		else:
			return False

	def contentAsLines( self ):
		res = []
		for e in self.content:
			if type(e) in (str,str):
				res.append(e)
			else:
				res.extend(e.contentAsLines())
		return res

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
		Element.__init__(self,name,attributes)

# -----------------------------------------------------------------------------
#
# PARSER CLASS
#
# -----------------------------------------------------------------------------

class Parser:
	"""Implements a parser that will turn a PAML document into an HTML
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

	# NOTE: Does not seem to be used, deprecating it
	# @classmethod
	# def ExpandIncludes( cls, text=None, path=None ):
	# 	lines  = []
	# 	parser = cls()
	# 	source_lines = None
	# 	if text is None:
	# 		with open(path) as f:
	# 			source_lines = [ensure_unicode(l) for l in f.readlines()]
	# 	else:
	# 		ensure_unicode(text)
	# 		source_lines = text.split("\n")
	# 	parser._paths.append(path or ".")
	# 	for line in source_lines:
	# 		m = RE_INCLUDE.match(line)
	# 		if m:
	# 			indent, line = parser._getLineIndent(line)
	# 			parser._parseInclude(m, indent, lambda l:lines.append(ensure_unicode(l) if isinstance(l, str) else l))
	# 		else:
	# 			lines.append(line + u"\n")
	# 	return u"".join(lines)

	def __init__( self, formatter=None, defaults=None ):
		self._tabsOnly   = False
		self._spacesOnly = False
		self._tabsWidth  = TAB_WIDTH
		self._elementStack = []
		self._writer = Writer()
		self._formatter = formatter or HTMLFormatter()
		self._paths     = []
		self._defaults  = defaults or {}

	def setDefaults( self, defaults ):
		self._defaults = defaults
		return self

	def path( self ):
		"""Returns the current path of the file being parsed, if any"""
		if not self._paths or self._paths[-1] == "--":
			return "."
		else:
			return self._paths[-1]

	def indent( self ):
		if self._elementStack:
			return self._elementStack[-1][0]
		else:
			return 0

	def parseFile( self, path ):
		"""Parses the file with the given  path, and return the corresponding
		HTML document."""
		should_close = False
		if path == "--":
			f = sys.stdin
		else:
			# FIXME: File exists and is readable
			f = open(path, "r")
			should_close = True
		self._paths.append(path)
		self._writer.onDocumentStart()
		for l in f.readlines():
			self._parseLine(ensure_unicode(l))
		if should_close: f.close()
		result = self._formatter.format(self._writer.onDocumentEnd())
		self._paths.pop()
		return result

	def parseString( self, text, path=None ):
		"""Parses the given string and returns an HTML document."""
		if path: self._paths.append(path)
		try:
			text = ensure_unicode(text)
		except UnicodeEncodeError as e:
			# FIXME: What should we do?
			pass
		self._writer.onDocumentStart()
		for line in text.split("\n"):
			self._parseLine(line + "\n")
		res = self._formatter.format(self._writer.onDocumentEnd())
		if path: self._paths.pop()
		return res

	def _isInEmbed( self, indent=None ):
		"""Tells if the current element is an embed element (like
		CSS,PHP,etc)"""
		if not self._elementStack:
			return False
		elif indent is None:
			return self._elementStack[-1][1] == T_EMBED
		else:
			return self._elementStack[-1][1] == T_EMBED and self._elementStack[-1][0] < indent

	def _parseLine( self, line ):
		"""Parses the given line of text.
		This is an internal method that you should not really use directly."""
		# FIXME: This function is WAY TOO BIG, it should be broken down in
		# _parse<element>
		original_line = line
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
			if self._isInEmbed():
				line_with_indent = "\n"
				if len(line) > (self.indent()+4)/4:
					line_with_indent = original_line[(self.indent()+4)/4:]
				self._writer.onTextAdd(line_with_indent)
				return
			else:
				return
		is_comment     = RE_COMMENT.match(line)
		if is_comment and not self._isInEmbed(indent):
			# FIXME: Integrate this
			return
			return self._writer.onComment(line)
		is_pi = RE_PI.match(line)
		if is_pi:
			self._writer.onTextAdd(line)
			return
		# Is it an include element (%include ...)
		if self._parseInclude( RE_INCLUDE.match(original_line), indent ):
			return
		# Is it a macro element (%macro ...)
		if self._parseMacro( RE_MACRO.match(original_line), indent ):
			return
		self._gotoParentElement(indent)
		# Is the parent an embedded element ?
		if self._isInEmbed(indent):
			line_with_indent = original_line[int((self.indent()+4)/4):]
			self._writer.onTextAdd(line_with_indent)
			return
		# Is it a declaration ?
		is_declaration = RE_DECLARATION.match(line)
		if is_declaration:
			self._pushStack(indent, T_DECLARATION)
			declared_name = is_declaration.group(1)
			self._writer.onDeclarationStart(declared_name)
			return
		# Is it an element ?
		is_element = RE_ELEMENT.match(line)
		# It may be an inline element, like:
		# <a(href=/about):about> | <a(href=/sitemap):sitemap>
		if is_element:
			at_index    = is_element.group().rfind("@")
			paren_index = is_element.group().rfind(")")
			is_embed    = (at_index > paren_index)
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
			if is_embed:
				inline_element = False
		else:
			inline_element = False
		if is_element and not inline_element:
			# The element is an embedded element, we use this to make sure we
			# don't interpret the content as PAML
			if is_embed:
				language = is_element.group()[at_index+1:]
				if language[-1] == ":":language = language[:-1]
				self._pushStack(indent, T_EMBED, language)
			else:
				self._pushStack(indent, T_ELEMENT)
			group  = is_element.group()[1:]
			rest   = line[len(is_element.group()):]
			name,attributes,embed,hints=self._parsePAMLElement(group)
			# Element is a single line if it ends with ':'
			self._writer.onElementStart(name, attributes, isInline=False)
			if group[-1] == ":" and rest:
				self._parseContentLine(rest)
		else:
			# Otherwise it's data
			self._parseContentLine(line)

	def _tokenize( self, text, escape="\"'" ):
		res = []
		o   = 0
		end = len(text)
		while o < end:
			escape_index     = end + 1
			escape_index_end = -1
			escape_char      = None
			# We look for the closest matching escape character
			for char in escape:
				# We find the occurence of the escape char
				i = text.find(char,o)
				# If it is there and closer to the current offset than
				# the previous escape character
				if i != -1 and  i < escape_index:
					# We look for the end
					j = text.find(char,i + 1)
					# If there is an end, we assign it as the current escape
					if j != -1:
						escape_index     = i
						escape_index_end = j
						escape_char      = char
			# If we did not find an escape char
			if escape_char == None:
				res.append(text[o:])
				o = end
			else:
				if o < escape_index:
					res.append(text[o:escape_index])
				res.append(text[escape_index:escape_index_end+1])
				o = escape_index_end+1
		return res

	def _parseIncludeSubstitutions( self, text ):
		"""A simple parser that extract (key,value) from a string like
		`KEY=VALUE,KEY="VALUE\"VALUE",KEY='VALUE\'VALUE'`"""
		offset = 0
		result = [] + self._defaults.items()
		while offset < len(text):
			equal  = text.find("=", offset)
			assert equal >= 0, "Include subsitution without value: {0}".format(text)
			name   = text[offset:equal]
			offset = equal + 1
			if offset == len(text):
				value = ""
			elif text[offset] in  '\'"':
				# We test for quotes and escape it
				quote = text[offset]
				end_quote = text.find(quote, offset + 1)
				while end_quote >= 0 and text[end_quote - 1] == "\\":
					end_quote = text.find(quote, end_quote + 1)
				value  = text[offset+1:end_quote].replace("\\" + quote, quote)
				offset = end_quote + 1
				if offset < len(text) and text[offset] == ",": offset += 1
			else:
				# Or we look for a comma
				comma  = text.find(",", offset)
				if comma < 0:
					value  = text[offset:]
					offset = len(text)
				else:
					value  = text[offset:comma]
					offset = comma + 1
			result.append((name.strip(), value))
		return result

	def _parseInclude( self, match, indent, parseLine=None ):
		"""An include rule is expressed as follows
		%include PATH {NAME=VAL,...} +.class...(name=val,name,val)
		"""
		if not match: return False
		# FIXME: This could be written better
		path = match.group(2).strip()
		subs = None
		# If there is a paren, we extract the replacement
		lparen = path.rfind("{")
		offset = 0
		if lparen >= 0:
			subs    = {}
			rparen  = path.rfind("}")
			if rparen > lparen:
				for name, value in self._parseIncludeSubstitutions(path[lparen+1:rparen]):
					value       = value.strip()
					if value and value[0] in ["'", '"']: value = value[1:-1]
					subs[name] = value
				path = path[:lparen] + path[rparen+1:]
		# FIXME: The + will be swallowed if after paren
		plus = path.find("+")
		if plus >= 0:
			element = "div" + path[plus+1:].strip()
			path    = path[:plus].strip()
			_, attributes, _, _ = self._parsePAMLElement(element)
			if self._writer:
				self._writer.overrideAttributesForNextElement(attributes)
		if path[0] in ['"',"'"]:
			path = path[1:-1]
		else:
			path = path.strip()
		# Now we load the file
		local_dir  = os.path.dirname(os.path.abspath(os.path.normpath(self.path())))
		local_path = os.path.normpath(os.path.join(local_dir, path))
		if   os.path.exists(local_path):
			path = local_path
		elif os.path.exists(local_path + ".paml"):
			path = local_path + ".paml"
		elif os.path.exists(path):
			path = path
		elif os.path.exists(path + ".paml"):
			path = path + ".paml"
		if not os.path.exists(path):
			error_line = "ERROR: File not found <code>%s</code>" % (local_path)
			if parseLine:
				parseLine(error_line)
			else:
				return self._writer.onTextAdd(error_line)
		else:
			self._paths.append(path)
			with open(path,'rb') as f:
				for l in f.readlines():
					if RE_PROCESSING_INSTRUCTION.match(l): continue
					# FIXME: This does not work when I use tabs instead
					l = ensure_unicode(l)
					p = int(indent/4)
					# We do the substituion
					if subs: l = string.Template(l).safe_substitute(**subs)
					(parseLine or self._parseLine) (p * "\t" + l)
			self._paths.pop()
		return True

	def _parseMacro( self, match, indent, parseLine=None ):
		if not match: return False
		name   = match.group(2)[1:]
		params = match.group(4)
		macro  = Macro.Get(name)
		assert macro, "paml.engine: Undefined macro: {0} in {1}".format(name, match.group())
		macro(self, params, indent)
		return True

	def _pushStack(self, indent, type, mode=None):
		self._elementStack.append((indent, type))
		self._writer.pushMode(mode)

	def _popStack(self):
		self._elementStack.pop()
		self._writer.popMode()

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
			name,attributes,embed, hints=self._parsePAMLElement(group)
			self._writer.onElementStart(name, attributes, isInline=True)
			text = line[element.end():closing]
			if text: self._writer.onTextAdd(text)
			self._writer.onElementEnd()
			offset = closing + 1
		# We add the remaining text
		if offset < len(line):
			text = line[offset:]
			# We remove the trainling EOL at the end of the line. This might not
			# be the best way to do it, though.
			if text and text[-1] == "\n": text = text[:-1] + " "
			if text: self._writer.onTextAdd(text)

	def _parsePAMLElement( self, element ):
		"""Parses the declaration of a PAML element, which is like the
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
		pipe_start   = element.rfind("|")
		at_start     = element.rfind("@")
		rest         = None
		if parens_start != -1:
			parens_end = element.rfind(")")
			if at_start < parens_end: at_start = -1
			attributes_list = element[parens_start+1:parens_end]
			if attributes_list[-1] == ")": attributes_list = attributes_list[:-1]
			attributes = self._parsePAMLAttributes(attributes_list)
			element = element[:parens_start]
			rest    = element[parens_end:]
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
		# We take care of embeds
		if at_start != -1:
			embed   = element[at_start+1:]
			element = element[:at_start]
		else:
			embed = None
		# We take care of hints
		hints = []
		if pipe_start != -1:
			hints   = (original[pipe_start+1:].rsplit("@", 1)[0]).split("+")
			element = element[:pipe_start]
		# We look for the classes
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
		return (element, attributes, embed, hints)

	def _parsePAMLAttributes( self, attributes ):
		"""Parses a string representing PAML attributes and returns a list of
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
			self._popStack()
			self._writer.onElementEnd()

	def _getLineIndent( self, line ):
		"""Returns the line indentation as a number. It takes into account the
		fact that tabs may be requried or not, and also takes into account the
		'tabsWith' property."""
		line   = line or ""
		tabs   = RE_LEADING_TAB.match(line)
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
# FORMATTING FUNCTION (BORROWED FROM LAMBDAFACTORY MODELWRITER MODULE)
#
# -----------------------------------------------------------------------------

RE_SPACES = re.compile("\s")

class HTMLFormatter:
	"""Formats the elements of the PAML object model. A formatter really acts
	as a state machine, and keeps track of the various formatting hints bound to
	the PAML XML/HTML elements to render the document in the most appropriate
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
		self.useProcessCache = True

	def setDefaults( self, element, formatOptions=()):
		"""Sets the formatting defaults for the given element name."""
		assert type(element) in (str, str)
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
		for _ in flags:
			if isinstance(_,list) or isinstance(_,tuple):
				for f in _:
					self.setFlag(f)
			else:
				self.setFlag(_)

	def setFlag( self, flag ):
		"""Sets the given flag."""
		if flag == FORMAT_SINGLE_LINE:
			self.setFlags(FORMAT_NORMALIZE)
		if flag not in self.flags[-1]:
			self.flags[-1].append(flag)

	def setFlags( self, *flags ):
		"""Set the given flags, given as varargs."""
		for _ in flags: self.setFlag(_)

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
			#text = "".join(map(lambda _:_.encode("utf-8"), text))
			text  = "".join(text)
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

	# FIXME: This should probably be moved to the parser
	# FIXME: Yes, it should DEFINITELY be moved above
	def _formatElement( self, element ):
		"""Formats the given element and its content, by using the formatting
		operations defined in this class."""
		attributes = element._attributesAsHTML()
		exceptions = HTML_EXCEPTIONS.get(element.name)
		content    = element.content
		mode       = element.mode.split("+")[0] if element.mode else None
		# FIXME: Flags are not properly supported
		if exceptions:
			not_empty = exceptions.get("NOT_EMPTY")
			if not_empty != None and not content:
				element.content.append(Text(not_empty))
		# Does this element has any content that needs to be pre-processed?
		if mode == "sugar":
			lines = element.contentAsLines()
			import paml.web
			source = u"".join(lines)
			t = time.time()
			res, _ = paml.web.processSugar(source, "", cache=self.useProcessCache, includeSource=element.mode.endswith("+source"))
			logging.trace("Parsed Sugar: {0} lines in {1:0.2f}s".format(len(lines), time.time() - t))
			element.content = [Text(res)]
		elif mode in ("coffeescript", "coffee"):
			lines = element.contentAsLines()
			import paml.web
			source = u"".join(lines)
			t = time.time()
			res, _ = paml.web.processCoffeeScript(source, "", cache=self.useProcessCacheFalse)
			logging.trace("Parsed CoffeeScript: {0} lines in {1:0.2f}s".format(len(lines), time.time() - t))
			element.content = [Text(res)]
		elif mode in ("typescript", "ts"):
			lines = element.contentAsLines()
			import paml.web
			source = u"".join(lines)
			t = time.time()
			res, _ = paml.web.processTypeScript(source, "", cache=self.useProcessCacheFalse)
			logging.trace("Parsed TypeScript: {0} lines in {1:0.2f}s".format(len(lines), time.time() - t))
			element.content = [Text(res)]
		elif mode  in ("clevercss", "ccss"):
			lines = element.contentAsLines()
			import paml.web
			source = u"".join(lines)
			t = time.time()
			res, _ = paml.web.processCleverCSS(source, ".")
			logging.trace("Parsed CleverCSS: {0} lines in {1:0.2f}s".format(len(lines), time.time() - t))
			element.content = [Text(res)]
		elif mode  in ("pythoniccss", "pcss"):
			lines = element.contentAsLines()
			import paml.web
			source = u"".join(lines)
			t = time.time()
			res, _ = paml.web.processPythonicCSS(source, ".")
			logging.trace("Parsed PythonicCSS: {0} lines in {1:0.2f}s".format(len(lines), time.time() - t))
			element.content = [Text(res)]
		elif element.mode and element.mode.endswith("nobrackets"):
			lines = element.contentAsLines()
			import paml.web
			source = u"".join(lines)
			t = time.time()
			prefix = element.mode[0:0-(len("nobrackets"))]
			suffix = ".nb"
			if prefix: suffix = "." + prefix + suffix
			p = tempfile.mktemp(suffix=suffix)
			with open(p, "w") as f: f.write(source)
			res, _ = paml.web.processNobrackets(source, p)
			if os.path.exists(p): os.unlink(p)
			logging.trace("Parsed Nobrackets: {0} lines in {1:0.2f}s".format(len(lines), time.time() - t))
			element.content = [Text(res)]
		elif mode == "texto":
			lines = element.contentAsLines()
			import texto
			source = u"".join(lines)
			res    = ensure_unicode(texto.toHTML(source))
			element.content = [Text(res)]
			self.setFlag(FORMAT_PRESERVE)
		elif mode == "hjson":
			lines = element.contentAsLines()
			import hjson
			source = u"".join(lines)
			res    = ensure_unicode(hjson.dumpsJSON(hjson.loads(source)))
			element.content = [Text(res)]
		elif mode == "raw":
			text = "".join(element.contentAsLines())
			while text and text[-1] in "\n\t":
				text = text[:-1]
			element.content = [Text(text)]
			element.setFormat(FORMAT_PRESERVE)
			element.setFormat(FORMAT_COMPACT)
		# NOTE: This is a post-processor
		if element.mode and (element.mode.endswith ("+escape") or "+escape+" in element.mode):
			for text in element.content:
				if isinstance(text, Text):
					text.content = text.content.replace("<", "&lt;").replace(">", "&gt;")
		# If the element has any content, then we apply it
		if element.content:
			flags = element.getFormatFlags() + list(self.getDefaults(element.name))
			self.pushFlags(*flags)
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
			# FIXME: isInline is always false
			if element.isInline:
				self.pushFlags(FORMAT_SINGLE_LINE)
				self.writeTag(start)
				self._formatContent(element)
				self.writeTag(end)
				self.popFlags()
			# Or maybe the element has a SINGLE_LINE flag, in which case we add a
			# newline inbetween
			elif self.hasFlag(FORMAT_SINGLE_LINE) or element.isTextOnly():
				self.writeTag(start)
				self._formatContent(element)
				self.writeTag(end)
			# Otherwise it's a normal open/closed element
			else:
				self.newLine()
				self.writeTag(start)
				if not self.hasFlag(FORMAT_COMPACT):
					self.newLine()
					self.startIndent()
				self._formatContent(element)
				if not self.hasFlag(FORMAT_COMPACT):
					self.endIndent()
					self.ensureNewLine()
				self.writeTag(end)
			self.popFlags()
		# Otherwise it doesn't have any content
		else:
			if exceptions and exceptions.get("NO_CLOSING"):
				text =  "<%s%s>" % (element.name, attributes)
			else:
				text =  "<%s%s />" % (element.name, attributes)
			# And if it's an inline, we don't add a newline
			if not element.isInline: self.newLine()
			self.writeTag(text)

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
		text   = self.formatText(text)
		if self.hasFlag(FORMAT_PRESERVE):
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
				text    = self.indentString(text, start=not compact, end=not compact)
		return text

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
# JAVASCRIPT HTML FORMATTER
#
# -----------------------------------------------------------------------------

class JSFormatter( HTMLFormatter ):
	"""Formats the given PAML document to a JavaScript source code
	using the 'html.js' markup file."""

	def format( self, document, indent=0 ):
		elements = [v for v in document.content if isinstance(v, Element)]
		assert len(elements) == len(document.content) == 1, "JSHTMLFormatter can only be used with one element"
		return self._formatContent(elements[0])

	def _formatContent( self, value ):
		"""Formats the content of the given element. This uses the formatting
		operations defined in this class."""
		# FIXME: Should escape entities
		if isinstance( value, Text ):
			return  json.dumps(value.content)
		elif isinstance( value, Element ):
			element = value
			if element.isPI: return ""
			res = ["html.%s(" % (element.name)]
			cnt = []
			if element.attributes:
				attr = []
				for name, value in element.attributes:
					attr.append("%s:%s" % (json.dumps(name), json.dumps(value)))
				cnt.append("{%s}" % (",".join(attr)))
			for child in element.content:
				cnt.append(self._formatContent(child))
			res.append(",".join(cnt))
			res.append(")")
			return "".join(res)
		else:
			assert None, "Unrecognized value type: " + str(value)

# -----------------------------------------------------------------------------
#
# WRITER CLASS
#
# -----------------------------------------------------------------------------

# TODO: rename AbstractWriter
class Writer:
	"""The Writer class implements a simple SAX-like interface to create the
	resulting HTML/XML document. This is not API-compatible with SAX because
	PAML has slightly different information than what SAX offers, which requires
	specific methods."""

	def __init__( self ):
		self.onDocumentStart()

	def onDocumentStart( self ):
		self._modes     = []
		self._content   = []
		self._nodeStack = []
		self._document  = Element("document")
		self._override  = None
		self._bemStack  = []

	def onDocumentEnd( self ):
		return self._document

	def onComment( self, line ):
		line = line.replace("\n", " ").strip()
		# FIXME: Why is this disabled ?
		#comment = ET.Comment(line)
		#self._node().append(comment)

	def onTextAdd( self, text ):
		"""Adds the given text fragment to the current element."""
		self._node().append(Text(text))

	def onElementStart( self, name, attributes=None,isInline=False ):
		# We extend the override if present
		if self._override:
			# FIXME: This would be much more elegant with an ordered key-value
			# pair set
			keys           = []
			class_override = None
			# We look for the 'class' attribute, if any
			for item in self._override:
				if item[0] == "class": class_override = item
				keys.append(item[0])
			# We now add all the attributes not overridden
			for key, value in attributes:
				if key not in keys:
					self._override.append([key,value])
				# We merge the class attribute if present
				elif key == "class":
					if class_override[1]:
						class_override[1] += " " + value
					else:
						class_override[1] = value
			attributes = self._override
		# We expand BEM class attributes
		# NOTE: I'm implementing it so that it can manage multiple prefixes,
		# but I'm not sure if it's going to be actually useful.
		new_attributes = []
		bem_prefixes   = []
		for attr in attributes:
			if attr[0] != "class":
				new_attributes.append(attr)
				continue
			class_attributes = attr[1].split()
			value            = []
			for i,_ in enumerate(class_attributes):
				if _.endswith("-"):
					bem_prefixes.append(_[0:-1])
				elif _.startswith("-"):
					_ = self._getBEMName(_)
					value.append(_)
				else:
					value.append(_)
			attr[1] = " ".join(value)
		# We only want 0 or 1 BEM prefixes
		assert len(bem_prefixes) <= 1
		element = Element(name,attributes=attributes,isInline=isInline)
		# We clear the override
		if self._override:
			self._override = None
		self._node().append(element)
		self._pushStack(element, bem_prefixes[0] if bem_prefixes else None)

	def overrideAttributesForNextElement( self, attributes ):
		self._override = []
		self._override.extend(attributes)

	def onElementEnd( self ):
		self._popStack()

	def onDeclarationStart( self, name, attributes=None ):
		element = Declaration(name)
		self._pushStack(element)

	def onDeclarationEnd( self ):
		self._popStack()

	def _getBEMName( self, name ):
		"""Returns the BEM fully qualified name of the given class. This
		assumes that `name` starts with a dash."""
		res = [name]
		i   = len(self._bemStack) - 1
		# The BEM stack is either a BEM prefix, or None. We start at the
		# deepest level and walk back up. Whenever an element in the stack
		# does not start with an `-`, we break the loop.
		# NOTE: this algorithm only works if you have 0 or 1 BEM prefix
		# per node.
		while i >= 0:
			prefix = self._bemStack[i]
			if prefix:
				res.insert(0, prefix)
				# We break the loop if the prefix DOES NOT start with -
				if prefix[0] != "-":
					break
			i -= 1
		# We simply join the resulting array into a string
		return "".join(res)

	def _pushStack( self, node, bemPrefixes=None ):
		node.setMode(self.mode())
		self._nodeStack.append(node)
		# NOTE: Might just as well store the bem prefixes in the node?
		self._bemStack.append(bemPrefixes)

	def _popStack(self):
		self._nodeStack.pop()
		self._bemStack.pop()

	def _node( self ):
		if not self._nodeStack: return self._document
		return self._nodeStack[-1]

	def pushMode( self, name ):
		self._modes.append(name)

	def popMode( self ):
		self._modes.pop()

	def mode( self ):
		modes = [x for x in self._modes if x]
		if modes:
			return modes[-1]
		else:
			return None

# -----------------------------------------------------------------------------
#
# COMMAND-LINE INTERFACE
#
# -----------------------------------------------------------------------------

def parse( text, path=None, format="html" ):
	parser = Parser()
	if format == "js": parser._formatter = JSFormatter()
	return parser.parseString(text, path=path)

def run( arguments, input=None ):
	p = argparse.ArgumentParser(description="Processes PAML files")
	p.add_argument("file",  type=str, help="File to process", nargs="?")
	p.add_argument("-t", "--to",  dest="format", help="Converts the PAML to HTML or JavaScript", choices=("html", "js"))
	p.add_argument("-d", "--def", dest="var",   type=str, action="append")
	args      = p.parse_args(arguments)
	env       = dict(_.split("=",1) for _ in args.var or ())
	formatter = JSFormatter() if args.format == "js" else HTMLFormatter()
	parser    = Parser(formatter=formatter, defaults=env)
	return parser.parseFile(args.file or "--")

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	sys.stdout.write( run(sys.argv[1:]).encode("utf-8") )

# EOF - vim: tw=80 ts=4 sw=4 noet


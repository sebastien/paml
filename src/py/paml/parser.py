import os
import sys
import string

from paml.utils import ensureUnicode, readSourceLines
from paml.grammar import (
	RE_ATTRIBUTE, RE_COMMENT, RE_EMPTY, RE_DECLARATION, RE_ELEMENT, RE_INLINE,
	RE_MACRO, RE_INCLUDE, RE_USE, RE_DOCTYPE, RE_PI, RE_LEADING_TAB,
	RE_LEADING_SPC, RE_XML_COMMENT,
	T_ELEMENT, T_DECLARATION, T_EMBED, TAB_WIDTH,
)
from paml.formatter import HTMLFormatter
from paml.writer import PamlWriter
from paml.macros import PamlMacro

# Backward-compat aliases used internally by the class
ensure_unicode = ensureUnicode
read_source_lines = readSourceLines

# -----------------------------------------------------------------------------
#
# PARSER CLASS
#
# -----------------------------------------------------------------------------


class PamlParser:
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

	def __init__(self, formatter=None, defaults=None):
		self._tabsOnly = False
		self._spacesOnly = False
		self._tabsWidth = TAB_WIDTH
		self._elementStack = []
		self._writer = PamlWriter()
		self._formatter = formatter or HTMLFormatter()
		self._paths = []
		env_library = os.environ.get("PAML_LIBRARY", "")
		paml_library_paths = [p for p in env_library.split(":") if p]
		self._searchPaths = ["."] + paml_library_paths + ["src/py/paml", "lib/paml"]
		self._defaults = defaults or {}

	def setDefaults(self, defaults):
		self._defaults = defaults
		return self

	def path(self):
		"""Returns the current path of the file being parsed, if any"""
		if not self._paths or self._paths[-1] == "--":
			return "."
		else:
			return self._paths[-1]

	def indent(self):
		if self._elementStack:
			return self._elementStack[-1][0]
		else:
			return 0

	def parseFile(self, path):
		"""Parses the file with the given  path, and return the corresponding
		HTML document."""
		if path == "--":
			lines = [ensure_unicode(_) for _ in sys.stdin.readlines()]
		else:
			lines = read_source_lines(path)
		self._paths.append(path)
		self._writer.onDocumentStart()
		for line in lines:
			self._parseLine(ensure_unicode(line))
		result = self._formatter.format(self._writer.onDocumentEnd())
		self._paths.pop()
		return result

	def parseString(self, text, path=None):
		"""Parses the given string and returns an HTML document."""
		if path:
			self._paths.append(path)
		try:
			text = ensure_unicode(text)
		except UnicodeEncodeError:
			# FIXME: What should we do?
			pass
		self._writer.onDocumentStart()
		for line in text.split("\n"):
			self._parseLine(line + "\n")
		res = self._formatter.format(self._writer.onDocumentEnd())
		if path:
			self._paths.pop()
		return res

	def _isInEmbed(self, indent=None):
		"""Tells if the current element is an embed element (like
		CSS,PHP,etc)"""
		if not self._elementStack:
			return False
		elif indent is None:
			return self._elementStack[-1][1] == T_EMBED
		else:
			return (
				self._elementStack[-1][1] == T_EMBED
				and self._elementStack[-1][0] < indent
			)

	def _parseLine(self, line):
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
		is_empty = RE_EMPTY.match(line)
		if is_empty:
			# FIXME: When you have an empty line followed by content which is
			# text with same or greeater indent, the empty line  should be taken
			# into account. Same for elements with greater indent.
			if self._isInEmbed():
				line_with_indent = "\n"
				if len(line) > (self.indent() + 4) / 4:
					i = int(((self.indent() or 0) + 4) / 4)
					line_with_indent = original_line[i:]
				self._writer.onTextAdd(line_with_indent)
				return
			else:
				return
		is_comment = RE_COMMENT.match(line)
		if is_comment:
			comment = is_comment.group(1).strip()
			if not self._isInEmbed(indent) and (
				comment.startswith("START:") or comment.startswith("END:")
			):
				return self._writer.onComment(comment)
			else:
				return
		is_pi = RE_PI.match(line)
		if is_pi:
			self._writer.onProcessingInstruction(is_pi.group(2))
			return
		is_doctype = RE_DOCTYPE.match(line)
		if is_doctype:
			self._writer.onDocType(is_doctype.group(2))
			return
		is_xml_comment = RE_XML_COMMENT.match(line)
		if is_xml_comment:
			self._writer.onXMLComment(is_xml_comment.group(2))
			return
		# Is it an include element (%include ...)
		if self._parseInclude(RE_INCLUDE.match(original_line), indent):
			return
		# Is it an include element (%use ...)
		if self._parseUse(RE_USE.match(original_line), indent):
			return
		# Is it a macro element (%macro ...)
		if self._parseMacro(RE_MACRO.match(original_line), indent):
			return
		self._gotoParentElement(indent)
		# Is the parent an embedded element ?
		if self._isInEmbed(indent):
			line_with_indent = original_line[int((self.indent() + 4) / 4) :]
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
			at_index = is_element.group().rfind("@")
			paren_index = is_element.group().rfind(")")
			is_embed = at_index > paren_index
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
				language = is_element.group()[at_index + 1 :]
				if language[-1] == ":":
					language = language[:-1]
				self._pushStack(indent, T_EMBED, language)
			else:
				self._pushStack(indent, T_ELEMENT)
			group = is_element.group()[1:]
			rest = line[len(is_element.group()) :]
			name, attributes, embed, hints = self._parsePAMLElement(group)
			# Element is a single line if it ends with ':'
			self._writer.onElementStart(name, attributes, isInline=False, hints=hints)
			if group[-1] == ":" and rest:
				self._parseContentLine(rest)
		else:
			# Otherwise it's data
			self._parseContentLine(line)

	def _tokenize(self, text, escape="\"'"):
		res = []
		o = 0
		end = len(text)
		while o < end:
			escape_index = end + 1
			escape_index_end = -1
			escape_char = None
			# We look for the closest matching escape character
			for char in escape:
				# We find the occurence of the escape char
				i = text.find(char, o)
				# If it is there and closer to the current offset than
				# the previous escape character
				if i != -1 and i < escape_index:
					# We look for the end
					j = text.find(char, i + 1)
					# If there is an end, we assign it as the current escape
					if j != -1:
						escape_index = i
						escape_index_end = j
						escape_char = char
			# If we did not find an escape char
			if escape_char is None:
				res.append(text[o:])
				o = end
			else:
				if o < escape_index:
					res.append(text[o:escape_index])
				res.append(text[escape_index : escape_index_end + 1])
				o = escape_index_end + 1
		return res

	def _parseIncludeSubstitutions(self, text):
		"""A simple parser that extract (key,value) from a string like
		`KEY=VALUE,KEY="VALUE\"VALUE",KEY='VALUE\'VALUE'`"""
		offset = 0
		result = [_ for _ in self._defaults.items()]
		while offset < len(text):
			equal = text.find("=", offset)
			if equal < 0:
				raise ValueError("Include subsitution without value: {0}".format(text))
			name = text[offset:equal]
			offset = equal + 1
			if offset == len(text):
				value = ""
			elif text[offset] in "'\"":
				# We test for quotes and escape it
				quote = text[offset]
				end_quote = text.find(quote, offset + 1)
				while end_quote >= 0 and text[end_quote - 1] == "\\":
					end_quote = text.find(quote, end_quote + 1)
				value = text[offset + 1 : end_quote].replace("\\" + quote, quote)
				offset = end_quote + 1
				if offset < len(text) and text[offset] == ",":
					offset += 1
			else:
				# Or we look for a comma
				comma = text.find(",", offset)
				if comma < 0:
					value = text[offset:]
					offset = len(text)
				else:
					value = text[offset:comma]
					offset = comma + 1
			result.append((name.strip(), value))
		return result

	def _parseInclude(self, match, indent, parseLine=None):
		"""An include rule is expressed as follows
		%include PATH {NAME=VAL,...} +.class...(name=val,name,val)
		"""
		if not match:
			return False
		# FIXME: This could be written better
		path = match.group(2).strip()
		subs = None
		plus = path.find("+")
		include_path = path[:plus].rstrip() if plus >= 0 else path
		override_suffix = path[plus:] if plus >= 0 else ""
		# If there is a paren, we extract the replacement
		lparen = include_path.rfind("{")
		if lparen >= 0:
			subs = {}
			rparen = include_path.rfind("}")
			if rparen > lparen:
				for name, value in self._parseIncludeSubstitutions(
					include_path[lparen + 1 : rparen]
				):
					value = value.strip()
					if value and value[0] in ["'", '"']:
						value = value[1:-1]
					subs[name] = value
				include_path = include_path[:lparen] + include_path[rparen + 1 :]
		# FIXME: The + will be swallowed if after paren
		path = include_path + override_suffix
		if plus >= 0:
			element = "div" + path[plus + 1 :].strip()
			path = path[:plus].strip()
			_, attributes, _, _ = self._parsePAMLElement(element)
			if self._writer:
				self._writer.overrideAttributesForNextElement(attributes)
		if not path:
			error_line = "ERROR: Empty include path"
			if parseLine:
				parseLine(error_line)
			else:
				return self._writer.onTextAdd(error_line)
			return True
		if path[0] in ['"', "'"]:
			path = path[1:-1]
		else:
			path = path.strip()
		# Now we load the file
		original_path = path
		path = self._findIncludedPath(path)
		if not path or not os.path.exists(path):
			error_line = "ERROR: File not found <code>%s</code>" % (original_path)
			if parseLine:
				parseLine(error_line)
			else:
				return self._writer.onTextAdd(error_line)
		else:
			if not path.endswith(".paml"):
				# If it's not a PAML file we include it as-is, skipping
				# any processing instruction
				with open(path, "rt") as f:
					text = f.read()
					if text.startswith("<?xml"):
						text = text[text.find("\n") :]
					self._writer.onRawTextAdd(text)
			else:
				self._paths.append(path)
				p = int(indent / 4) * "\t"
				os.path.relpath(path, os.path.dirname(path))
				# (parseLine or self._parseLine)("#START:INCLUDE[{0}]".format(relpath))
				for line in read_source_lines(path):
					if RE_PI.match(line):
						continue
					# We do the substituion
					if subs:
						line = string.Template(line).safe_substitute(**subs)
					(parseLine or self._parseLine)(p + line)
				# (parseLine or self._parseLine)("#END:INCLUDE[{0}]".format(relpath))
				self._paths.pop()
		return True

	def _findIncludedPath(self, path):
		"""Looks for the given `path` and returns the first matching one."""
		for paths in (
			[os.path.dirname(_) for _ in self._paths],
			[os.path.dirname(self.path())],
			self._searchPaths,
		):
			for parent in paths:
				local_dir = os.path.abspath(os.path.normpath(parent))
				local_path = os.path.normpath(os.path.join(local_dir, path))
				for p in (local_path, local_path + ".paml", path, path + ".paml"):
					if os.path.exists(p):
						return p

	def _parseUse(self, match, indent, parseLine=None):
		"""An use rule is expressed as follows
		%use id
		"""
		if not match:
			return False
		attr = ""
		# We find the parent element
		self._gotoParentElement(indent)
		if match.group(3):
			attr += ' class="{0}"'.format(match.group(3)[1:].strip())
		if match.group(4):
			attr += ' width="{0}px"'.format(match.group(5).strip())
			attr += ' height="{0}px"'.format(match.group(6).strip())
		self._writer.onRawTextAdd(
			'<svg{1} data-target="{0}" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
			'<use xlink:href="#{0}" /></svg>'.format(match.group(2), attr)
		)
		return True

	def _parseMacro(self, match, indent, parseLine=None):
		if not match:
			return False
		name = match.group(2)[1:]
		params = match.group(4)
		macro = PamlMacro.Get(name)
		if not macro:
			raise ValueError(
				"paml.engine: Undefined macro: {0} in {1}".format(name, match.group())
			)
		macro(self, params, indent)
		return True

	def _pushStack(self, indent, type, mode=None):
		self._elementStack.append((indent, type))
		self._writer.pushMode(mode)

	def _popStack(self):
		self._elementStack.pop()
		self._writer.popMode()

	def _parseContentLine(self, line):
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
			text = line[offset : element.start()]
			if text:
				self._writer.onTextAdd(text)
			# And we append the element itself
			group = element.group()[1:]
			name, attributes, embed, hints = self._parsePAMLElement(group)
			self._writer.onElementStart(name, attributes, isInline=True, hints=hints)
			text = line[element.end() : closing]
			if text:
				self._writer.onTextAdd(text)
			self._writer.onElementEnd()
			offset = closing + 1
		# We add the remaining text
		if offset < len(line):
			text = line[offset:]
			# We remove the trainling EOL at the end of the line. This might not
			# be the best way to do it, though.
			if text and text[-1] == "\n":
				text = text[:-1] + " "
			if text:
				self._writer.onTextAdd(text)

	def _parsePAMLElement(self, element):
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
		if element[-1] == ":":
			element = element[:-1]
		# We look for the attributes list
		parens_start = element.find("(")
		pipe_start = element.rfind("|")
		at_start = element.rfind("@")
		if parens_start != -1:
			parens_end = element.rfind(")")
			if at_start < parens_end:
				at_start = -1
			attributes_list = element[parens_start + 1 : parens_end]
			if attributes_list and attributes_list[-1] == ")":
				attributes_list = attributes_list[:-1]
			attributes = self._parsePAMLAttributes(attributes_list)
			element = element[:parens_start]
			element[parens_end:]
		else:
			attributes = []

		# Useful functions to manage attributes
		def has_attribute(name, attributes):
			for a in attributes:
				if a[0] == name:
					return a
			return None

		def set_attribute(name, value, attribtues):
			for a in attributes:
				if a[0] == name:
					a[1] = value
					return
			attributes.append([name, value])

		def append_attribute(name, value, attributes, prepend=False):
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
			embed = element[at_start + 1 :]
			element = element[:at_start]
		else:
			embed = None
		# We take care of hints
		hints = []
		if pipe_start != -1:
			hints = (original[pipe_start + 1 :].rsplit("@", 1)[0]).split("+")
			element = element[:pipe_start]
		# We look for the classes
		classes = element.split(".")
		if len(classes) > 1:
			element = classes[0]
			classes = classes[1:]
			classes = " ".join(classes)
			append_attribute("class", classes, attributes, prepend=True)
		else:
			element = classes[0]
		eid = element.split("#")
		# FIXME: If attributes or ids are already defined, we should look for it
		# and do something appropriate
		if len(eid) > 1:
			if len(eid) != 2:
				raise ValueError("More than one id given: %s" % (original))
			if has_attribute("id", attributes):
				raise Exception("Id already given as element attribute")
			attributes.insert(0, ["id", eid[1]])
			element = eid[0]
		else:
			element = eid[0]
		# handle '::' syntax for namespaces
		element = element.replace("::", ":")
		return (element, attributes, embed, hints)

	def _parsePAMLAttributes(self, attributes):
		"""Parses a string representing PAML attributes and returns a list of
		couples '[name, value]' representing the attributes."""
		result = []
		original = attributes
		while attributes:
			match = RE_ATTRIBUTE.match(attributes)
			if not match:
				raise ValueError("Given attributes are malformed: %s" % (attributes))
			name = match.group(1)
			value = match.group(4)
			# handles '::' syntax for namespaces
			name = name.replace("::", ":")
			if value and value[0] == value[-1] and value[0] in ("'", '"'):
				value = value[1:-1]
			result.append([name, value])
			attributes = attributes[match.end() :]
			if attributes:
				if attributes[0] != ",":
					raise ValueError(
						"Attributes must be comma-separated: %s" % (attributes)
					)
				attributes = attributes[1:]
				if not attributes:
					raise ValueError(
						"Trailing comma with no remaining attributes: %s" % (original)
					)
		return result

	def _gotoParentElement(self, currentIndent):
		"""Finds the parent element that has an identation lower than the given
		'currentIndent'."""
		while self._elementStack and self._elementStack[-1][0] >= currentIndent:
			self._popStack()
			self._writer.onElementEnd()

	def _getLineIndent(self, line):
		"""Returns the line indentation as a number. It takes into account the
		fact that tabs may be requried or not, and also takes into account the
		'tabsWith' property."""
		line = line or ""
		tabs = RE_LEADING_TAB.match(line)
		spaces = RE_LEADING_SPC.match(line)
		if self._tabsOnly and spaces and len(spaces.group()) > 0:
			raise Exception("Tabs are expected, your lines are indented with spaces")
		if self._spacesOnly and tabs and len(tabs.group()) > 0:
			raise Exception("Spaces are expected, your lines are indented with tabs")
		if tabs and len(tabs.group()) > 0:
			return len(tabs.group()) * self._tabsWidth, line[len(tabs.group()) :]
		elif spaces and len(spaces.group()) > 0:
			return len(spaces.group()), line[len(spaces.group()) :]
		else:
			return 0, line

import os
import re
import time
import json
import shutil
import logging
import tempfile
import xml.dom

from paml.utils import xmlEscape, xslEscape, _runEmbeddedCommand, ensureUnicode
from paml.grammar import (
	FORMAT_INLINE, FORMAT_SINGLE_LINE, FORMAT_PRESERVE,
	FORMAT_XSL, FORMAT_NORMALIZE, FORMAT_STRIP, FORMAT_COMPACT, FORMAT_WRAP,
	FORMAT_OPTIONS,
	HTML_DEFAULTS, HTML_EXCEPTIONS,
	RE_INLINE, RE_SPACE,
)
from paml.model import PamlText, PamlElement, PamlComment, PamlRawText, XMLComment, DocType, ProcessingInstruction

RE_SPACES = re.compile(r"\s")

# Backward-compat alias used by engine.py
_runEmbeddedCommand = _runEmbeddedCommand

# -----------------------------------------------------------------------------
#
# FORMATTING FUNCTION (BORROWED FROM LAMBDAFACTORY MODELWRITER MODULE)
#
# -----------------------------------------------------------------------------


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

	def __init__(self, strict=False):
		"""Creates a new formatter."""
		self.indent = 0
		# NOTE: I removed the indentation. It does not serve any purpose
		# as the HTML is going to be minified anyway.
		self.indentValue = ""
		self.textWidth = 80
		# FIXME
		self.defaults = {}
		self.defaults = HTML_DEFAULTS
		self.flags = [[]]
		self.useProcessCache = True
		self.strict = strict
		self._init()

	def _isWebComponent(self, name):
		"""Returns True if the element name contains a hyphen, indicating
		it is a web component/custom element that requires explicit
		open/close tags rather than self-closing syntax."""
		return "-" in name

	def _requiresExplicitCloseInHTML(self, name):
		"""Returns True for tags that should never be emitted as self-closing
		when using HTML mode."""
		if not isinstance(name, str):
			return False
		lname = name.lower()
		return lname in (
			"a",
			"canvas",
			"div",
			"h1",
			"h2",
			"h3",
			"h4",
			"h5",
			"h6",
			"iframe",
			"li",
			"ol",
			"script",
			"slot",
			"span",
			"template",
			"ul",
		)

	def _init(self):
		pass

	def setDefaults(self, element, formatOptions=()):
		"""Sets the formatting defaults for the given element name."""
		if not isinstance(element, str):
			raise TypeError("element must be a string")
		if not isinstance(formatOptions, (list, tuple)):
			raise TypeError("formatOptions must be a list or tuple")
		for f in formatOptions:
			if f not in FORMAT_OPTIONS:
				raise ValueError("Unknown formatting option: %s" % (f))
		self.defaults[element] = list(formatOptions)

	def getDefaults(self, elementName):
		"""Gets the formatting defaults for the given element name."""
		return self.defaults.get(elementName) or ()

	def pushFlags(self, *flags):
		"""Pushes the given flags (as varargs) on the flags queue."""
		self.flags.append([])
		for _ in flags:
			if isinstance(_, list) or isinstance(_, tuple):
				for f in _:
					self.setFlag(f)
			else:
				self.setFlag(_)

	def setFlag(self, flag):
		"""Sets the given flag."""
		if flag == FORMAT_SINGLE_LINE:
			self.setFlags(FORMAT_NORMALIZE)
		if flag not in self.flags[-1]:
			self.flags[-1].append(flag)

	def setFlags(self, *flags):
		"""Set the given flags, given as varargs."""
		for _ in flags:
			self.setFlag(_)

	def popFlags(self):
		"""Pops the given flags from the flags queue."""
		self.flags.pop()

	def hasFlag(self, flag):
		"""Tells if the given flag is currently defined."""
		if flag == FORMAT_SINGLE_LINE:
			single_line = self.findFlag(flag)
			preserve = self.findFlag(FORMAT_PRESERVE)
			if single_line > preserve:
				return True
			else:
				return False
		else:
			return self.findFlag(flag) != -1

	def getFlags(self):
		"""Returns the list of defined flags, by order of definition (last flags
		are more recent."""
		res = []
		for flags in self.flags:
			res.extend(flags)
		return res

	def findFlag(self, flag):
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

	def format(self, document, indent=0):
		"""Formats the given document, starting at the given indentation (0 by
		default)."""
		self.startWriting()
		self.indent = indent
		self._formatContent(document)
		return self.endWriting()

	def _formatContent(self, element):
		"""Formats the content of the given element. This uses the formatting
		operations defined in this class."""
		text = []
		# NOTE: In this process we aggregate text elements, which are typically
		# one text element per line. This allows proper formatting
		for e in element.content:
			if isinstance(e, PamlElement):
				if text:
					self.writeText("".join(text))
					text = []
				self._formatElement(e)
			elif isinstance(e, PamlText):
				text.append(e.content)
			elif isinstance(e, PamlRawText):
				self._result.append(e.content)
			elif isinstance(e, XMLComment):
				self._result.append("<!-- {0} -->\n".format(xmlEscape(e.content)))
			elif isinstance(e, ProcessingInstruction):
				self._result.append("<?{0}?>\n".format(e.content))
			elif isinstance(e, DocType):
				self._result.append("<!{0}>\n".format(e.content))
			else:
				raise Exception("Unsupported content type: %s" % (e))
		if text:
			# text = "".join(map(lambda _:_.encode("utf-8"), text))
			text = ("\n" if self.hasFlag(FORMAT_PRESERVE) else "").join(text)
			if not element.isInline:
				while text and text[-1] in "\n\t ":
					text = text[:-1]
			self.writeText(text)

	def _inlineCanSpanOneLine(self, element):
		"""Tells wether the given element (when considered as an inline) can
		span one single line. It can if only it has inlines that can span
		one line and text without EOLs as content."""
		if isinstance(element, PamlText):
			return element.content.find("\n") == -1
		elif isinstance(element, PamlComment):
			return False
		else:
			for c in element.content:
				if not self._inlineCanSpanOneLine(c):
					return False
			return True

	# FIXME: This should probably be moved to the parser
	# FIXME: Yes, it should DEFINITELY be moved above
	def _formatElement(self, element):
		"""Formats the given element and its content, by using the formatting
		operations defined in this class."""
		if isinstance(element, PamlComment):
			return self._formatComment(element)
		attributes = element._attributesAsHTML(strict=self.strict)
		exceptions = HTML_EXCEPTIONS.get(element.name)
		content = element.content
		mode = element.mode.split("+")[0] if element.mode else None
		# FIXME: Flags are not properly supported
		if exceptions:
			not_empty = exceptions.get("NOT_EMPTY")
			if not_empty is not None and not content:
				# Textareas intentionally keep one literal space when empty. Render
				# it directly so normal block whitespace formatting cannot discard it.
				if element.name == "textarea":
					self.writeTag("<%s%s> </%s>" % (element.name, attributes, element.name))
					return
				element.content.append(PamlText(not_empty))
		# Does this element has any content that needs to be pre-processed?
		if mode and mode.startswith("sugar"):
			lines = element.contentAsLines()
			version = mode[len("sugar") :]
			source = "".join(lines)
			t = time.time()
			command = shutil.which(mode) or shutil.which("sugar" + version)
			res = _runEmbeddedCommand([command] if command else [], source, ".sjs")
			logging.info(
				"Parsed Sugar: {0} lines in {1:0.2f}s".format(
					len(lines), time.time() - t
				)
			)
			element.content = [PamlText(res)]
		elif mode in ("coffeescript", "coffee"):
			lines = element.contentAsLines()
			source = "".join(lines)
			t = time.time()
			res = _runEmbeddedCommand(["coffee", "-cp"], source, ".coffee")
			logging.info(
				"Parsed CoffeeScript: {0} lines in {1:0.2f}s".format(
					len(lines), time.time() - t
				)
			)
			element.content = [PamlText(res)]
		elif mode in ("typescript", "ts"):
			lines = element.contentAsLines()
			source = "".join(lines)
			t = time.time()
			res = _runEmbeddedCommand(["tsc"], source, ".ts")
			logging.info(
				"Parsed TypeScript: {0} lines in {1:0.2f}s".format(
					len(lines), time.time() - t
				)
			)
			element.content = [PamlText(res)]
		elif mode in ("clevercss", "ccss"):
			lines = element.contentAsLines()
			source = "".join(lines)
			t = time.time()
			try:
				import clevercss

				res = clevercss.convert(source)
			except ImportError:
				res = source
			logging.info(
				"Parsed CleverCSS: {0} lines in {1:0.2f}s".format(
					len(lines), time.time() - t
				)
			)
			element.content = [PamlText(res)]
		elif mode in ("pythoniccss", "pcss"):
			lines = element.contentAsLines()
			source = "".join(lines)
			t = time.time()
			res = _runEmbeddedCommand(["pcss"], source, ".pcss")
			logging.info(
				"Parsed PCSS: {0} lines in {1:0.2f}s".format(
					len(lines), time.time() - t
				)
			)
			element.content = [PamlText(res)]
		elif element.mode and element.mode.endswith("nobrackets"):
			lines = element.contentAsLines()
			source = "".join(lines)
			t = time.time()
			prefix = element.mode[0 : 0 - (len("nobrackets"))]
			suffix = ".nb"
			if prefix:
				suffix = "." + prefix + suffix
			res = source
			try:
				import nobrackets

				processor = nobrackets.Processor()
				processor.registerExtensions(nobrackets)
				with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
					f.write(source)
					temp_path = f.name
				try:
					res = processor.processPath(temp_path)
				finally:
					if os.path.exists(temp_path):
						os.unlink(temp_path)
			except ImportError:
				pass
			logging.info(
				"Parsed Nobrackets: {0} lines in {1:0.2f}s".format(
					len(lines), time.time() - t
				)
			)
			element.content = [PamlText(res)]
		elif mode == "texto":
			lines = element.contentAsLines()
			import texto

			source = "".join(lines)
			res = ensureUnicode(texto.toHTML(source))
			element.content = [PamlText(res)]
			self.setFlag(FORMAT_PRESERVE)
		elif mode == "hjson":
			lines = element.contentAsLines()
			import hjson

			source = "".join(lines)
			res = ensureUnicode(hjson.dumpsJSON(hjson.loads(source)))
			element.content = [PamlText(res)]
		elif mode == "raw":
			text = "".join(element.contentAsLines())
			while text and text[-1] in "\n\t":
				text = text[:-1]
			element.content = [PamlText(text)]
			element.setFormat(FORMAT_PRESERVE)
			element.setFormat(FORMAT_COMPACT)
		# NOTE: This is a post-processor
		if element.mode and (
			element.mode.endswith("+escape") or "+escape+" in element.mode
		):
			for text in element.content:
				if isinstance(text, PamlText):
					text.content = text.content.replace("<", "&lt;").replace(
						">", "&gt;"
					)
		# If the element has any content, then we apply it
		if element.content:
			flags = element.getFormatFlags() + list(self.getDefaults(element.name))
			self.pushFlags(*flags)
			if element.isPI:
				if attributes:
					raise ValueError("Processing instruction cannot have attributes")
				start = "<?%s " % (element.name)
				end = " ?>"
			else:
				start = "<%s%s>" % (element.name, attributes)
				end = "</%s>" % (element.name)
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
				self.writeTag(start)
				if not self.hasFlag(FORMAT_COMPACT) and not self.hasFlag(
					FORMAT_PRESERVE
				):
					self.startIndent()
				self._formatContent(element)
				if not self.hasFlag(FORMAT_COMPACT) and not self.hasFlag(
					FORMAT_PRESERVE
				):
					self.endIndent()
				self.writeTag(end)
			self.popFlags()
		# Otherwise it doesn't have any content
		else:
			if not self.strict and exceptions and exceptions.get("NO_CLOSING"):
				text = "<%s%s>" % (element.name, attributes)
			elif (
				not self.strict
				and self._requiresExplicitCloseInHTML(element.name)
			):
				text = "<%s%s></%s>" % (element.name, attributes, element.name)
			elif self._isWebComponent(element.name):
				text = "<%s%s></%s>" % (element.name, attributes, element.name)
			else:
				text = "<%s%s />" % (element.name, attributes)
			# And if it's an inline, we don't add a newline
			self.writeTag(text)

	def _formatComment(self, comment):
		self.writeTag("<!-- {0} -->\n".format(comment.content))

	# -------------------------------------------------------------------------
	# TEXT OUTPUT COMMANDS
	# -------------------------------------------------------------------------

	def _isNewLine(self):
		"""Tells wether the current line is a new line."""
		if not self._result or not self._result[-1]:
			return False
		return not self._result or self._result[-1][-1] == "\n"

	def _ensureNewLine(self):
		"""Ensures that there is a new line."""
		if not self._isNewLine():
			if not self._result:
				self._result.append("")
			else:
				self._result[-1] = self._result[-1] + "\n"

	def startWriting(self):
		self._result = []

	def startIndent(self):
		self.indent += 1

	def endIndent(self):
		if self.indent <= 0:
			raise ValueError("Cannot decrease indent below 0")
		self.indent -= 1

	def writeTag(self, tagText):
		if self._isNewLine():
			self._result.append(self.indentAsSpaces() + tagText)
		else:
			if self._result:
				self._result[-1] = self._result[-1] + tagText
			else:
				self._result.append(tagText)

	def writeText(self, text):
		result = self._result
		text = self.formatText(text)
		if self.hasFlag(FORMAT_XSL):
			text = xslEscape(text)
		if self.hasFlag(FORMAT_PRESERVE):
			result.append(text)
		else:
			if self._isNewLine():
				if self.hasFlag(FORMAT_WRAP):
					# print "WRAP ",repr(self.wrapText(text))
					result.append(self.wrapText(text))
				else:
					# print "INDENT ",repr(self.indentAsSpaces() + text)
					result.append(self.indentAsSpaces() + text)
			elif result:
				len(result[-1])
				if self.hasFlag(FORMAT_WRAP):
					# print "APPEND WRAP ",repr(self.wrapText(text, len(result[-1])))
					result[-1] = result[-1] + self.wrapText(text, len(result[-1]))
				else:
					# print "APPEND ",repr(text)
					result[-1] = result[-1] + text
			else:
				if self.hasFlag(FORMAT_WRAP):
					result.append(self.wrapText(text, len(result[-1])))
				else:
					result.append(text)

	def formatText(self, text):
		"""Returns the given text properly formatted according to
		this formatted configuration."""
		if not self.hasFlag(FORMAT_PRESERVE):
			text = xmlEscape(text)
			if self.hasFlag(FORMAT_NORMALIZE):
				text = self.normalizeText(text)
			if self.hasFlag(FORMAT_STRIP):
				text = self.stripText(text)
			if not self.hasFlag(FORMAT_SINGLE_LINE):
				compact = self.hasFlag(FORMAT_COMPACT)
				text = self.indentString(text, start=not compact, end=not compact)
		return text

	def endWriting(self):
		res = "".join(self._result)
		del self._result
		return res

	def _iterateOnWords(self, text):
		"""Splits the given text into words (separated by ' ', '\t' or '\n') and
		returns an iterator on these words.

		This function is used by 'wrapText'."""
		offset = 0
		space = None
		inline = None
		while offset < len(text):
			space = RE_SPACE.search(text, offset)
			inline = RE_INLINE.search(text, offset)
			if space:
				if inline and inline.start() < space.start():
					end = text.find(">", inline.end()) + 1
					yield text[offset:end]
					offset = end
				else:
					yield text[offset : space.start()]
					offset = space.end()
			else:
				yield text[offset:]
				offset = len(text)
		if space and space.end() == len(text) or inline and inline.end() == len(text):
			yield ""

	def wrapText(self, text, offset=0, textWidth=80, indent=None):
		"""Wraps the given text at the given 'textWidth', starting at the given
		'offset' with the given optional 'ident'."""
		words = []
		for word in self._iterateOnWords(text):
			words.append(word)
		return " ".join(words)

	# -------------------------------------------------------------------------
	# TEXT MANIPULATION OPERATIONS
	# -------------------------------------------------------------------------

	def indentString(self, text, indent=None, start=True, end=False):
		"""Indents the given 'text' with the given 'value' (which will be
		converted to either spaces or tabs, depending on the formatter
		parameters.

		If 'start' is True, then the start line will be indented as well,
		otherwise it won't. When 'end' is True, a newline is inserted at
		the end of the resulting text, otherwise not."""
		if indent is None:
			indent = self.indent
		first_line = True
		result = []
		prefix = self.indentAsSpaces(indent)
		lines = text.split("\n")
		line_i = 0
		for line in lines:
			if not line and line_i == len(lines) - 1:
				continue
			if first_line and not start:
				result.append(line)
			else:
				result.append(prefix + line)
			first_line = False
			line_i += 1
		result = "\n".join(result)
		if end:
			result += "\n"
		return result

	def indentAsSpaces(self, indent=None, increment=0):
		"""Converts the 'indent' value to a string filled with spaces or tabs
		depending on the formatter parameters."""
		if indent is None:
			indent = self.indent
		return self.indentValue * (indent + increment)

	def normalizeText(self, text):
		"""Replaces the tabs and eols by spaces, ignoring the value of tabs."""
		return RE_SPACES.sub(" ", text)

	def stripText(self, text):
		"""Strips leading and trailing spaces or eols from this text"""
		while text and text[0] in "\t\n ":
			text = text[1:]
		while text and text[-1] in "\t\n ":
			text = text[:-1]
		return text

	def reformatText(self, text):
		"""Reformats a text so that it fits a particular text width."""
		return text


# -----------------------------------------------------------------------------
#
# JAVASCRIPT HTML FORMATTER
#
# -----------------------------------------------------------------------------


class JSFormatter(HTMLFormatter):
	"""Formats the given PAML document to a JavaScript source code
	using the 'html.js' markup file."""

	def format(self, document, indent=0):
		elements = [v for v in document.content if isinstance(v, PamlElement)]
		if len(elements) != 1 or len(document.content) != 1:
			raise ValueError("JSHTMLFormatter can only be used with one element")
		return self._formatContent(elements[0])

	def _formatContent(self, value):
		"""Formats the content of the given element. This uses the formatting
		operations defined in this class."""
		# FIXME: Should escape entities
		if isinstance(value, PamlText):
			return json.dumps(value.content)
		elif isinstance(value, PamlElement):
			element = value
			if element.isPI:
				return ""
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
			raise TypeError("Unrecognized value type: " + str(value))


# -----------------------------------------------------------------------------
#
# XML FORMATTER
#
# -----------------------------------------------------------------------------


class XMLFormatter(HTMLFormatter):
	def __init__(self, document=None, root=None):
		self.dom = xml.dom.getDOMImplementation()
		self.doc = document or self.dom.createDocument(None, None, None)
		self.node = None
		self.root = root

	def format(self, document, indent=0):
		elements = [v for v in document.content if isinstance(v, PamlElement)]
		for _ in elements:
			node = self._formatContent(_)
			self.node = node
			if self.root:
				self.root.appendChild(node)
			else:
				self.doc.appendChild(node)
		return self.doc.toxml()

	def _formatContent(self, value):
		"""Formats the content of the given element. This uses the formatting
		operations defined in this class."""
		# FIXME: Should escape entities
		if isinstance(value, PamlText):
			return self.doc.createTextNode(value.content)
		elif isinstance(value, PamlRawText):
			import xml.dom.minidom

			document = None
			try:
				document = xml.dom.minidom.parseString(value.content)
			except Exception:
				pass
			if not document:
				return self.doc.createTextNode(value.content)
			else:
				# NOTE: We might want to return more
				return document.childNodes[0]
		elif isinstance(value, PamlElement):
			element = value
			if element.isPI:
				return None
			node = self.doc.createElementNS(None, element.name)
			if element.attributes:
				for name, value in element.attributes:
					node.setAttributeNS(None, name, value)
			for child in element.content:
				node.appendChild(self._formatContent(child))
			return node
		else:
			raise TypeError("Unrecognized value type: " + str(value))


# -----------------------------------------------------------------------------
#
# FORMATTER FACTORY
#
# -----------------------------------------------------------------------------


def formatter(format):
	if format == "js":
		return JSFormatter()
	if format == "jshtml":
		return JSFormatter()
	elif format == "xml":
		return XMLFormatter()
	elif format == "xhtml":
		return HTMLFormatter(strict=True)
	elif format == "html":
		return HTMLFormatter(strict=False)
	else:
		return None

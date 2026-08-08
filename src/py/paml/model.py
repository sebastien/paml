# Module: model
# Node types used to represent parsed Paml documents before rendering.

from paml.utils import xmlEscape

# -----------------------------------------------------------------------------
#
# OBJECT MODEL
#
# -----------------------------------------------------------------------------


class PamlText:
	"""Reprensents a text fragment within the HTML document."""

	def __init__(self, content):
		self.content = content

	def contentAsLines(self):
		return [self.content]


class PamlRawText:
	"""Reprensents a text fragment within the HTML document that should not be
	escaped."""

	def __init__(self, content):
		self.content = content

	def contentAsLines(self):
		return [self.content]


class PamlElement:
	"""Represents an element within the HTML document."""

	def __init__(self, name, attributes=None, isInline=False, isPI=False, hints=None):
		self.name = name
		self.attributes = attributes or []
		self.content = []
		self.isInline = isInline
		self.mode = None
		self.isPI = isPI
		self.isDocType = False
		self.isComment = False
		self.formatOptions = hints or []
		if name[0] == "?":
			self.isPI = True
			self.name = name[1:]

	@property
	def isDoctype(self):
		"""Compatibility alias for `isDocType`."""
		return self.isDocType

	@isDoctype.setter
	def isDoctype(self, value):
		self.isDocType = value

	def setFormat(self, option):
		if option not in self.formatOptions:
			self.formatOptions.append(option)
		return self

	def getFormatFlags(self):
		return self.formatOptions or []

	def setMode(self, mode):
		self.mode = mode

	def append(self, n):
		self.content.append(n)

	def isTextOnly(self):
		if len(self.content) == 0:
			return True
		elif (
			len(self.content) == 1
			and isinstance(self.content[0], PamlText)
			and self.content[0].content.find("\n") == -1
		):
			return True
		else:
			return False

	def contentAsLines(self):
		res = []
		for e in self.content:
			if type(e) in (str, str):
				res.append(e)
			else:
				res.extend(e.contentAsLines())
		return res

	def _attributesAsHTML(self, strict=True):
		"""Returns the attributes as HTML"""
		r = []

		def escape(v):
			v = xmlEscape(v)
			if v.find('"') == -1:
				v = '"%s"' % (v)
			elif v.find("'") == -1:
				v = "'%s'" % (v)
			else:
				v = '"%s"' % (v.replace('"', '\\"'))
			return v

		for name, value in self.attributes:
			if value is None:
				r.append('%s=""' % (name) if strict else str(name))
			else:
				r.append("%s=%s" % (name, escape(value)))
		r = " ".join(r)
		if r:
			r = " " + r
		return r


class PamlComment(object):
	def __init__(self, line):
		self.isComment = True
		self.content = line

	def contentAsLines(self):
		return [self.content]


class XMLComment(object):
	def __init__(self, line):
		self.isComment = True
		self.content = line

	def contentAsLines(self):
		return [self.content]


class DocType(object):
	def __init__(self, line):
		self.isDocType = True
		self.content = line

	def contentAsLines(self):
		return [self.content]


class ProcessingInstruction(object):
	def __init__(self, line):
		self.isPI = True
		self.content = line

	def contentAsLines(self):
		return [self.content]


class PamlDeclaration(PamlElement):
	def __init__(self, name, attributes=None):
		PamlElement.__init__(self, name, attributes)


# EOF

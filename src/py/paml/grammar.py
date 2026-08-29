# Module: grammar
# Regular expressions, parser tokens, and formatting defaults for Paml syntax.

import re

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

SYMBOL_NAME = r"\??([\w\d_-]+::)*[\w\d_-]+"
SYMBOL_ID_CLS = r"(\#%s|\.%s)+" % (SYMBOL_NAME, SYMBOL_NAME)
SYMBOL_ATTR_NAME = r"\??([\w\d_-]+::?)?[\w\d_-]+"
SYMBOL_ATTR = r"(%s)(=('[^']+'|\"[^\"]+\"|([^),]+)))?" % (SYMBOL_ATTR_NAME)
SYMBOL_ATTRS = r"\(%s(\s*,\s*%s)*\)" % (SYMBOL_ATTR, SYMBOL_ATTR)
SYMBOL_CONTENT = r"@\w[\w\d\-_\+]*"
SYMBOL_HINTS = r"\|[a-z](\+[a-z])*"
SYMBOL_ELEMENT = r"<(%s(%s)?|%s)(%s)?(%s)?(%s)?\:?" % (
	SYMBOL_NAME,
	SYMBOL_ID_CLS,
	SYMBOL_ID_CLS,
	SYMBOL_ATTRS,
	SYMBOL_HINTS,
	SYMBOL_CONTENT,
)
RE_ATTRIBUTE = re.compile(SYMBOL_ATTR)
RE_COMMENT = re.compile("^#(.*)$")
RE_EMPTY = re.compile(r"^\s*$")
RE_DECLARATION = re.compile(r"^@(%s):?" % (SYMBOL_NAME))
RE_ELEMENT = re.compile(r"^%s" % (SYMBOL_ELEMENT))
RE_INLINE = re.compile(r"%s" % (SYMBOL_ELEMENT))
RE_MACRO = re.compile(r"^(\s)*(@\w+(:\w+)?)\s*\(([^\)]+)\)\s*$")
RE_INCLUDE = re.compile(r"^(\s)*%include (.+)$")
RE_USE = re.compile(r"^(\s)*%use\s+#([A-Za-z0-9_\-]+)(\.\w+)?(\s+(\d+)x(\d+))?$")
RE_DOCTYPE = re.compile(r"^(\s)*\<\!([^>]+)\>\s*$")
RE_PI = re.compile(r"^(\s)*\<\?(.+)\?\>\s*$")
RE_LEADING_TAB = re.compile(r"\t*")
RE_LEADING_SPC = re.compile(r"[ ]*")
RE_SPACE = re.compile(r"[\s\n]")
RE_XML_COMMENT = re.compile(r"^(\s)*\<\!\-\-(([^\-]|\-[^\-]|\-\-[^\>])+)\-\-\>\s*$")
# TODO: Support numerical entities
# RE_ENTITY      = re.compile("&[A-Za-z];")

T_ELEMENT = "EL"
T_DECLARATION = "DC"
T_EMBED = "EM"

TAB_WIDTH = 4

# -----------------------------------------------------------------------------
#
# FORMATTING
#
# -----------------------------------------------------------------------------

# FIXME: This does not work. What we should have is
# - compact: no leading or trailing whitepsace
FORMAT_INLINE = "i"
FORMAT_INLINE_BLOCK = "ib"
FORMAT_SINGLE_LINE = "sl"
FORMAT_PRESERVE = "p"
FORMAT_XSL = "x"
FORMAT_NORMALIZE = "n"
FORMAT_STRIP = "s"
FORMAT_COMPACT = "c"
FORMAT_WRAP = "w"
FORMAT_OPTIONS = (
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
	"script": "p".split(),
	"link": "i".split(),
	"title": "sl n".split(),
	"h1": "sl n".split(),
	"h2": "sl n".split(),
	"h3": "sl n".split(),
	"h4": "sl n".split(),
	"p": "n c w".split(),
	"code": "p".split(),
	"pre": "p".split(),
	"div": "ib".split(),
}

HTML_EXCEPTIONS = {
	"links": dict(NO_CLOSING=True),
	"br": dict(NO_CLOSING=True),
	"img": dict(NO_CLOSING=True),
	# FIXME: No idea why there was a no closing, but this is wrong
	# "path" :dict(NO_CLOSING=True),
	"textarea": {"NOT_EMPTY": " "},
	"td": {"NOT_EMPTY": "&nbsp;"},
	"th": {"NOT_EMPTY": "&nbsp;"},
}

# EOF

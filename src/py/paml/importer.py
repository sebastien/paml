#!/usr/bin/env python3
# Module: importer
# Converts HTML and XML documents into Paml source.
# -----------------------------------------------------------------------------
# Project           :   PAML
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   09-Jun-2010
# Last mod.         :   30-Jul-2010
# -----------------------------------------------------------------------------

import sys
from html.parser import HTMLParser
import xml.dom.minidom as minidom


HTML_VOID_ELEMENTS = {
	"area",
	"base",
	"br",
	"col",
	"embed",
	"hr",
	"img",
	"input",
	"link",
	"meta",
	"param",
	"source",
	"track",
	"wbr",
}

HTML_IMPLIED_END_TAGS = {
	"dd": {"dd", "dt"},
	"dt": {"dd", "dt"},
	"li": {"li"},
	"option": {"option", "optgroup"},
	"p": {
		"address",
		"article",
		"aside",
		"blockquote",
		"div",
		"dl",
		"fieldset",
		"footer",
		"form",
		"h1",
		"h2",
		"h3",
		"h4",
		"h5",
		"h6",
		"header",
		"hgroup",
		"hr",
		"main",
		"menu",
		"nav",
		"ol",
		"p",
		"pre",
		"section",
		"table",
		"ul",
	},
	"rt": {"rt", "rp"},
	"rp": {"rt", "rp"},
	"thead": {"tbody", "tfoot"},
	"tbody": {"tbody", "tfoot"},
	"tr": {"tr"},
	"th": {"th", "td"},
	"td": {"th", "td"},
}


class _HtmlNode:
	def __init__(self, tag=None, attributes=()):
		self.tag = tag
		self.attributes = list(attributes)
		self.children = []


class _HtmlParser(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.roots = []
		self.stack = []

	def _append(self, node):
		if self.stack:
			self.stack[-1].children.append(node)
		else:
			self.roots.append(node)

	def _close_implied(self, tag):
		if self.stack and tag in HTML_IMPLIED_END_TAGS.get(self.stack[-1].tag, ()):
			self.stack.pop()

	def handle_starttag(self, tag, attrs):
		tag = tag.lower()
		self._close_implied(tag)
		node = _HtmlNode(tag, [(name, value or "") for name, value in attrs])
		self._append(node)
		if tag not in HTML_VOID_ELEMENTS:
			self.stack.append(node)

	def handle_startendtag(self, tag, attrs):
		self._close_implied(tag.lower())
		self._append(_HtmlNode(tag.lower(), [(name, value or "") for name, value in attrs]))

	def handle_endtag(self, tag):
		tag = tag.lower()
		for index in range(len(self.stack) - 1, -1, -1):
			if self.stack[index].tag == tag:
				del self.stack[index:]
				return

	def handle_data(self, data):
		self._append(data)

	def handle_comment(self, data):
		node = _HtmlNode()
		node.comment = data
		self._append(node)


class XML2Paml:
	def __init__(self):
		self.indent = 0
		self.result = ""

	def extractLines(self, text):
		lines = [_.strip() for _ in text.split("\n")]
		return [_ for _ in lines if len(_.strip()) > 0]

	def convert(self, node, bodyOnly=False):
		if isinstance(node, (list, tuple)):
			for n in node:
				self.convert(n, bodyOnly)
		elif isinstance(node, str):
			for line in self.extractLines(node):
				self.output(line)
		elif hasattr(node, "nodeType"):
			self._convertDom(node, bodyOnly)
		else:
			self._convertHtml(node, bodyOnly)
		return self.result

	def _convertDom(self, node, bodyOnly=False):
		t = node.nodeType
		if t == node.DOCUMENT_NODE:
			if bodyOnly:
				html_node = [
					n
					for n in node.childNodes
					if n.nodeType == node.ELEMENT_NODE and n.nodeName.lower() == "html"
				]
				body_nodes = (
					[
						n
						for n in html_node[0].childNodes
						if n.nodeType == node.ELEMENT_NODE and n.nodeName.lower() == "body"
					]
					if html_node
					else []
				)
				if body_nodes:
					for n in body_nodes[0].childNodes:
						self.convert(n)
					return self.result
			for n in node.childNodes:
				self.convert(n)
		elif t == node.COMMENT_NODE:
			for line in self.extractLines(node.nodeValue):
				self.output("# " + line)
		elif t == node.TEXT_NODE:
			for line in self.extractLines(node.nodeValue):
				self.output(line)
		elif t == node.ELEMENT_NODE:
			self._outputElement(node.nodeName, list(node.attributes.items()), node.childNodes)
		return self.result

	def _convertHtml(self, node, bodyOnly=False):
		if isinstance(node, (list, tuple)):
			if bodyOnly:
				for child in node:
					if getattr(child, "tag", "") == "html":
						self._convertHtml(child, True)
						return self.result
			for child in node:
				self._convertHtml(child)
			return self.result
		if getattr(node, "comment", None) is not None:
			for line in self.extractLines(node.comment):
				self.output("# " + line)
			return self.result
		if isinstance(node, str):
			self.convert(node)
			return self.result
		if getattr(node, "tag", None):
			if bodyOnly and node.tag == "html":
				for child in node.children:
					if getattr(child, "tag", "") == "body":
						for body_child in child.children:
							self._convertHtml(body_child)
						return self.result
			self._outputElement(node.tag, node.attributes, [])
			self.indent += 1
			for child in node.children:
				self._convertHtml(child)
			self.indent -= 1
		return self.result

	def _outputElement(self, name, attributes, children):
		classes = ""
		ids = ""
		attrs = []
		for n, v in attributes:
			if n == "class":
				classes = "." + ".".join([_.strip() for _ in v.split(" ")])
			elif n == "id":
				ids = "#" + ([_.strip() for _ in v.split(" ")])[0]
			else:
				attrs.append('%s="%s"' % (n, v))
		if attrs:
			attrs = "(%s)" % (",".join(attrs))
		else:
			attrs = ""
		self.output("<%s%s%s%s" % (name, ids, classes, attrs))
		for n in children:
			self.indent += 1
			self.convert(n)
			self.indent -= 1

	def output(self, text):
		self.result += ("\t" * self.indent) + text + "\n"


def parseHtml(doc):
	markup = None
	if hasattr(doc, "read"):
		markup = doc.read()
	if isinstance(doc, str):
		if doc.lstrip().startswith("<"):
			markup = doc
		else:
			with open(doc, "rb") as f:
				markup = f.read()
	if markup is not None:
		if isinstance(markup, bytes):
			markup = markup.decode("utf-8", errors="replace")
		parser = _HtmlParser()
		parser.feed(markup)
		parser.close()
		return parser.roots
	return doc


def parseXml(doc):
	if hasattr(doc, "read"):
		return minidom.parse(doc)
	if isinstance(doc, str):
		return minidom.parseString(doc) if doc.lstrip().startswith("<") else minidom.parse(doc)
	return doc


def run(doc, bodyOnly=False, sourceFormat=None):
	if isinstance(doc, (list, tuple)):
		doc = doc[0] if doc else sys.stdin
	if sourceFormat in ("html", "htm", "xhtml"):
		doc = parseHtml(doc)
		converter = XML2Paml()
		return converter.convert(doc, bodyOnly)
	if sourceFormat == "xml":
		doc = parseXml(doc)
		converter = XML2Paml()
		return converter.convert(doc, bodyOnly)
	if hasattr(doc, "read"):
		doc = parseXml(doc)
	elif isinstance(doc, str):
		if doc.lstrip().startswith("<"):
			doc = parseHtml(doc)
		else:
			doc = parseXml(doc)
	converter = XML2Paml()
	return converter.convert(doc, bodyOnly)


def parseFile(path):
	ext = path.lower()
	if ext.endswith((".html", ".htm", ".xhtml")):
		return run(path, sourceFormat="html")
	if ext.endswith(".xml"):
		return run(path, sourceFormat="xml")
	return run(path)


if __name__ == "__main__":
	sys.stdout.write(parseFile(sys.argv[1]))

# EOF

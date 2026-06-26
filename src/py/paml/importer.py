#!/usr/bin/env python3
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
import re
import xml.dom.minidom as minidom

from lxml import etree
from lxml import html as lxml_html


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
			self._convertLxml(node, bodyOnly)
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

	def _convertLxml(self, node, bodyOnly=False):
		if hasattr(node, "getroot"):
			node = node.getroot()
		if bodyOnly and getattr(node, "tag", "") == "html":
			body = node.find("body")
			if body is not None:
				node = body
		if isinstance(node, etree._Comment):
			for line in self.extractLines(node.text or ""):
				self.output("# " + line)
			return self.result
		if isinstance(node, etree._ProcessingInstruction):
			return self.result
		if isinstance(node, etree._Element):
			self._outputElement(node.tag, list(node.attrib.items()), [])
			self.indent += 1
			if node.text:
				self.convert(node.text)
			for child in node.iterchildren():
				self.convert(child)
				if child.tail:
					self.convert(child.tail)
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


def _parse_html(doc):
	full_html = re.compile(br"<\s*(html|body)\b", re.I)
	markup = None
	if hasattr(doc, "read"):
		markup = doc.read()
	if isinstance(doc, str):
		if doc.lstrip().startswith("<"):
			markup = doc.encode("utf-8")
		else:
			with open(doc, "rb") as f:
				markup = f.read()
	if markup is not None:
		if full_html.search(markup):
			if re.search(br"<\s*html\b", markup, re.I):
				return lxml_html.fromstring(markup)
			return etree.fromstring(markup, etree.XMLParser(recover=True))
		return lxml_html.fragments_fromstring(markup)
	return doc


def _parse_xml(doc):
	if hasattr(doc, "read"):
		return minidom.parse(doc)
	if isinstance(doc, str):
		return minidom.parseString(doc) if doc.lstrip().startswith("<") else minidom.parse(doc)
	return doc


def run(doc, bodyOnly=False, sourceFormat=None):
	if isinstance(doc, (list, tuple)):
		doc = doc[0] if doc else sys.stdin
	if sourceFormat in ("html", "htm", "xhtml"):
		doc = _parse_html(doc)
		converter = XML2Paml()
		return converter.convert(doc, bodyOnly)
	if sourceFormat == "xml":
		doc = _parse_xml(doc)
		converter = XML2Paml()
		return converter.convert(doc, bodyOnly)
	if hasattr(doc, "read"):
		doc = _parse_xml(doc)
	elif isinstance(doc, str):
		if doc.lstrip().startswith("<"):
			doc = _parse_html(doc)
		else:
			doc = _parse_xml(doc)
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

# EOF - vim: tw=80 ts=4 sw=4 noet

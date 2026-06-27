import unittest

from paml.parser import PamlParser


class EmptyElementFormattingTests(unittest.TestCase):
	def parse(self, source):
		return PamlParser().parseString(source)

	def test_empty_span_placeholder_has_no_whitespace_content(self):
		self.assertEqual(
			self.parse(
				"<div\n"
				"\t<span.placeholder(slot=cond,data-placeholder=Conditional)\n"
				"\t<span.placeholder(slot=then,data-placeholder=Then)\n"
			),
			'<div><span slot="cond" data-placeholder="Conditional" class="placeholder"></span>'
			'<span slot="then" data-placeholder="Then" class="placeholder"></span></div>',
		)

	def test_empty_non_void_elements_use_explicit_closing_tags(self):
		for name in ("a", "canvas", "div", "iframe", "li", "ol", "script", "span", "template", "ul"):
			with self.subTest(name=name):
				self.assertEqual(self.parse("<%s" % name), "<%s></%s>" % (name, name))

	def test_empty_textarea_and_table_cells_keep_required_content(self):
		self.assertEqual(self.parse("<textarea"), "<textarea> </textarea>")
		self.assertEqual(self.parse("<td"), "<td>&nbsp;\n</td>")
		self.assertEqual(self.parse("<th"), "<th>&nbsp;\n</th>")


if __name__ == "__main__":
	unittest.main()

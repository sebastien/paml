import os
import subprocess
import sys
import unittest

from paml.importer import run


class ImporterTests(unittest.TestCase):
	def test_html_conversion_handles_elements_text_comments_and_void_tags(self):
		result = run(
			"<div id='main' class='one two'>Hello<br>world<!-- note --></div>",
			sourceFormat="html",
		)

		self.assertEqual(
			result,
			"<div#main.one.two\n\tHello\n\t<br\n\tworld\n\t# note\n",
		)

	def test_html_conversion_applies_common_implied_end_tags(self):
		result = run("<ul><li>One<li>Two</ul>", sourceFormat="html")

		self.assertEqual(result, "<ul\n\t<li\n\t\tOne\n\t<li\n\t\tTwo\n")

	def test_html_conversion_selects_body_for_complete_documents(self):
		result = run(
			"<!doctype html><html><head><title>Page</title></head>"
			"<body><p>Hello</p></body></html>",
			sourceFormat="html",
		)

		self.assertIn("<html\n", result)
		self.assertIn("\t<head\n", result)
		self.assertIn("\t<body\n", result)

	def test_xml_conversion_remains_available(self):
		result = run("<?xml version='1.0'?><root><child>text</child></root>", sourceFormat="xml")

		self.assertEqual(result, "<root\n\t<child\n\t\ttext\n")

	def test_package_imports_without_site_packages(self):
		environment = os.environ.copy()
		environment["PYTHONPATH"] = os.path.abspath("src/py")
		completed = subprocess.run(
			[
				sys.executable,
				"-S",
				"-c",
				"import paml; assert paml.parse('<p:Hello') == '<p>Hello</p>'",
			],
			env=environment,
			capture_output=True,
			text=True,
		)

		self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
	unittest.main()

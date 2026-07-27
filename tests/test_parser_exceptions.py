import os
import tempfile
import unittest

from paml.parser import PamlParser


class ParserExceptionLocationTests(unittest.TestCase):
	def test_unclosed_inline_tag_reports_the_tag_column(self):
		with self.assertRaisesRegex(
			Exception,
			r"Preferences\.html:3:11: Unclosed inline tag:"
		):
			PamlParser().parseString(
				"<html\n\t<body\n\t\tCreated <span(out=createdAt|memberDate)\n",
				path="Preferences.html",
			)

	def test_parser_errors_keep_their_exception_type(self):
		with self.assertRaisesRegex(ValueError, r"template\.paml:1:1:"):
			PamlParser().parseString("<div#main#duplicate", path="template.paml")

	def test_include_errors_report_the_included_file(self):
		with tempfile.TemporaryDirectory() as directory:
			main_path = os.path.join(directory, "main.paml")
			child_path = os.path.join(directory, "child.paml")
			with open(main_path, "w") as main:
				main.write("%include child\n")
			with open(child_path, "w") as child:
				child.write("<div\n\tCreated <span\n")

			with self.assertRaisesRegex(
				Exception,
				r"child\.paml:2:10: Unclosed inline tag:"
			):
				PamlParser().parseFile(main_path)


if __name__ == "__main__":
	unittest.main()

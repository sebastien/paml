import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from paml.cli import run


class CliTests(unittest.TestCase):
	def test_output_option_writes_file_and_suppresses_stdout_result(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, "output.html")
			with patch("sys.stdin", io.StringIO("<p:Hello")):
				result = run(["-o", path])

			self.assertEqual(result, "")
			with open(path) as file:
				self.assertEqual(file.read(), "<p>Hello</p>")

	def test_output_option_renders_input_file(self):
		with tempfile.TemporaryDirectory() as directory:
			source = os.path.join(directory, "input.paml")
			output = os.path.join(directory, "output.html")
			with open(source, "w") as file:
				file.write("<p:Hello")

			run(["-o", output, source])

			with open(output) as file:
				self.assertEqual(file.read(), "<p>Hello</p>")

	def test_executable_does_not_emit_engine_deprecation_warning(self):
		completed = subprocess.run(
			[sys.executable, os.path.join(os.path.dirname(__file__), "..", "bin", "paml"), "--help"],
			capture_output=True,
			text=True,
		)

		self.assertEqual(completed.returncode, 0)
		self.assertNotIn("DeprecationWarning", completed.stderr)


if __name__ == "__main__":
	unittest.main()

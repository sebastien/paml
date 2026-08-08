#!/usr/bin/env python3
# Module: cli
# Command-line entry point and convenience API for processing Paml documents.
import os
import sys
import argparse

import paml.importer
from paml.parser import PamlParser
from paml.formatter import createFormatter


def parse(text, path=None, format="html"):
	"""Returns rendered output for Paml source `text` in `format`."""
	fmt = createFormatter(format)
	parser = PamlParser(formatter=fmt)
	return parser.parseString(text, path=path)


def run(arguments, input=None):
	"""Runs the Paml command-line interface for `arguments`."""
	p = argparse.ArgumentParser(description="Processes PAML files")
	p.add_argument("file", type=str, help="File to process", nargs="?")
	p.add_argument(
		"-f",
		"--from",
		dest="source_format",
		help="Reads HTML/XML and converts it to Paml",
		choices=("html", "htm", "xhtml", "xml"),
	)
	p.add_argument(
		"-t",
		"--to",
		dest="format",
		help="Converts the PAML to HTML or JavaScript",
		choices=("html", "js", "xml", "xhtml"),
	)
	p.add_argument("-d", "--def", dest="var", type=str, action="append")
	args = p.parse_args(arguments)
	if args.file:
		_, ext = os.path.splitext(args.file.lower())
		if not args.source_format and ext in (".html", ".htm", ".xhtml", ".xml"):
			args.source_format = "html" if ext != ".xml" else "xml"
	if args.source_format:
		return paml.importer.run(args.file or sys.stdin, sourceFormat=args.source_format)
	env = dict(_.split("=", 1) for _ in args.var or ())
	parser = PamlParser(formatter=createFormatter(args.format), defaults=env)
	return parser.parseFile(args.file or "--")


if __name__ == "__main__":
	sys.stdout.write(run(sys.argv[1:]))

# EOF

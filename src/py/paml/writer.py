# Module: writer
# Event-driven document-tree builder used by the Paml parser.

from paml.model import PamlElement, PamlText, PamlRawText, PamlComment, XMLComment, DocType, ProcessingInstruction, PamlDeclaration

# -----------------------------------------------------------------------------
#
# WRITER CLASS
#
# -----------------------------------------------------------------------------


class PamlWriter:
	"""The PamlWriter class implements a simple SAX-like interface to create the
	resulting HTML/XML document. This is not API-compatible with SAX because
	PAML has slightly different information than what SAX offers, which requires
	specific methods."""

	def __init__(self):
		self.onDocumentStart()

	def onDocumentStart(self):
		self._modes = []
		self._content = []
		self._nodeStack = []
		self._document = PamlElement("document")
		self._override = None
		self._bemStack = []
		self._hintStack = []

	def onDocumentEnd(self):
		return self._document

	def onComment(self, line):
		line = line.replace("\n", " ").strip()
		comment = PamlComment(line)
		self._node().append(comment)

	def onXMLComment(self, text):
		node = XMLComment(text)
		self._node().append(node)
		return node

	def onProcessingInstruction(self, text):
		node = ProcessingInstruction(text)
		self._node().append(node)
		return node

	def onDocType(self, text):
		node = DocType(text)
		self._node().append(node)
		return node

	def onTextAdd(self, text):
		"""Adds the given text fragment to the current element."""
		node = PamlText(text)
		self._node().append(node)
		return node

	def onRawTextAdd(self, text):
		"""Adds the given text fragment to the current element."""
		node = PamlRawText(text)
		self._node().append(node)
		return node

	def onElementStart(self, name, attributes=None, isInline=False, hints=None):
		# We extend the override if present
		if self._override:
			# FIXME: This would be much more elegant with an ordered key-value
			# pair set
			keys = []
			class_override = None
			# We look for the 'class' attribute, if any
			for item in self._override:
				if item[0] == "class":
					class_override = item
				keys.append(item[0])
			# We now add all the attributes not overridden
			for key, value in attributes:
				if key not in keys:
					self._override.append([key, value])
				# We merge the class attribute if present
				elif key == "class":
					if class_override[1]:
						class_override[1] += " " + value
					else:
						class_override[1] = value
			attributes = self._override
		# We expand BEM class attributes
		# NOTE: I'm implementing it so that it can manage multiple prefixes,
		# but I'm not sure if it's going to be actually useful.
		new_attributes = []
		bem_prefixes = []
		for attr in attributes:
			if attr[0] != "class":
				new_attributes.append(attr)
				continue
			class_attributes = attr[1].split()
			value = []
			for i, _ in enumerate(class_attributes):
				if _.startswith("-") and _.endswith("-"):
					_ = self._getBEMName(_[:-1])
					value.append(_)
					bem_prefixes.append(_)
				elif _.endswith("-"):
					prefix = _[0:-1]
					value.append(prefix)
					bem_prefixes.append(prefix)
				elif _.startswith("-"):
					_ = self._getBEMName(_)
					value.append(_)
				else:
					value.append(_)
			attr[1] = " ".join(value)
		# We only want 0 or 1 BEM prefixes
		if len(bem_prefixes) > 1:
			raise ValueError("Only one BEM prefix is supported per node")
		element = PamlElement(name, attributes=attributes, isInline=isInline, hints=hints)
		# We clear the override
		if self._override:
			self._override = None
		self._node().append(element)
		self._pushStack(element, bem_prefixes[0] if bem_prefixes else None, hints)

	def overrideAttributesForNextElement(self, attributes):
		self._override = []
		self._override.extend(attributes)

	def onElementEnd(self):
		self._popStack()

	def onDeclarationStart(self, name, attributes=None):
		element = PamlDeclaration(name)
		self._pushStack(element)

	def onDeclarationEnd(self):
		self._popStack()

	def _getBEMName(self, name):
		"""Returns the BEM fully qualified name of the given class. This
		assumes that `name` starts with a dash."""
		res = [name]
		i = len(self._bemStack) - 1
		# The BEM stack is either a BEM prefix, or None. We start at the
		# deepest level and walk back up. Whenever an element in the stack
		# does not start with an `-`, we break the loop.
		# NOTE: this algorithm only works if you have 0 or 1 BEM prefix
		# per node.
		while i >= 0:
			prefix = self._bemStack[i]
			if prefix:
				res.insert(0, prefix)
				# We break the loop if the prefix DOES NOT start with -
				if prefix[0] != "-":
					break
			i -= 1
		# We simply join the resulting array into a string
		return "".join(res)

	def _pushStack(self, node, bemPrefixes=None, hints=None):
		node.setMode(self.mode())
		self._nodeStack.append(node)
		# NOTE: Might just as well store the bem prefixes in the node?
		self._bemStack.append(bemPrefixes)
		self._hintStack.append(hints)

	def _popStack(self):
		self._nodeStack.pop()
		self._bemStack.pop()
		self._hintStack.pop()

	def _node(self):
		if not self._nodeStack:
			return self._document
		return self._nodeStack[-1]

	def pushMode(self, name):
		self._modes.append(name)

	def popMode(self):
		self._modes.pop()

	def mode(self):
		modes = [x for x in self._modes if x]
		if modes:
			return modes[-1]
		else:
			return None


# EOF

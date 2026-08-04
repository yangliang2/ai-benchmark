"""An in-memory store of named JSON-like documents (dicts, lists, scalars)."""


class DocStore:
    """Named documents, stored as given."""

    def __init__(self):
        self._documents = {}

    def put(self, name, document):
        """Store document under name, replacing any previous one."""
        self._documents[name] = document

    def get(self, name):
        """The document stored under name; KeyError if there is none."""
        return self._documents[name]

    def names(self):
        """The stored documents' names, sorted."""
        return sorted(self._documents)

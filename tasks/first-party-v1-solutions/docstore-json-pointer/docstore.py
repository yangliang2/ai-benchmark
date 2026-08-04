"""An in-memory store of named JSON-like documents (dicts, lists, scalars),
addressable with JSON Pointers (RFC 6901)."""


def resolve(document, pointer):
    """The value pointer designates inside document.

    The empty pointer is the whole document; otherwise "/"-separated tokens
    step into dicts by key and lists by index, with "~1" for "/" and "~0"
    for "~". Malformed pointers raise ValueError, missing keys and indices
    KeyError.
    """
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"pointer {pointer!r} does not start with '/'")
    value = document
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[_index(token, value)]
        elif isinstance(value, dict):
            if token not in value:
                raise KeyError(token)
            value = value[token]
        else:
            raise KeyError(token)
    return value


def _index(token, values):
    """The list index a reference token stands for."""
    if not token.isdigit() or (len(token) > 1 and token[0] == "0"):
        raise ValueError(f"{token!r} is not a list index")
    index = int(token)
    if index >= len(values):
        raise KeyError(token)
    return index


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

    def fetch(self, name, pointer):
        """Resolve pointer inside the document stored under name."""
        return resolve(self.get(name), pointer)

    def names(self):
        """The stored documents' names, sorted."""
        return sorted(self._documents)

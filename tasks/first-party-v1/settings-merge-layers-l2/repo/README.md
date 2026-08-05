# settings

Standard-library helpers for application settings. Settings are plain nested
mappings: a mapping is a section, anything else is a value.

- `flatten(settings)` — the settings as dotted paths to values
- `value_at(settings, path, default=None)` — the value at one dotted path
- `set_value(settings, path, value)` — a copy with one path set

Nothing here modifies the settings it is given.

Run the tests with `pytest`.

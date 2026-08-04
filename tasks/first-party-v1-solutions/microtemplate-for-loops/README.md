# microtemplate

A standard-library template language.

- `template.render(text, context)` — substitute "{{ name }}" placeholders,
  optionally piped through a filter: "{{ name|upper }}"
- `filters.FILTERS` — the available filters

Run the tests with `pytest`.

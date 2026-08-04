# microtemplate

A tiny template language, standard library only.

- `template.render(text, context)` — substitute "{{ name }}" placeholders,
  optionally piped through a filter: "{{ name|upper }}"
- `filters.FILTERS` — the available filters

Run the tests with `pytest`.

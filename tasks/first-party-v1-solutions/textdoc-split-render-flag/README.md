# textdoc

Standard-library document rendering.

- `textdoc.render_html(doc)` / `textdoc.render_text(doc)` — a doc
  (`{"title": ..., "items": [...]}`) as HTML or plain text
- `summary.listing_line(doc)` — one-line listing entry
- `export.export_page(doc)` — a full HTML page
- `preview.clipped(doc, width)` — plain text clipped to a width

Run the tests with `pytest`.

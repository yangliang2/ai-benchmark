# album

Standard-library helpers for photo albums and the keywords filed against
them. A keyword is kept as it was written; two keywords that canonicalise the
same way are the same keyword.

- `new_album(title)` — an empty album
- `add_keyword(album, keyword)` — file a keyword, as written
- `keywords(album)` — the keywords as written, in filing order
- `canonical(keyword)` — the form two keywords share when they are the same
- `keyword_set(album)` — which keywords the album carries, canonically
- `has_keyword(album, keyword)` — whether it carries one, however written
- `describe(album)` — a one-line summary

Questions about *which* keywords an album carries are answered canonically;
`keywords` is the one question about how they were typed.

Run the tests with `pytest`.

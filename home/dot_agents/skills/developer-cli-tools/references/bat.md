# bat: file previews

For a person, `bat path/to/file.py` provides highlighted output with file and
line information. For an agent, explicitly disable the pager and presentation:

```sh
bat --no-config --paging=never --color=never --style=plain \
  --line-range=10:40 -- path/to/file.py
```

`--no-config` avoids an inherited bat configuration changing the preview.
Quote paths and put `--` before filenames that could begin with a dash. A plain
preview has no line-number gutter; use `rg -n` to locate a line, or choose
`--style=numbers` when a human needs a numbered preview.

Use a bounded range when investigating one match. Prefer `sed -n '10,40p'`
when bat is unavailable or only raw text is needed. Use `cat` for the whole
file. Bat output is a preview, not a byte-preserving input for file rewrites.

Source: [bat documentation](https://github.com/sharkdp/bat).

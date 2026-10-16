# fd: filename predicates

Use fd when filenames, extensions, or file types are the question. From the
intended repository directory:

```sh
fd --type f --extension py . src tests
fd --type f --glob '*config*' src
fd --type f --extension py --print0 . src
```

The pattern normally matches filenames as a regular expression. `--glob` uses
glob matching, while `--full-path` includes the path in the match. Hidden and
ignored files are excluded by default; add `--hidden` or `--no-ignore` only for
paths where that wider coverage is needed. Check a no-result search's scope
before concluding absence.

Use NUL-delimited output for filename pipelines and verified, quoted paths for
later operations. `--exec`/`--exec-batch` run commands on matches; they are not
just search output and should not introduce edits while discovering files.

If fd is missing, use `rg --files -g '*.py' src tests` or scoped `find`.
These dotfiles declare fd in the standard Mise selection.

Source: [fd documentation](https://github.com/sharkdp/fd).

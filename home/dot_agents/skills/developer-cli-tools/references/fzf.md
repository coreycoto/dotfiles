# fzf: select or filter candidates

Use interactive selection only when a person is available at the terminal:

```sh
rg --files -g '*.py' src | fzf
```

For unattended fuzzy discovery, feed a known list and use filter mode:

```sh
rg --no-config --files -g '*.py' src | FZF_DEFAULT_OPTS= FZF_DEFAULT_OPTS_FILE= \
  fzf --filter='parser' --no-sort
```

Filter mode returns all matches and exits without opening a selection UI.
Clearing the two option variables avoids inherited interactive bindings or
options; supplying stdin avoids implicit candidate generation. Fuzzy matching
is useful for discovery, but cannot establish that a unique exact filename
exists. Verify candidate count and the exact path before a later operation;
do not silently take the first match. Use `rg -F -x` for exact line matching.

For filenames that can contain newlines, preserve record boundaries:

```sh
rg --no-config --files -0 src | FZF_DEFAULT_OPTS= FZF_DEFAULT_OPTS_FILE= \
  fzf --read0 --print0 --filter='parser' --no-sort
```

Treat output as data and pass verified paths as arguments. Zero candidates is
not a tool crash. A plain `fzf`, `zoxide query -i`, or shell completion can wait
for input and is unsuitable for an unattended tool call. Check upstream pipeline
errors separately; an empty candidate list does not prove discovery succeeded.

Source: [fzf documentation](https://github.com/junegunn/fzf).

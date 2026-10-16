# agent-browser

Use browser automation for rendered UI evidence or interaction that requires a
browser. Prefer the available native browser integration and its required skill
when the user selected that surface. Otherwise load the installed agent-browser
workflow skill before execution.

```sh
agent-browser skills get core
agent-browser open https://example.com
agent-browser snapshot -i
```

Use refs from the latest snapshot; take a fresh snapshot after navigation or DOM
changes. Opening a page creates browser state and may make authenticated requests.
Form submission, messages, and purchases require the task's corresponding scope.
Keep cookies, auth profiles, downloads, and screenshots containing private data
out of dotfiles. Mise installs `npm:agent-browser` in an isolated directory through
`dotfiles-tools --apply`. Its package includes the native executable and matching
workflow assets; no shared Bun-global lifecycle trust is required.
Browser installation is separate from package installation;
`agent-browser install` downloads a browser, so do it only when needed.

Source: [official documentation](https://agent-browser.dev).

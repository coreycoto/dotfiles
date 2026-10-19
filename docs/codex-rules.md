# Staged personal command-rule migration

This source prepares a migration; it does not activate rules or remove the old
home export. Chezmoi manages only `.config/dotfiles/codex-rules/`, outside every
active Codex rules layer. No startup task, hook or general dotfiles apply copies
these files into `.codex/rules`. `default.rules`, project trust, hook trust and
the main Codex configuration remain unmanaged.

## Inventory and ownership

The historical home `coreycoto.com.rules` has 92 prefix rules: 73 allowances,
14 prompts and 5 denials. Its reviewed SHA-256 is recorded in `migration.json`.
Those counts describe the historical ownership baseline, not a requirement to
keep every prompt global. Policy revision 2 retains all five denials with their
exact patterns, aliases, decisions and justifications, and narrows the global
proposal to eight prompts. The 73 allowances are not imported. The old file
remains effective until a separately authorized migration and retirement.

| Prepared file | Rules | Ownership |
| --- | --- | --- |
| `personal.rules` | 8 prompts, 4 denials | Browser credentials/uploads/attachment/sensitive options, GitHub authentication and release creation, Git reset/clean/push/tag and uv publication |
| `legacy-project.rules` | 1 denial | Historical Bun migration/sync restriction; preserve pending separate denial review |

## Reviewed prompt scope

These are escalation rules: a matching `prompt` requests approval before an
invocation outside the sandbox. They are not extra conversational confirmations
for every authorized edit. The strictest matching decision wins; a remembered
allowance cannot override a matching prompt or denial. User rules apply across
repositories on that host. Project rules load only through a trusted project
configuration layer; neither location establishes Cloud discovery.

| Historical prompt | Revision 2 treatment |
| --- | --- |
| Browser credentials | Keep global |
| Browser request route/unroute | Keep in the owning project's browser-testing policy |
| Browser upload/install | Keep uploads global; remove the global browser-install prompt |
| Browser connect | Keep global |
| Browser `--cdp`, `--headers`, `--extension`, `--executable-path` | Keep global as a compatibility group pending individual review |
| `fzf` | Remove global prompt; interactive selection belongs to the task workflow |
| `gh auth login` | Keep global |
| `gh release create` | Keep global, including draft creation |
| Git reset/checkout/clean/push/tag/rebase | Keep reset/clean/push/tag global; ordinary checkout/rebase follow the project workflow |
| Playwright install/codegen | Remove global prompt; handle in the authorized development task |
| `sed -i` | Remove global prompt; ordinary edits follow task authorization |
| uv add/remove/publish/build/init | Keep publication global; ordinary dependency and packaging work follows the project workflow |
| Bun clean/database:check | Keep project-specific; script names have repository-defined meaning |
| Voiceprint staging path | Keep in the repository that owns the sensitive data |

Removing a prompt does not add an allow rule. With no matching rule, the host's
remaining sandbox and approval policy determine handling. Unchanged
`default.rules` or project rules may still allow or restrict the command.
Initially adding the replacements alongside the historical file keeps all old
prompts effective. Their removal takes effect only after verified retirement
of that old file and a separate client reload.

The four GitHub denials cover local CLI PR lifecycle changes, issue closure or
reopening, repository deletion, and release editing/deletion. They are reasonable
personal policy candidates and already exist in the home export. Retaining them
does not change their authority or turn every CLI restriction into a universal
connector restriction: honor the original action and transport contract, and
never switch transports to bypass a prohibition. The retained release-create
prompt is not permission to publish without the requested authority.

At coreycoto.com revision `75f3db2de31f2eef90ec065ac6d6e7423bfd4701`, the
project has one file, `.codex/rules/boundaries.rules`, containing 18 rules:
13 prompts and 5 denials, with no allowances. Four denials are general GitHub
restrictions; the fifth covers `bun run database:migrate`. The project also
forbids `gh release create`, while the historical home rule prompts for it.
The stricter project denial must continue to win when that layer is active.
The old home `bun run codex:sync` denial is retained even though that command
was made read-only in project commit `ee2f75a888360cf23d445d850886d1948b34d23b`.
Removing obsolete restrictions is a separate policy decision.

The project already retains request interception, Bun clean/database checks and
voiceprint staging prompts. Those three prompts are deliberately absent from
the revised global proposal. This source does not remove or rewrite the
project's existing prompts or denials. Prefixes do not constrain accounts, URLs, current
directories or connector resources. Existing patterns with machine-specific
browser aliases are retained for compatibility, not advertised as universal
protection against every executable spelling or shell wrapper.

## Read-only preflight

Run from the reviewed source checkout with an existing Python interpreter:

```sh
python3 scripts/codex-rules.py --home "$HOME"
```

The command has no apply mode. It checks reviewed source digests, exact legacy
ownership and destination conflicts, and reports the current `default.rules`
digest without changing it or displaying its commands. Missing or edited legacy
content produces `legacy_unverified`; symlinks, non-file destinations and locally
edited replacement files produce `conflict`. Already matching replacement bytes
are identified. An unknown legacy file must be reviewed, not deleted, even if
its filename matches. A matching digest supports this particular historical
migration; it is not a general claim of ownership over the user's rules folder.

## Later activation and retirement

After source merge, obtain separate authorization for the exact home migration.
Use a scoped staging apply; unrelated shell drift, including Docker Desktop PATH
additions, does not need to be applied. Before changing active rules:

1. Review the exact prepared files and their SHA-256 values. Run the preflight;
   require `ready_for_review`, including the expected legacy digest. Compare the
   actual complete active rule combination with the prepared replacement using
   `codex execpolicy check --rules FILE ... -- COMMAND` and the historical cases.
   Include `default.rules`, other user files and the applicable trusted project
   rules. Keep all real commands as argument data to the checker, never execute
   them. Inspect unrelated rules locally without publishing their contents.
2. Create a private backup of the affected rule files and configuration, modes
   and digests. Existing backup.py covers managed targets, so it is not a backup
   of the unmanaged active rules; retain a dedicated verified backup before this
   migration. Record ownership only for the two replacement files.
3. Quiesce other clients or editors that can write command rules. Recheck source,
   legacy and destination digests immediately before writing. Abort on drift.
   Install the two exact reviewed files into `.codex/rules/` with private modes,
   preserving unrelated files, `default.rules`, trust and configuration. Initially
   retain `coreycoto.com.rules` alongside the replacements.
4. Restart/reload the relevant Codex clients and verify rule discovery separately
   from file installation. File-combination checks are offline policy evidence,
   not proof of the active session's configuration. If available, use native
   decision diagnostics or a harmless local `--help` invocation that matches a
   denied prefix; never verify by trying a real release or business-data change.
5. Only after separately authorized retirement, verified backups, unchanged
   ownership/digests and replacement qualification, remove the exact old export.
   Test the resulting complete combination and reload again. This removes its
   73 allowances, so some formerly allowed commands may require host review.
   All five historical denials and eight reviewed global prompts must remain
   represented. Keep project-specific prompts in the owning repository. Preserve the backup
   and report source, staging, active installation, reload and runtime evidence
   separately. On failure, retain the old file and evidence; do not retry blindly.

A preflight read cannot make later writes race-free. If exclusive access cannot
be established, leave retirement pending. A policy check is neither connector
enforcement nor hook trust, and does not make release draft-state checks atomic.

The native checker suite uses offline synthetic defaults, project prompts and
legacy-overlap fixtures. It checks every denied prefix and reviewed global
prompt in both file orders, verifies routine commands fall back without adding
allowances, preserves remembered allowances, and keeps draft release edits
forbidden. CI installs the pinned Codex 0.162.1 checker so these tests run there
as well as locally. No test executes a release or provider command.

Sources: [Codex rules](https://learn.chatgpt.com/docs/agent-configuration/rules),
[coreycoto.com sync retirement](https://github.com/coreycoto/coreycoto.com/commit/ee2f75a888360cf23d445d850886d1948b34d23b).

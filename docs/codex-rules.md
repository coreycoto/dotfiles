# Staged personal command-rule migration

This source prepares a migration; it does not activate rules or remove the old
home export. Chezmoi manages only `.config/dotfiles/codex-rules/`, outside every
active Codex rules layer. No startup task, hook or general dotfiles apply copies
these files into `.codex/rules`. `default.rules`, project trust, hook trust and
the main Codex configuration remain unmanaged.

## Inventory and ownership

The historical home `coreycoto.com.rules` has 92 prefix rules: 73 allowances,
14 prompts and 5 denials. Its reviewed SHA-256 is recorded in `migration.json`.
Those counts describe the historical ownership baseline. Revision 2 retained all
five denials and eight reviewed global prompts. Policy revision 3 keeps those
eight prompts unchanged and removes three denial groups after a separate review.
The 73 historical allowances are not imported. `migration.json` records both the
revision-3 staged digests and the previous revision-2 file digests; these are
review evidence, not authorization to overwrite active files.

| Prepared file | Rules | Ownership |
| --- | --- | --- |
| `personal.rules` | 8 prompts, 2 denials | Existing personal prompts plus repository deletion and release edit/delete restrictions |
| `legacy-project.rules` | Empty replacement | Clears the owned revision-2 global Bun restriction during a later authorized activation |

The empty replacement keeps the existing managed target explicit. Staging or
applying dotfiles does not clear its active counterpart in `.codex/rules`.

## Reviewed denial scope

| Historical denial | Revision 3 treatment |
| --- | --- |
| `gh pr merge/close/reopen/edit/ready` | Remove global tool routing; use workflow guidance and the requested delivery stage |
| `gh issue close/reopen` | Remove the manual-only restriction without adding an approval prompt; use authorized issue workflow and completion evidence |
| `bun run database:migrate/codex:sync` | Remove globally; script behavior and any migration constraints belong to the owning project |
| `gh repo delete` | Retain exactly |
| `gh release delete/edit` | Retain exactly; release editing remains deferred, including draft edits |

Removing a denial adds no allowance. Existing defaults, trusted project rules,
sandbox behavior and approval policy still apply. Project Management and Product
Development guidance governs authorized work, but instructional guidance is not
executable enforcement. Prefix rules do not enforce equivalent connector paths;
honor each existing action and transport contract without bypassing denials.
Source preparation does not authorize merging, publishing or issue closure.

The release rule still cannot distinguish a draft from a published release.
It blocks draft edits too; do not replace it with a broad allow or use another
transport. A later release-editing decision must separately address exact
repository/release identity, current state, relevant shell and connector paths,
unknown state, hook failures and concurrent publication. A read of `isDraft`
before a write does not guarantee atomic protection.

## Reviewed prompt scope

These are escalation rules: a matching `prompt` requests approval before an
invocation outside the sandbox. They are not extra conversational confirmations
for every authorized edit. The strictest matching decision wins; a remembered
allowance cannot override a matching prompt or denial. User rules apply across
repositories on that host. Project rules load only through a trusted project
configuration layer; neither location establishes Cloud discovery.

| Historical prompt | Retained treatment from revision 2 |
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

Removing a prompt does not add an allow rule either. An old export or active
revision-2 files keep their matching restrictions effective until a separately
authorized replacement and client reload. The release-create prompt is not
permission to publish without the requested authority.

At coreycoto.com revision `75f3db2de31f2eef90ec065ac6d6e7423bfd4701`, the
project has one file, `.codex/rules/boundaries.rules`, containing 18 rules:
13 prompts and 5 denials, with no allowances. Four denials are general GitHub
restrictions; the fifth covers `bun run database:migrate`. The project also
forbids `gh release create`, while the historical home rule prompts for it.
The stricter project denial must continue to win when that layer is active.
Revision 3 removes the old global Bun restriction. The project made
`codex:sync` read-only in commit
`ee2f75a888360cf23d445d850886d1948b34d23b`. Its remaining project-specific
restrictions are unchanged by this dotfiles proposal.

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

Source merge and staging application are separate from active installation.
This revision does not activate anything. Before a later authorized activation:

1. Review the exact revision-3 files and digests, and identify the current active
   baseline. For the original export, the preflight requires its exact historical
   digest. For an installed revision 2, compare both active file digests with
   `migration.json`'s `previous_policy.files` and the prior private ownership
   receipt. The preview deliberately reports `conflict` for revision-2 bytes;
   it has no upgrade or overwrite mode. Do not treat that result as permission
   to write. Missing, edited or ambiguous baselines require further review.
2. Back up affected active files privately with their modes and digests.
   Managed-target backup.py does not back up unmanaged active rules. Quiesce
   other rule writers and recheck source and destination ownership immediately
   before writing; abort on drift. Do not overwrite locally edited files.
3. Qualify the complete proposed combination with the existing native checker:
   `codex execpolicy check --rules FILE ... -- COMMAND`. Include unchanged
   `default.rules`, unrelated user rules and applicable trusted project rules.
   Use commands only as argument data; never execute a provider operation as a
   policy test. Removed global denials may still match a stricter project rule.
4. Only under separate exact-baseline activation authorization, replace the two
   owned files with the reviewed bytes and private modes. Preserve unrelated
   rules, `default.rules`, configuration and hook trust. Retain the empty
   `legacy-project.rules` replacement so the old global Bun denial is cleared.
   If the original export is still active, leave its retirement pending until
   separately authorized; overlap keeps its old restrictions effective.
5. After installation, reload the relevant clients and verify rule discovery
   separately from offline checks. Preserve both remaining denial groups and
   all eight prompts. Report source, staging, active installation, hook trust,
   reload and runtime evidence as separate stages. On failure, preserve backups
   and the failed-operation evidence; do not retry blindly.

A preflight read cannot make later writes race-free. If exclusive access cannot
be established, leave activation pending. A policy check is neither connector
enforcement nor hook trust, and does not make release draft-state checks atomic.

The native checker suite uses offline synthetic defaults, project prompts,
revision-2 and historical-overlap fixtures. It checks every retained denial and
prompt in both file orders; removed prefixes fall back with no new allowances.
Explicit synthetic allowances and stricter prompt/forbidden layers remain
respected in both orders. Draft release edits stay forbidden. CI installs the
pinned Codex 0.162.1 checker so these tests run there as well as locally.
No test executes a release or provider command.

Sources: [Codex rules](https://learn.chatgpt.com/docs/agent-configuration/rules),
[coreycoto.com sync retirement](https://github.com/coreycoto/coreycoto.com/commit/ee2f75a888360cf23d445d850886d1948b34d23b).

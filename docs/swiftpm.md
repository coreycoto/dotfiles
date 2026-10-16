# Swift toolchain and package collections

Xcode owns the Apple Swift compiler, SDKs, and Swift Package Manager on macOS.
The selected Apple toolchain is separate from the project-owned Tuist version
managed by mise. These dotfiles do not install another Swift compiler, switch
the active Xcode, or copy an SDK into the home directory.

Check the selected tools before working on a project:

```sh
xcode-select --print-path
xcrun --find swift
xcrun swift --version
xcrun --show-sdk-path
```

Read the project's required Xcode/Swift versions, CI configuration, SDK and
deployment targets, `Package.swift` tools version and language settings, and
dependency-resolution policy. A `swift-tools-version` requirement is not an
exact machine toolchain pin. Project manifests, build settings, and reviewed
`Package.resolved` files stay in their repositories; collections do not select
dependency versions.

For an installed alternative Xcode, prefer a deliberate per-command selection:

```sh
env DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun swift --version
```

Adapt the path to the project's selected installed Xcode. A global
`xcode-select --switch` changes other projects and needs its own explicit host
decision. iOS/macOS application workflows can require the full Xcode app,
rather than only the Command Line Tools package. See Apple's
[command-line tool selection](https://developer.apple.com/documentation/xcode/configuring-command-line-tools-settings).

## Collection selection: documentation only

No collection configuration is managed by chezmoi. Keep collection sources
local and preserve existing selections. Apple's public collection is documented
in the [Swift package collections guide](https://www.swift.org/blog/package-collections/).

Collections help discover packages; their downloaded metadata and SQLite caches
are generated state. A configured collection URL is a source selection, not a
reason to import the discovery database. Registries and mirrors can also affect
resolution and authentication, so they require their own project or host review.

To deliberately select the public Apple collection on another Mac, inspect the
installed tool's help and existing selections first. A list can disclose private
collection sources; review it locally rather than capturing it in Git:

```sh
xcrun swift package-collection list
xcrun swift package-collection add --help
xcrun swift package-collection add \
  https://developer.apple.com/swift/packages/collections/apple.json
```

Adding a collection fetches metadata and can prompt for trust. Keep signature
validation enabled; do not use `--skip-signature-check` or auto-accept unsigned
collections. Review any trust decision locally. If the source is already
selected, preserve it rather than rewriting the file or adding duplicates.
These commands are explicit onboarding actions, not chezmoi or startup scripts.

## macOS directories and compatibility links

SwiftPM manages its own configuration, security and cache locations. The
[upstream directory implementation](https://github.com/swiftlang/swift-package-manager/blob/main/Sources/Basics/FileSystem/FileSystem%2BExtensions.swift)
can create compatibility links under `~/.swiftpm` to macOS Library locations.
Inspect the installed toolchain's actual paths instead of copying another
machine's absolute link destinations.
Do not manage these links, replace them with copied directories, or delete an
older directory merely because its name looks redundant.

Inspect paths and symlink targets before any future configuration migration.
Configuration may include local/private sources; security directories contain
fingerprints and trust decisions; caches contain downloaded metadata and build
state. None of those directories is managed by dotfiles.

## Disposable validation and recovery

For ordinary package trials, use a disposable package plus the installed
toolchain's explicit `--config-path`, `--cache-path`, `--security-path`, and
`--scratch-path` options. Check collection subcommand help separately; do not
assume those path options are supported there. Validate collection changes in a disposable
macOS account or an environment whose Foundation paths have first been checked;
changing `HOME` alone is not proof of isolation. Read the installed help before
assuming a path override is supported.

Collection sources have no dotfiles activation or rollback.
Before an explicit local collection change, privately back up only its source
selection file, following the actual symlink target. Undo an added public source
with the installed tool's removal command, preserving other sources:

```sh
xcrun swift package-collection remove \
  https://developer.apple.com/swift/packages/collections/apple.json
```

If the source existed before the change, retain it. Review the resulting source
list locally. Restore only the affected authored selection if needed; do not
restore generated databases over a running tool or reset the entire SwiftPM
directory. For toolchain rollback, remove a session's `DEVELOPER_DIR` override
or deliberately reselect the prior installed Xcode, then recheck project builds.
Preserve private registries, local mirrors, credentials, security fingerprints,
and trust databases outside Git.

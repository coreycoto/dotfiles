---
name: dotfiles-maintenance
description: Maintain chezmoi-managed dotfiles through source edits, explicit manifest updates, disposable-home validation, and reviewed activation. Use for adding portable preferences, managing authored agent skills, or diagnosing source/target drift.
---

# Dotfiles maintenance

Identify the intended source checkout and read its `AGENTS.md`, inventory,
manifest, and installation procedure. In these dotfiles `.chezmoiroot` selects
`home/`; each managed file must have an explicit source-to-target manifest entry.
Edit authored source rather than an installed copy or generated plugin cache.

Classify additions: portable preferences and authored instructions belong in
source; identity, credentials, installation trees, histories, and generated state
stay local. Preserve unmanaged overlays and unrelated installed skills. Do not
import a whole live application or agent directory to capture a few settings.

Read [chezmoi operations](references/chezmoi.md) when inspecting drift, adding a
managed file, previewing changes, or activating a reviewed checkout.

Validate the manifest and repeated application in the repository's disposable
home checks. Verify referenced files survive installation and resolve relative
to the installed skill, not only relative to the checkout. Use the repository's
staged secret scan before publication.

A source PR and real-home activation are separate outcomes. Apply only within
existing user authorization; when activation is requested, use the documented
backup, preview, apply, and verification procedure for the exact reviewed source.
Do not infer activation from a merge or introduce startup installation hooks.

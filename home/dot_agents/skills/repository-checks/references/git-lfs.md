# Git LFS: pointers and stored content

From the intended checkout, inspect tracking and pending changes:

```sh
git lfs version
git lfs ls-files
git lfs status
git check-attr filter -- path/to/asset
```

Git stores an LFS pointer while the content is stored separately. Inspect the
working file and tracking attributes before concluding it is corrupt; a pointer
can remain after a clone with smudging disabled or a failed object download.
Local Git history does not prove the object exists on the remote.

When the task authorizes downloading the required asset, retrieve only the
relevant content, for example:

```sh
git lfs pull --include='path/to/asset' --exclude=''
```

Pull downloads objects and updates working-tree content for the selected ref.
Verify the intended ref and local changes first, then confirm content is
available. Diagnose authentication or a missing remote object instead of
replacing the pointer with arbitrary local content.

`git lfs track` changes attributes; tracking a pattern does not retroactively
convert old commits. `git lfs migrate` can rewrite history. Keep these operations
separate from ordinary object retrieval and scope them to the requested work.

Sources: [Git LFS](https://git-lfs.com/),
[pull command](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-pull.adoc).

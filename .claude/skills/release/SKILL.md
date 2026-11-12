---
name: release
description: Use when the user asks to release, cut a release, tag a version, bump the version or publish a GitHub release of this hooks repo from the local machine - e.g. "release", "cut v0.3.0", "release a patch".
argument-hint: "[patch|minor|major]"
---

# Releasing

Releases are cut by hand from a clean `main`. Each release is one `chore(release): vX.Y.Z` commit
(version bump, docs `rev:` pins, CHANGELOG entry), an annotated `vX.Y.Z` tag and a GitHub release.
Never tag without that commit, and never push a tag without a GitHub release.

## 1. Preflight

Run all of these and stop on the first failure:

```bash
git branch --show-current                                            # must print main
git fetch -q origin && git status --short --branch                   # clean, not ahead/behind
gh auth status
mise run pre-commit || mise run pre-commit
uv run pytest -q
mise run docs:build
```

- Not on `main`, a dirty tree, or out of sync with `origin/main` → stop and tell the user. Don't
    stash, reset or pull for them
- The first pre-commit run may fail only because a formatter rewrote files. If the second fails too,
    or anything rewrote files, stop: the tree must be clean before the release commit. Never use
    `--no-verify`

## 2. Pick the version

```bash
PREV="$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null)"; echo "${PREV:-<none>}"
git log --oneline ${PREV:+"$PREV"..HEAD}
```

- No previous tag → this is the first release, `NEW=0.1.0` (what `pyproject.toml` already says)
- Otherwise derive the increment from the Conventional Commits in the range: any `!` or
    `BREAKING CHANGE` → major, else any `feat` → minor, else any `fix`/`perf` → patch. Before 1.0,
    major bumps the minor. `$ARGUMENTS` overrides the derived increment
- Only `chore`/`docs`/`test`/`ci`/`refactor`/`style` in the range → nothing user-visible: stop and
    ask whether to release anyway
- Say the version and the reason in one line before going on

## 3. Check the tag is free

```bash
NEW=0.2.0   # X.Y.Z from step 2, no v prefix
git tag -l "v$NEW"; git ls-remote --tags origin "v$NEW"
```

Either prints anything → stop and ask. Never move a tag that is already on `origin`.

## 4. Bump

```bash
mise run release:bump "$NEW"
```

Use exactly this task: it sets `pyproject.toml` and `uv.lock` (via `uv version`) and rewrites every
`rev:` pin of this repo in `README.md` and `docs/` to `v$NEW`. Don't hand-edit those.

First release only: `docs/index.md` has a "Pin `rev`" warning saying there are no release tags yet.
Rewrite it to say to pin a release tag and that `prek auto-update` bumps it.

## 5. CHANGELOG.md

Write the entry by following the `devkit:changelog-generator` skill for the range `$PREV..HEAD`
(the whole history on the first release). The audience is people who use these hooks: keep hook
ids. Prepend it to `CHANGELOG.md` (create the file on the first release). Keep the entry's body; it
becomes the GitHub release notes in step 7.

## 6. Commit, tag, push

```bash
git add pyproject.toml uv.lock README.md docs CHANGELOG.md
git commit -q -m "chore(release): v$NEW"
git tag -a "v$NEW" -m "release v$NEW"
git push origin main "v$NEW"
git log --oneline -1 && git ls-remote --tags origin "v$NEW"
```

The prek `pre-commit` hook runs on commit. If it rewrites files the commit aborts: `git add` them
and commit again. Don't amend, don't `--no-verify`.

## 7. GitHub release

```bash
NOTES="$(mktemp)"   # the CHANGELOG entry body, never a file inside the repo
gh release create "v$NEW" --verify-tag --title "v$NEW" --notes-file "$NOTES"
```

If this fails, leave the commit and tag alone; report the error and the command to re-run.

Report the commit hash, the version, what was pushed and the release URL.

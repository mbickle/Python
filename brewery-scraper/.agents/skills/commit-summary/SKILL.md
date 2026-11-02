---
name: commit-summary
description: Draft a git commit message or a PR title and description from the current diff. Use when asked for a commit message, PR summary, or changelog entry.
---

# Commit and PR summaries

Produce a commit message, or a PR title plus description, that describes the changes actually present on disk. This is drafting only: never run `git commit`, `git push`, or open a PR unless the user explicitly asks.

## 1. Gather

```bash
git status --short
git log --oneline -10
git diff --cached --stat && git diff --stat
git diff --cached
git diff
```

- Read the full diff, not just the stat or the file names.
- Record which files are staged, which are unstaged, and which are untracked (`??`). If the message will not cover everything on disk, say so.
- Skim `AGENTS.md`, the README, and the last few commit subjects for style, attribution rules, and the project's verification commands.

## 2. Classify the change

Group each changed file under one heading: behavior change, refactor, tests, docs, tooling/config, dependencies, cleanup. For each group, state why it matters, not which files it touched.

## 3. Title

- Imperative mood, no trailing period, 72 characters or fewer.
- Lead with the largest user-visible outcome; secondary changes belong in the body.
- No vague verbs (`update`, `improve`, `fix stuff`). Use concrete ones: `Add`, `Split`, `Remove`, `Document`, `Harden`, `Replace`.
- Use a conventional-commit prefix (`feat:`, `fix:`) only if the repo already does.

## 4. Body or description

Commit body:

```
<1-2 sentences: the problem and the approach>

- <area>: <change and why it matters>
- <area>: <...>

Verification: <exact commands run> -> <result>
```

PR description: the same content under `## Summary`, `## Changes`, `## Verification`, and `## Follow-ups` (open risks, known gaps, untracked or unstaged leftovers).

## 5. Rules

- Never claim a check that was not run in this session. Quote the real result ("70 passed", "All checks passed").
- Do not invent issue or ticket numbers; ask if the repo links them.
- Keep unrelated dirt out of the message and call it out separately.
- Follow the repo's attribution policy: omit co-author trailers when `AGENTS.md` or the user says so.
- Match terse repo style for one-line commits; use the full template for PR bodies.

## 6. Optional: commit

Only when asked. Stage the intended files, then:

```bash
git commit -m "$(cat <<'EOF'
<title>

<body>
EOF
)"
```

Do not stage files that were already modified before the task began.

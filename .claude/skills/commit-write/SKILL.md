---
name: commit-write
description: Create a safe, explicit git commit for the current requested scope using the commit-writer agent, precise staging, hooks intact, and no push by default.
---

# commit-write

Use this when the user explicitly asks to commit current changes, write a commit, or says in Russian: "сделай коммит", "закоммить", "напиши commit", "создай коммит".

Prefer the `commit-writer` project subagent for the actual git workflow.

## Required inspection

Run before staging or committing:

```bash
git status --short
git diff
git diff --staged
git log --oneline -n 8
```

## Rules

- Commit only after an explicit user request for this scope.
- Stage only relevant files by exact path.
- Never use `git add .` or `git add -A`.
- Never commit secrets, credentials, `.env`, private keys, or suspicious generated files.
- Never amend unless explicitly requested.
- Never push unless explicitly requested.
- Never skip hooks or bypass signing.
- If hooks fail, fix the cause and create a new commit attempt.
- Leave unrelated user changes unstaged and mention them.
- If the requested scope is unclear, ask before staging.

## Commit message

- Follow recent repository commit style.
- Keep the subject concise.
- Explain why the change exists.
- Use a HEREDOC.
- End with:

```text
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

## Output format

- Files staged.
- Commit message subject.
- Commit hash if successful.
- Remaining changes not included.

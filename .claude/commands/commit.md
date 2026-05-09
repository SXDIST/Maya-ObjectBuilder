---
description: Review repository changes and create a git commit
allowed-tools: Bash(git rev-parse *), Bash(git status *), Bash(git diff *), Bash(git log *), Bash(git add *), Bash(git commit *)
---

Create a git commit from the current repository changes.

Follow this workflow exactly:

1. First check whether the current directory is inside a git repository:

   ```bash
   git rev-parse --is-inside-work-tree
   ```

   If this command fails or does not print `true`, stop immediately and tell the user: `Git is not initialized in this directory.` Do not run `git init` automatically.

2. Inspect the repository state before committing:

   ```bash
   git status --short
   git diff --stat
   git diff
   git diff --cached
   git log --oneline -5
   ```

3. Decide what should be committed:
   - Include only relevant changed/untracked files.
   - Do not stage secrets, local credentials, `.env` files, private keys, generated caches, or unrelated user work.
   - Prefer staging specific files by path instead of `git add .` or `git add -A`.
   - If changes are unrelated or ambiguous, ask the user what to include before staging.

4. Draft a concise commit message that matches the repository's recent style and accurately describes the change.
   - Use imperative mood when appropriate.
   - Focus on the purpose of the change, not a long file-by-file list.

5. Stage the selected files and create a new commit.
   - Never amend an existing commit unless the user explicitly asks.
   - Never bypass hooks with `--no-verify` unless the user explicitly asks.
   - Use a heredoc for the commit message.
   - End the commit message with:

   ```text
   Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
   ```

6. After committing, run:

   ```bash
   git status --short
   ```

   Report the commit hash and any remaining uncommitted files.

If there are no changes to commit, tell the user that the working tree has no commit-ready changes and do not create an empty commit.

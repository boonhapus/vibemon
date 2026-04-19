---
name: wrangle-commits
description: >
  Group staged changes into logical commits.
  Uses caveman-commit message format - see ~/.agents/skills/caveman-commit/SKILL.md for reference.
---

## Workflow

Stage and commit following caveman-commit format:
- <type>(<scope>): <imperative summary>
- Types: feat, fix, refactor, perf, docs, test, chore, build, ci, style, revert

1. Run `git status` and `git diff --stat` to see pending changes
2. Analyze the diff to identify logical groupings
3. Stage files logically using `git add <paths>`
4. Write commit message following caveman-commit rules:
   - `<type>(<scope>): <imperative summary>`
   - Types: feat, fix, refactor, perf, docs, test, chore, build, ci, style, revert
   - Imperative mood (add, fix, remove — not added, adds)
   - ≤50 chars, no trailing period
5. Run `git commit -m "message"`
6. Repeat for remaining changes

## Tips

- New feature ≠ one commit — split if changes are logically distinct
- Refactor often gets its own commit
- Dependency changes = `chore`
- Documentation = `docs`
- If unsure, check `git log --oneline -10` for project style
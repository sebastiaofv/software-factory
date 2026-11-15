# Software Factory

This repository is a reusable GitHub-issue pipeline for subscription-backed
Claude Code and Codex CLIs. Python scripts own workflow state and GitHub
operations; shared Markdown prompts define each model's bounded role.

## Development

Python 3.9+ and Git are sufficient for the automated tests. No package install
is required. Validate changes with:

```bash
python3 -m unittest discover -s factory/tests -v
python3 -m json.tool factory/config.json > /dev/null
git diff --check
```

The test suite uses fake coding/GitHub CLIs and temporary repositories. Keep
live provider requests and real GitHub mutations out of routine verification.
`factory/checks.sh` is an installer template, deliberately failing until adapted
in a target project; it is separate from this repository's own tests.

## Editing

Change role instructions in `factory/prompts/`. Both skills delegate to the
same runner. Add provider-specific behavior in `factory/lib/adapters.py` and
keep scheduling and job state independent of the chosen CLI/model. Authentication
checks must not print credential values or read private CLI token stores.
Usage estimates must distinguish unavailable data from zero and subscription
billing from API-equivalent estimates.

`factory/bin/job` is the only writer of job.json. Runtime artifacts under
`factory/jobs/` and checkouts under `.worktrees/` are gitignored; preserve them
when editing or testing the factory.

For dashboard work, serve `factory/` on localhost with Python's HTTP server.
The reference jobs under `examples/jobs/` can be served as test fixtures without
modifying live runtime state. Consult INSTALL.md and DESIGN.md when changing
execution profiles, installation paths, permissions, or recovery behavior.

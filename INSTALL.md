# Install the software factory

Install into the user's project root. Read the existing project instructions and
preserve unrelated files. The reference source is:

```text
https://raw.githubusercontent.com/sebastiaofv/software-factory/main/<path>
```

## 1. Check the project

- Python 3.9+, Git, and an authenticated `gh` must be available.
- The Git repository must have a GitHub `origin` and an existing default branch
  on that remote. Use `gh repo view --json defaultBranchRef` to identify it.
- Install the coding CLIs used by the chosen profiles. Sign into Claude Code
  with `claude auth login`, and Codex with `codex login`, using subscription
  accounts. For one subscription, configure every role to use that CLI.
- Inspect existing factory files before replacing them. For an upgrade, preserve
  the target project's checks, prompts, model choices, and runtime jobs.

The adapter flags have been checked against Claude Code 2.1.325 and Codex CLI
0.162.1. Use current versions supporting the flags described in `DESIGN.md`.
The factory uses Python's standard library; no model SDK is required.

## 2. Copy the files

From the reference source, copy these paths into the same locations:

```text
.agents/skills/factory/SKILL.md
.claude/skills/factory/SKILL.md
factory/bin/factory
factory/bin/job
factory/bin/gate
factory/bin/route
factory/lib/__init__.py
factory/lib/config.py
factory/lib/adapters.py
factory/lib/runner.py
factory/prompts/intake.md
factory/prompts/spec-writer.md
factory/prompts/builder.md
factory/prompts/reviewer-code.md
factory/prompts/reviewer-security.md
factory/prompts/reviewer-ui.md
factory/prompts/approver.md
factory/config.json
factory/checks.sh
factory/dashboard.html
factory/tests/fake_cli.py
factory/tests/test_factory.py
```

For each path, create its parent directory and download the matching raw URL.
Use `curl -fsSL` so an HTTP error fails the install. Then make the commands
executable:

```bash
chmod +x factory/bin/factory factory/bin/job factory/bin/gate factory/bin/route factory/checks.sh
```

Do not copy the reference's README, design guide, examples, or root AGENTS.md
into another project. Their contents describe this repository. The skill points
to INSTALL.md and DESIGN.md when those files exist; in an installed target,
use the project's own factory instructions instead.

## 3. Configure the target project

### Project checks

Replace `factory/checks.sh` with the project's real install, lint, typecheck,
test, and build commands as appropriate. Read the project instructions, manifest,
and CI configuration. Keep `set -euo pipefail`; commands must be noninteractive
and exit nonzero on failure. Verification must not rewrite source or snapshots.
Run the checks on the project's base branch before starting a job.

The failing checks template is intentional: do not replace it with an empty
successful script. Factory self-tests are a separate command:

```bash
python3 -m unittest discover -s factory/tests -v
```

### Profiles and routing

Adapt `factory/config.json`:

- Set `base_branch` to the remote default branch and `merge_method` to a method
  enabled by the repository.
- Configure `profiles` with the installed CLI (`claude` or `codex`), a model
  supported by the subscription, and optional `reasoning_effort`. Null model
  and effort settings use the CLI's defaults.
- Assign a profile to all four `steps`: intake, spec-writer, builder, approver.
  Set reviewer profiles in `routing` and `surface_reviewers`. Every risk tier
  must include a code reviewer.
- For a single-CLI installation, update every step and reviewer reference to a
  profile for that CLI. Unused profile definitions do not require that CLI.
- Retain factory internals in `protected_paths`; add other paths only when a
  job must never modify them. Existing project tests should generally remain
  editable. Patterns use fnmatch semantics, where `*` can also match `/`.
- Set `max_grill_rounds` (question rounds intake may post on an issue) and
  `simple_track_risks` (risks allowed on the simple track: `low`, optionally
  `medium`, never `high`).
- Set `concurrency`, `max_rounds`, `step_timeout_seconds`, and
  `check_timeout_seconds` to appropriate project limits. Start with concurrency
  1 when evaluating a new installation.
- Move `ports.base` if the project already uses its allocated range.

The runner rejects recognized API-key or alternate-provider environment
overrides for the selected CLI. It does not remove them silently. Unset the
reported variable names in the execution environment; never print their values
or copy authentication files into the repository. CLI and account extra-usage
settings remain the operator's responsibility.

### Shared prompts

Tailor `factory/prompts/` to the project without changing the required output
filenames or first-line formats. In particular:

- Intake: describe the project's purpose so it can judge what belongs, and
  what makes a change simple or complex in this project.
- Security review: identify auth, payment, data-access, and input-handling areas.
- UI review (one session covers UX and visual design): document users, design
  conventions, and how to run browser verification. The supplied prompts expect an installed `agent-browser` CLI.
- Approver: state which changes need a human product or operational decision.

Keep the intake header lines (`DECISION`, `RISK`, `TRACK`, `SURFACES`,
`RESCOPED`) and the `## Questions` section: the runner validates the header,
and the questions are what the factory posts on the issue.

### Domain language

The prompts read the project's domain glossary (`GLOSSARY.md`, or an existing
`CONTEXT.md`; a `GLOSSARY-MAP.md` or `CONTEXT-MAP.md` for several contexts),
its ADRs in `docs/adr/`, and `.out-of-scope/*.md` for rejected requests, when
they exist. None is required: the builder creates the glossary and ADR folder
when a spec first asks for an entry. Don't add them to `protected_paths`.

The runner controls the CLI/model for each role. Shared prompts must not
hardcode provider-specific spawning, stop hooks, or session resumption tools.
The builder leaves source changes for the runner to commit and publish.

### Project instructions

Update the target project's AGENTS.md (create it if absent). Document setup,
validation commands matching checks.sh, and how to run its development server on
a supplied port. Add a concise factory section:

```markdown
## Software factory

Run `factory/bin/factory run` for open issues labeled `factory`, or add an issue
number to run one. Intake may grill the author on the issue first: answer its
numbered questions in a comment and rerun, or keep `factory/bin/factory run --watch`
running so replies, feedback, and newly labeled issues are picked up as they arrive. Claude's `/factory` and Codex's `$factory` invoke the same
runner. Profiles in `factory/config.json` select the coding CLI/model per role.
Project checks: `factory/checks.sh`. State and native CLI logs live in
`factory/jobs/`; each job's checkout is `.worktrees/<job-id>`. Both directories
are gitignored. Only `factory/bin/job` writes job.json.

Dashboard: `python3 -m http.server --bind 127.0.0.1 --directory factory 8000`,
then open http://localhost:8000/dashboard.html. This serves the installed
`factory/dashboard.html` directly, regardless of the project folder's name.
```

Tell tools that do not honor `.gitignore` to exclude `.worktrees/`, which
contains full additional checkouts.

### Gitignore and labels

Append these paths if missing:

```gitignore
/factory/jobs/
/.worktrees/
```

Keep the skills, shared prompts, scripts, and configuration committable. Create
missing GitHub labels (preserve existing labels):

```bash
gh label create factory --color 5319E7 --description "Build this with the software factory"
gh label create factory:needs-info --color FBCA04 --description "The factory is waiting for answers on the issue"
gh label create factory:needs-human --color D93F0B --description "The factory needs a human decision"
```

## 4. Verify

1. `bash factory/checks.sh` passes on the base branch.
2. `python3 -m unittest discover -s factory/tests -v` passes. These tests use
   temporary local repositories and fake CLIs; no subscription requests or real
   GitHub writes are made.
3. `factory/bin/factory doctor` verifies profile references, the selected CLIs'
   subscription logins, GitHub authentication, prompts, and configured checks.
   It does not spend model tokens or prove every selected model's entitlement.
4. `factory/bin/job queue` can read the project's labeled issues. This command
   can reconcile already merged jobs; run it only in the installed target.
5. `git check-ignore factory/jobs/x .worktrees/x` prints both paths. All copied
   implementation and skill files remain committable.

Job receipts upgrade in place: runs recorded before tracing have no
`duration_seconds` or `uncached_input_tokens`, so the trace derives them from
timestamps and from input minus cached input, and jobs created earlier have no
stage `history`.

## 5. Upgrade an existing installation

The older Claude-only factory used `.claude/agents/*.md`, a Claude-specific stop
hook, bare model aliases in routing, and transcript-based cost accounting.
Move project-specific instructions from those agent files into the matching
`factory/prompts/` files. Remove only obsolete factory agent definitions and
hook entries after preserving their customizations; keep unrelated agents and
hooks. Both skill entry points now delegate to the shared runner.

Use the new profiles/steps/routing structure while retaining the target's base
branch, checks, limits, and protected paths. Add `max_grill_rounds` and
`simple_track_risks` to an older config.json, and merge project customizations
into the new intake, spec-writer, builder, reviewer-code, reviewer-ui and
approver prompts.
An accepted intake.md from before tracks has no `TRACK` line; let such jobs
finish, since later roles then see `Track: not chosen yet`. Finish or inspect active jobs before
upgrading. Historical example artifacts remain readable. For a legacy active
job whose agents still contain model aliases, reroute an accepted intake job
with `factory/bin/route <id>`; jobs already past intake need their previous
installation to finish or an explicit migration. The new runner refuses unknown
legacy profiles rather than silently selecting another provider.

`reviewer-ux` was merged into `reviewer-ui`: one session now judges both the
flow and the visual design. Merge any project-specific UX instructions into
`factory/prompts/reviewer-ui.md`, delete `reviewer-ux.md`, and replace a
`"ui": { "ux": ..., "ui": ... }` surface mapping with `"ui": { "ui": <profile> }`.
A job routed before the merge that still lists a `ux` reviewer stops with a
clear error; reroute it, or let the previous installation finish it.

## 6. Hand over

Keep the current branch. Show the changes and verification results. Explain
that the installation must be available on the remote base branch because job
worktrees start from it. Do not start real factory jobs as an installation test
unless the user requested them. Each run can publish and merge real PRs.

Ask the user to label a small issue `factory`, run it, and inspect its PR and
local dashboard. Explain how to choose CLI profiles and where failures and
usage receipts appear: `factory/bin/factory trace <issue>` and the dashboard's
trace view list every step's time and tokens, and README.md's "Tracing and
debugging a job" explains the run folders. Subscription limits and extra-usage
settings still apply.

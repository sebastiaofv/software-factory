# Software Factory

Build GitHub issues through a repeatable pipeline, using your Claude Code and
Codex subscriptions. Pick a CLI and model independently for intake, specs,
building, reviews, and approval. A shared Python runner handles job state,
worktrees, checks, PRs, and merging.

## Install

Open Claude Code or Codex in the project you want the factory to work on and ask:

```text
Install this software factory in this project from:
https://github.com/sebastiaofv/software-factory
Follow INSTALL.md and configure the project's real checks.
```

You need Python 3.9+, Git, an authenticated [GitHub CLI](https://cli.github.com/),
and whichever coding CLIs your selected profiles use. The default configuration
uses both Claude Code and Codex. Sign in with your subscription accounts using
`claude auth login` and `codex login`. No model API integration is needed.

Run `factory/bin/factory doctor` after installation. This reference repo leaves
`factory/checks.sh` as a failing installer template: configure the target
project's real checks before running jobs. Tests for the factory itself are
separate: `python3 -m unittest discover -s factory/tests -v`.

## The loop

```mermaid
flowchart TD
    Issue["GitHub issue labeled factory"] --> Intake{"Intake · configured CLI / model"}
    Intake -->|NEEDS-INFO| Question["Post a grilling round on the issue"]
    Question -->|Author answers and run resumes| Intake
    Intake -->|REJECT| Rejected["Explain why and remove the label"]
    Intake -->|ACCEPT| Route["Route reviewers by risk and surfaces"]
    Route -->|simple track| Spec["Spec writer · configured CLI / model"]
    Route -->|complex track| Spec
    Spec --> Build["Builder · configured CLI / model"]
    Build --> Publish["Runner commits, pushes, and opens a draft PR"]
    Publish --> Gate{"Gate · project checks"}
    Gate -->|FAIL| Build
    Gate -->|PASS| Review{"Parallel reviewers · configured CLIs / models"}
    Review -->|CHANGES| Build
    Review -->|All PASS| Approver{"Approver · configured CLI / model"}
    Approver -->|APPROVE| Sync["Sync with base branch and run the gate again"]
    Sync -->|PASS| Merge["Merge the PR through GitHub"]
    Sync -->|Conflict or failure| Human["Human review · factory:needs-human"]
    Approver -->|ESCALATE| Human
```

The workflow borrows from [Matt Pocock's skills](https://github.com/mattpocock/skills):
intake **grills** the author on the issue before anything is built, the domain
glossary and ADRs keep the project's language consistent, the builder works
**test-first** in vertical slices, the code reviewer checks the Spec and
Standards axes separately, and specs design **deep modules** behind few seams.

Intake puts each accepted job on one of two tracks. The **simple** track (by
default only low-risk work) gets a short brief and light grilling. The
**complex** track gets grilled until every open decision is settled, and its
spec designs the modules, test seams, slices, glossary and ADR changes before
the builder starts. Both tracks share the same stages and reviewers.

Grilling happens on the GitHub issue. Each round is one comment, `Factory
grilling: round k`, with numbered questions and a recommended answer for each.
Answer in a comment, by number or with "go with your recommendations", then
rerun the factory: it rereads the issue and continues. After
`max_grill_rounds` rounds, intake must accept with its recommended answers or
reject.

Failed checks always return to the builder, which must fix every failure,
flaky or unrelated tests included, until the gate passes. Only a builder that
stops making progress escalates: after `max_stalled_rounds` (default 2) failed
gates in a row on an unchanged commit, or after `max_check_rounds` failed gates
in a row when you set that cap (`null`, the default, or `0` means unlimited).
Requested review changes return to the builder up to `max_rounds`; check-fixing
rounds don't count against it. After that, or when the builder is blocked, the
job goes to a human.
The runner runs up to `concurrency` jobs at once. Reviewers within each job run
in parallel: a code reviewer always, a UI reviewer (UX and visual design, in one
browser session) for `ui` changes, and a security reviewer for `security`
changes. Each job gets its own `.worktrees/<job-id>` checkout.

## Commands

Label an open issue `factory`, then run from the repository root:

```bash
factory/bin/factory doctor       # configuration, logins, and installation
factory/bin/factory run          # drain the queue; also resume interrupted jobs
factory/bin/factory run 12       # one issue
factory/bin/factory run --watch  # keep running: pick up replies, feedback, new issues
factory/bin/factory status       # local jobs and usage
factory/bin/factory trace 12     # every step of issue 12: time, tokens, verdict
```

`run --watch` (optionally with an issue number and `--interval <seconds>`,
default 60) does not exit when every job waits on a person. It rechecks GitHub
and starts jobs as authors answer grilling questions, as you give feedback with
`job feedback`, or as issues are labeled, while other jobs keep running. A job
that fails is reported and skipped until you restart the watcher. With an issue
number it exits once that issue is merged, rejected, or closed. Stop it with
Ctrl-C.

In Claude Code, use `/factory run` or `/factory run 12`. In Codex, invoke the
factory skill with `$factory` and ask it to run the queue or issue 12. Both
entry points execute the same runner; the host chat does not determine which
CLI builds or reviews the job.

Give feedback on an escalated job through either skill, or use
`factory/bin/job feedback <issue>` with your feedback on stdin and then rerun
that issue. Reject a waiting job with `factory/bin/job reject <issue>` and a
reason on stdin. You can also approve an escalated PR by merging it on GitHub.

## Choose CLIs and models

`factory/config.json` defines named profiles. Each profile selects `claude` or
`codex`, an optional model, and optional `reasoning_effort`. A null model or
effort uses that CLI's current default. Choose models available to your account.
Claude profiles accept `low`, `medium`, `high`, `xhigh`, or `max` (passed as
`claude --effort`); Codex profiles accept `none`, `minimal`, `low`, `medium`,
`high`, `xhigh`, `max`, or `ultra` (passed as `model_reasoning_effort`).

```json
{
  "profiles": {
    "claude-fast": { "cli": "claude", "model": "haiku", "reasoning_effort": "low" },
    "claude-balanced": { "cli": "claude", "model": "sonnet", "reasoning_effort": "medium" },
    "claude-strong": { "cli": "claude", "model": "opus", "reasoning_effort": "medium" },
    "codex": { "cli": "codex", "model": null, "reasoning_effort": null }
  },
  "steps": {
    "intake": "claude-fast",
    "spec-writer": "codex",
    "builder": "claude-strong",
    "approver": "codex"
  },
  "routing": {
    "low": { "code": "codex" },
    "medium": { "code": "codex" },
    "high": { "code": "codex" }
  },
  "surface_reviewers": {
    "ui": { "ui": "claude-balanced" },
    "security": { "security": "claude-strong" }
  }
}
```

This is the profile and routing portion of the shipped `factory/config.json`
(which also defines `codex-fast`, `codex-balanced` and `codex-strong`); retain
the other settings. The `ui` surface adds one reviewer that judges both the
flow (UX) and the visual design in a single browser session. For a single
subscription, point every step and reviewer at a profile using that CLI. Another CLI requires an adapter that implements authentication,
command construction, and result parsing in `factory/lib/adapters.py`.

## Dashboard

```bash
python3 -m http.server --bind 127.0.0.1 --directory factory 8000
```

Open <http://localhost:8000/dashboard.html>. Inspect each job's stages, routed
profiles, usage, check results, and review documents. Cards show tokens as
uncached input, cached input and output; a job's drawer has its full trace. To view the included
historical examples, copy `examples/jobs/` to `factory/jobs/` in a fresh checkout.

The runner stores native CLI output, prompts, and execution receipts under
`factory/jobs/<id>/runs/`. Token usage and any available API-equivalent estimate
are separate from subscription billing. Codex does not report a dollar estimate
in the supported JSON event stream, so mixed runs show an unavailable estimate
instead of treating missing cost as zero. Historical examples retain their
recorded estimates.

## Tracing and debugging a job

Every step leaves a record, so you can see later where a job's time and tokens
went and why it stopped.

### What is recorded

| Where | What |
|---|---|
| `factory/jobs/<id>/runs/<run>/result.json` | One receipt per CLI step and per gate run: role, round, stage, profile, models, commit, status, verdict or error, start, end, `duration_seconds`, tokens, session id. Gate receipts (`kind: check`) also hold the exit code and protected-path changes. |
| `runs/<run>/prompt.txt` | The exact prompt the CLI received. |
| `runs/<run>/stdout.jsonl` | The CLI's native output as it happens: Claude's stream-json events or Codex's JSONL events, with native usage fields. A step that timed out keeps its output so far. |
| `runs/<run>/stderr.log` | The CLI's error output. |
| `job.json` → `usage.executions` | Every receipt as one row, in start order, with the run folder name. |
| `job.json` → `usage.by_role` | Runs, seconds and tokens per role (`intake`, `builder`, `gate`, `reviewer-code`, ...). |
| `job.json` → `usage.tokens` | Token totals for the job. |
| `job.json` → `history` | Every stage transition with its time and round, including time spent waiting on the author (`needs-info`) or on you (`needs-human`). |

Runs whose receipt says `running` were interrupted; they stay visible. A step
reused from an earlier run (same role, round, commit, profile and source) starts
no CLI and adds no row.

### Reading it

```bash
factory/bin/factory trace 12           # runs, totals by role, time in each stage
factory/bin/factory trace 12 --json    # the same data, for scripts
```

`trace` takes an issue number or a job id. Its table has one row per run (numbers
illustrative):

```text
started              round  step           profile          status     verdict  time    uncached in  cached in  out    run
2026-11-20 09:12:03  0      intake         claude/haiku     completed  ACCEPT   41s     18,204       96,512     1,830  20261120T091203...-intake-1a2b3c
2026-11-20 09:12:44  1      builder        claude/opus      completed  READY    7m12s   64,920       1,402,118  21,407 ...
2026-11-20 09:19:58  1      gate           -                completed  FAIL     1m03s   -            -          -      ...
```

The dashboard's job drawer shows the same view under **trace: time & tokens**;
hover a row for its run folder or error. While a job runs, the runner also
prints one line after each step: `001-add-numbers: builder completed in 412s,
64,920 uncached in, 1,402,118 cached in, 21,407 out`.

### Token columns

- **uncached in**: prompt tokens not read from the provider's cache. For
  Claude this is input plus cache writes; for Codex, input minus cached input.
  This is the part that grows a session's cost fastest.
- **cached in**: prompt tokens read from cache. Each turn of a session resends
  its context, so this is usually the largest number, but providers count it
  far more cheaply.
- **out**: generated tokens, including reasoning where the CLI reports it.

Usage a CLI didn't report shows as `-` or "tokens unavailable", never as zero.
Gate rows have no tokens: they run `checks.sh`, not a model.

### Debugging a slow, expensive or failed job

1. Run `factory/bin/factory trace <issue>` and look at **By role** for the
   role with the most time or uncached input, and at **Stages** for where the
   job waited.
2. Find the run in the table and open `factory/jobs/<id>/runs/<run>/`.
   `prompt.txt` shows what the step was told; `stdout.jsonl` shows what it did,
   turn by turn; `result.json` has the error for a failed step.
3. For a failed gate, read `round-<N>/checks.md` and `checks.log`
   (`merge-checks.*` for the gate before merging).
4. Repeated builder rounds usually mean the gate or a reviewer keeps failing:
   compare that round's `checks.md` or `review-*.md` with the next `build.md`.
   job.json's `check_streak` counts the current run of failed gates
   (`failures`) and of rounds that changed nothing (`unchanged`).

The `session_id` in each row is the CLI's own session, useful when reporting a
problem with that CLI. The factory never resumes it.


## What's in here

```text
.agents/skills/factory/     shared Codex skill and workflow entry point
.claude/skills/factory/     Claude Code entry point to the same workflow
factory/
  bin/factory              runner commands: run, doctor, status, trace
  bin/job                  job state transitions and GitHub side effects
  bin/gate                 deterministic checks in a job's worktree
  bin/route                risk and surfaces → execution profiles
  lib/                     configuration, subscription CLI adapters, scheduler
  prompts/                 provider-independent role instructions
  config.json              profiles, routing, concurrency, timeouts, guardrails
  checks.sh                project checks; filled in during installation
  dashboard.html           local job board
  tests/                   temporary-repository tests with fake coding CLIs
examples/jobs/             historical example artifacts
INSTALL.md                 installation and upgrade instructions
DESIGN.md                  execution design, permissions, and recovery limits
```

## Subscriptions and permissions

- Claude Code must report a first-party subscription account; Codex must report
  ChatGPT login. The adapters refuse detected API-key/provider environment
  overrides. Your provider's account limits and extra-usage settings still apply.
  The factory cannot enforce a subscription's spending cap or verify entitlements
  for every selected model.
- Claude runs noninteractively with file tools and shell commands allowed;
  permission prompts are denied. Codex uses its workspace-write sandbox, the
  job directory as an additional writable directory, and network access enabled
  for project checks. Neither adapter adds a sandbox-bypass flag. Organization
  policy and existing CLI configuration may still restrict tools.
- These CLIs execute repository code with your local account's access. Keep
  production secrets out of the execution environment. Test UI changes with an
  installed `agent-browser` CLI as described in the review prompts.
- Only open issues labeled `factory` start. Agents write bounded role artifacts;
  the runner owns commits, pushes, PRs, and state transitions. The gate reruns
  project checks before review and after syncing for merge.
- Runs open and may merge real PRs. Start with `concurrency: 1`, inspect the
  results, and tailor escalation rules in `factory/prompts/approver.md`.

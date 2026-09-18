## Why

The rule this gate enforces is fixed rather than chosen here, and it has exactly two
satisfying conditions. That settles both halves of the contract before this change starts: the
gate looks for a spec file in the diff **or** an
`sdd-exception: (.+)` line in the description, and nothing else decides the verdict. "Spec file"
is read literally — a requirement delta under `openspec/changes/<change>/specs/` or the agreed
baseline under `openspec/specs/`, not a proposal.

This repository is a good place to prove it on GitHub Actions. It asks contributors to work
spec-first and has no mechanism that notices when they do not. The asking is thorough:
`AGENTS.md` — Specs names `openspec/specs/` as the capability baseline and tells a reader to
read the relevant spec before touching `reporting/live.py`, `transport.py` or the runner's
live-event emission; `CONTRIBUTING.md:18` routes every contributor to `openspec/project.md` as
the working agreement. The enforcement is nothing. `.travis.yml` is the only committed CI, and its two lanes
are `TOXENV=py312` and `TOXENV=flake8` plus a tag-triggered PyPI deploy — it proves the code
works and says nothing about whether the process was followed.

The consequence is already visible in the tree. Four changes sit in flight under
`openspec/changes/` — `add-agent-docs`, `enforce-sdd-and-audit-docs`, `harden-release-process`,
`enforce-release-notes-and-cadence` — and all four are documentation and tooling. Every
behavioural spec in the baseline covers one feature: the six capabilities behind `--live`, all
authored in a single March batch and archived together. Roughly the rest of the library has no
spec at all. A rule that no build enforces produces exactly this shape — the process is
followed while someone is paying attention to it and quietly stops when they are not.

`enforce-sdd-and-audit-docs` recognised the gap and its tasks 5.1–5.4 proposed the gate, but
that change carries docs corrections, an audit script and a `.claude` override alongside it and
has not landed; the gate has been blocked behind work it does not depend on for a month. A
workflow was drafted outside version control in the meantime (see design.md — Context) and
never committed, which is the strongest available evidence that this needs to be its own
change rather than a task group inside a larger one.

Now, because the contract is settled. Spektrum is the GitHub Actions proof of it: it is public,
it has no Actions workflow at all yet, and its OpenSpec tree is already clean —
`openspec validate --all --strict` exits 0 across all 10 items today. The gate can therefore be
introduced green, which is the one moment where it costs nothing to introduce.

## What Changes

- **Add a `pull_request`-triggered GitHub Actions workflow with two hard-failing jobs.** Job 1
  runs `openspec validate --all --strict`. Job 2 applies the two-condition rule below.
- **`--strict`, not bare `--all`.** The relaxed form accepts a spec whose requirement has no
  scenario, which is the most common way an authored spec turns out to be unusable. Since the
  repository already passes strict validation, anything less would ratchet the baseline down.
  **A declared exception does not waive validation**: it excuses the absence of a spec, never a
  corrupt one.
- **Two conditions, no path carve-outs.** A pull request passes job 2 if its diff adds or
  modifies at least one **spec file**, **or** its description contains a line matching
  `sdd-exception: (.+)` with non-empty captured text. Neither condition met, the gate fails.
  There is no exemption list: the obligation applies to every pull request regardless of what
  it touches, because the exception line already provides the relief an exemption list was
  reaching for, and provides it with a reason attached. A docs-only or `setup.py`-only pull
  request is not exempt; it states an exception, in one line, and says why.
- **A spec file, not any OpenSpec file.** Condition 1 is satisfied only by a `spec.md` under
  `openspec/changes/<change>/specs/` (a requirement delta) or under `openspec/specs/` (the
  agreed baseline). A `proposal.md`, `design.md`, `tasks.md` or `.openspec.yaml` on its own does
  not count: a proposal states motivation, a spec states the contract, and accepting the former
  would let a pull request present as spec-first while shipping no requirement at all — exactly
  the gap the gate exists to close. Including the baseline path means an archive passes by
  construction, since `openspec archive` writes `openspec/specs/`. A proposal-stage pull request
  is not stuck, it is recorded: `sdd-exception: proposal stage, spec deltas follow` names the
  stage the work is at instead of letting it pass silently.
- **The exception must capture a reason, and the job echoes it into the log.** The text after
  `sdd-exception:` has to be non-empty — a bare marker, an empty value or a label does not
  satisfy the rule. A label is one click and records no reason; captured text forces prose that
  a reviewer sees, and echoing it into the job's output means the justification survives in the
  build log rather than only in a field that can be edited afterwards. On GitHub the
  description is read from `github.event.pull_request.body`.
- **Evaluated once over the pull request's `base..head` diff, never per commit.**
  `openspec/project.md` asks for a PR to be squashed to one commit but explicitly endorses
  working in as many commits as you like while the branch is local; a per-commit rule would
  fail the spec-then-implementation shape the project recommends.
- **The gate blocks the merge, and the exception line is the sanctioned override.** Both jobs
  are registered as required status checks on the default branch — on GitHub a check blocks only
  by being named there, so the registration is named as part of this change rather than left to
  a later decision. The override is not a hole in a blocking gate; it is what keeps blocking
  proportionate. Without a required check, a pull request can be merged having done neither
  thing — no spec file and no stated reason — leaving a red run nobody is accountable for. With
  one, it can be merged only after one of the two has been done, and the relief is a single
  sentence that needs nobody's approval and is itself the record of why the rule was set aside.
- **The dependency is pinned to the correct package.** `@fission-ai/openspec@^1.12.0`. The
  unscoped `openspec` name on npm is a different package by a different author and installing
  it does not produce this CLI.
- **Travis is not touched.** It keeps tests, lint and the deploy. One job per concern: Travis
  proves the code works, Actions proves the process was followed, and a contributor can tell
  from the check's name which red build is which.

## Capabilities

### New Capabilities

- `sdd-ci-gate`: The repository's continuous-integration contract for spec-driven development —
  the two ways a pull request can satisfy the spec-first rule, what counts as a spec file, which
  conditions fail its checks, over which diff they are evaluated, and what a declared exception
  has to contain.

### Modified Capabilities

_(none — the six capabilities under `openspec/specs/` all describe the library's live view and
are untouched by this change.)_

A note on why this change declares a capability when its four in-flight siblings all set
`skip_specs: true`. That marker is right for them: their deliverables are corrected prose, a
release script and an audit tool, and "the documentation is accurate" is not a behaviour a
requirement can pin down. This gate is different in kind. It is a function from a diff and a
description to a pass/fail verdict, and every interesting question about it — does a bare
`sdd-exception:` with no text pass, does a docs-only PR need one, does a PR that adds only a
proposal count as spec-first, is the verdict taken over the squashed diff or the last commit,
does an exception excuse a malformed spec — has exactly one
correct answer that a reviewer must be able to look up rather than read off a shell script. The
gate is also the artifact every sibling repository will be checked against, so the
requirements, not one repository's YAML, are the shared thing. Inventing a requirement to
satisfy validation would be wrong; declining to write one for behaviour this precise would be
worse.

## Impact

- `.github/workflows/` — new. This repository has never had an Actions workflow, and COS-29
  removes the one file `.github/` did track, so this is the only thing in it.
- **New external dependency: Node and npm in CI.** The OpenSpec CLI is a Node package and the
  Travis matrix is Python-only. This is the first non-Python tool in the repository's build,
  and it is confined to the new workflow.
- `CONTRIBUTING.md` — one paragraph naming which CI system owns tests and lint versus which
  owns process, stating that the process gate holds the merge until one of the two conditions is
  met, and showing the `sdd-exception:` line so a contributor who needs it can copy it. **The
  gate's behaviour is specified here; the prose lands with the workflow.**
- **No pull request template.** COS-29 removes `.github/pull_request_template.md`:
  a description carries the change information and the test-run output, nothing else. So the
  exception line is taught by `CONTRIBUTING.md` and by the gate's own failure message, which
  has to state both satisfying conditions and how to re-run — there is no form to put it on.
- `enforce-sdd-and-audit-docs` — tasks 5.1–5.4 are superseded on two points, and two of their
  instincts are kept. That change's design paired a `spektrum/`-watched path rule with a
  `no-spec` label, ran `openspec validate --all` without `--strict`, and described the check as
  merge-blocking. The watched path and the missing `--strict` are the two decisions reversed
  here, for the reasons in design.md — Decisions. The merge-blocking framing is not one of
  them: it was right, and this change implements it. So is the escape hatch — wanting a way for
  an author to say "no spec, and here is why" is exactly what the rule provides, and it is also
  what lets the check block without becoming a stoppage. What changes there is the mechanism,
  not the intent — a label is one click that records no reason, an `sdd-exception: (.+)` line
  captures the reason in the description where a reviewer reads it and the job can echo it into
  the log. Whoever lands that change should strike section 5 rather than build it twice.
- **Branch protection on the default branch** — the two job names are added to its required
  status checks, and nothing else in that configuration changes. It is repository configuration
  rather than a file in the diff, so it cannot be reviewed in the diff; it is recorded here and
  in design.md, and it lands with this change rather than after it.
- **Not touched:** `spektrum/`, `tests/`, `.travis.yml` and `tox.ini`. No library behaviour
  changes and no released artifact moves.
- Tracked as **COS-31**. Related: **COS-30** carries the shared GitLab CI template for the same
  contract. GitHub Actions and GitLab CI share no configuration, so this is an independent
  proof of the contract on a second platform, not a port of that work; the requirements are the
  shared artifact, and only the host-specific details — `github.event.pull_request.body` versus
  the merge request's description — differ.

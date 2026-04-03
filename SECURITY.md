# Security Policy

Stream is still an early-stage library. The project has already been tightened through tests, validation rules, packaging checks, workflow checks, and documentation review, but we still want security feedback, correctness feedback, and hardening suggestions early and often.

## Reporting A Vulnerability

If you believe you have found a security issue in Stream, please avoid posting full exploit details, secrets, tokens, or private infrastructure information in public.

For most reports in this repository, GitHub-native collaboration is preferred:

- open a GitHub issue for suspected weaknesses, unsafe behavior, missing validation boundaries, packaging concerns, dependency-risk findings, workflow-policy problems, or replay/integrity behavior that is safe to discuss publicly,
- open a pull request if you already have a concrete hardening fix, regression test, workflow improvement, or documentation update,
- use the repository security reporting channel if it is enabled for anything sensitive that should not be disclosed publicly yet.

When filing an issue, PR, or private report, include:

- a short description of the issue,
- affected versions or commit range,
- reproduction steps or proof of concept,
- potential impact,
- whether the issue affects append, scan, replay, export, integrity, rebuild, or repair behavior.

If you are unsure whether something is a security bug or a correctness bug, open an issue anyway and mark it clearly as a suspected security concern.

## Supported Versions

Security fixes are expected to target the most recent development line first. Older versions may not receive backported fixes unless explicitly stated.

## What Kinds Of Reports Are Especially Helpful

For Stream, especially useful reports include:

- canonical history corruption that can be silently misinterpreted,
- `strict` replay paths that fail open instead of fail closed,
- `tolerant` replay paths that hide gaps or warnings,
- helper indexes being treated as source of truth,
- repair behavior that rewrites canonical history too broadly,
- example, CLI, packaging, or documentation content that exposes secrets or unsafe defaults,
- dependency, workflow, or build-process issues that weaken the local trust boundary.

## Disclosure Process

After a report is received, the maintainers will aim to:

1. acknowledge receipt,
2. validate the report,
3. prepare a fix or mitigation,
4. add regression coverage when appropriate,
5. document the change in release notes or related documentation when appropriate.

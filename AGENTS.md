# AGENTS.md

Scope: applies to the entire repository unless a deeper `AGENTS.md` overrides it.

---

# Project Intent

This repository is for creating, maintaining, testing, and publishing **AI Agent Skills**: portable packages of instructions, scripts, templates, and reference resources that give AI agents specialized capabilities.

The highest priorities are:

- correct and reproducible skill behavior,
- portable skill packages that follow the open Agent Skills pattern,
- concise instructions that load only the context needed for the task,
- safe and auditable script execution,
- maintainable documentation and examples.

Fast iteration is encouraged, but not at the expense of portability, reviewability, safety, or clear user-facing behavior.

---

# Core Skill Authoring Principles

## Skills are reusable workflows, not giant prompts

Create a skill when a task is repeatable and benefits from a consistent playbook, such as:

- a multi-step workflow,
- a recurring analysis pattern,
- a formatting or reporting standard,
- a domain-specific interpretation guide,
- a tool-assisted process with predictable inputs and outputs.

Do **not** create one massive skill that tries to cover an entire project or department. Prefer small, composable skills that can be loaded independently and combined by the agent when useful.

## Use progressive disclosure

Every skill must follow progressive disclosure:

1. **Advertise** through the skill `name` and `description`.
2. **Load** the `SKILL.md` only when the task matches the skill.
3. **Read resources** only when needed.
4. **Run scripts** only when needed and safe.

Keep the default loaded content small. Put detailed reference material, schemas, templates, long examples, and policies in separate files under `references/`, `assets/`, `examples/`, or `scripts/`.

## Skill instructions must be operational

A skill should tell the agent exactly how to perform the task. Include:

- when to use the skill,
- required and optional inputs,
- assumptions to check,
- step-by-step workflow,
- tool or script usage rules,
- output format,
- quality checks,
- refusal or escalation conditions,
- examples for realistic usage.

Avoid vague statements such as “do a good job,” “analyze carefully,” or “use best practices” unless they are followed by concrete, testable criteria.

---

# Required Skill Directory Structure

Use this default layout for file-based skills:

```text
skill-name/
├── SKILL.md                  # Required: frontmatter + concise operational instructions
├── references/               # Optional: policies, methods, schemas, lookup tables, long docs
├── assets/                   # Optional: templates, static examples, style guides, prompts
├── examples/                 # Optional: realistic input/output examples and test cases
├── scripts/                  # Optional: executable utilities used by the skill
├── tests/                    # Optional but recommended: skill evaluation cases and script tests
└── README.md                 # Optional for complex skills; explains package maintenance/use
```

Directory names should be lowercase, hyphen-separated, and stable. Avoid spaces, uppercase letters, and ambiguous abbreviations.

A skill directory must contain exactly one `SKILL.md` file.

---

# `SKILL.md` Requirements

Every skill must include YAML frontmatter followed by Markdown instructions.

## Required frontmatter

```yaml
---
name: skill-name
description: Clear description of what the skill does and when to use it.
---
```

## Recommended frontmatter

```yaml
---
name: skill-name
description: Clear description of what the skill does and when to use it. Include trigger keywords users are likely to say.
license: Apache-2.0
compatibility: Requires python3 and local filesystem access. No network access required.
metadata:
  author: team-or-owner
  version: "0.1.0"
  status: draft
  last_reviewed: "YYYY-MM-DD"
allowed-tools: shell python
---
```

## Frontmatter rules

- `name` must match the parent directory name.
- `name` must use lowercase letters, numbers, and hyphens only.
- `name` must not start or end with a hyphen.
- `name` must not contain consecutive hyphens.
- Keep `name` under 64 characters.
- `description` must explain both:
  - what the skill does,
  - when the agent should use it.
- Keep `description` under 1024 characters.
- Include practical trigger terms in `description`, because agents often decide whether to load a skill from the name and description alone.
- Do not overpromise capabilities in `description`.
- Use `compatibility` for environment requirements such as Python, R, shell, network access, OS assumptions, external binaries, or model/platform limitations.
- Use `metadata.version` and update it for meaningful skill changes.

## `SKILL.md` body length

Keep `SKILL.md` under 500 lines.

If the body is becoming long, move content into directly linked files such as:

- `references/methods.md`
- `references/schema.md`
- `assets/report-template.md`
- `examples/example-input.md`
- `examples/example-output.md`

---

# Standard `SKILL.md` Template

Use this structure unless there is a strong reason not to:

```markdown
---
name: skill-name
description: One or two sentences describing what this skill does and when to use it.
license: Apache-2.0
compatibility: Requires python3. No network access required.
metadata:
  author: owner-or-team
  version: "0.1.0"
  status: draft
---

# Skill Name

## Purpose

State the job-to-be-done in one short paragraph.

## When to Use

Use this skill when the user asks to ...

## When Not to Use

Do not use this skill when ...

## Required Inputs

- `input_name`: description, accepted format, constraints.

## Optional Inputs

- `option_name`: description and default.

## Workflow

1. Validate the available inputs.
2. Read only the needed resources.
3. Ensure the persistent skill environment exists (`bash scripts/ensure_env.sh` once, or rely on Python script auto-bootstrap via `scripts/skill_env.py`).
4. Prepare the run directory, manifest, `agent_request.txt`, and `agent_workflow.md` (see [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail)).
5. Run only the needed scripts; pass `--runId`, `--agentRequestFile`, and `--agentWorkflowFile` (or equivalents).
6. Produce the requested output.
7. Verify the reproducibility bundle (`run_metadata.json`, `logs/`, deliverables) and perform final quality checks.

## Resources

- `references/file.md`: when to read it.
- `assets/template.md`: when to use it.

## Scripts

- `scripts/ensure_env.sh`: create/reuse persistent environment under `~/.cache/cursor-skills/<skill-name>/`.
- `scripts/skill_env.py`: Python bootstrap (re-exec with cached interpreter when needed).
- `scripts/run_with_skill_env.sh`: run any command inside the cached environment.
- `scripts/tool.py`: what it does, accepted arguments, expected output, and safety constraints.

## Output Format

Describe the exact structure, headings, tables, filenames, or machine-readable schema expected.

## Reproducibility and documentation (CRITICAL)

Every skill run that writes derived artifacts must leave a complete audit trail under the run directory (see [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail)):

1. **`run_metadata.json`** — written by the script: UTC run ID, exact command, resolved inputs, parameters, tool versions, summary statistics, and output paths.
2. **`logs/<scriptName>.log`** — full script execution log (never the working directory).
3. **`logs/commands.log`** — append-only record of executed CLI commands.
4. **`agent_request.txt`** — verbatim user prompt.
5. **`agent_workflow.md`** — agent-produced steps: inspection, mapping, harmonization, manifest creation, CLI invocation.
6. **Optional agent-prepared artifacts** — e.g. `column_renames.tsv`, `prepared/*`, input manifests.

In the summary to the user, list the run directory, key deliverables, parameters used, and method + versions from `run_metadata.json`.

## Quality Checks

Before finishing, verify:

- required inputs were handled,
- assumptions were stated,
- output follows the requested format,
- no unavailable resources or tools were claimed,
- any scripts used produced expected outputs,
- `run_metadata.json` and `logs/<scriptName>.log` exist in the run directory,
- no WARNING/ERROR entries in the script log (unless documented and expected).

## Failure and Escalation

If required inputs are missing, ask only the minimum necessary question or provide a best-effort partial result when appropriate.
If the task is unsafe, impossible, or outside the skill scope, explain why and suggest a safer alternative.
```

---

# Description Quality Standard

The `description` is the most important field for automatic skill triggering.

A good description:

- is specific,
- names the task domain,
- includes common user phrasing and keywords,
- says when to use the skill,
- avoids broad claims.

Bad:

```yaml
description: Helps with reports.
```

Good:

```yaml
description: Create a monthly scientific project status report from notes, metrics, and action items. Use when asked to summarize project progress, risks, blockers, milestones, or next steps in a structured report.
```

Bad:

```yaml
description: Does bioinformatics.
```

Good:

```yaml
description: Review NGS quality-control tables and produce a structured sample-level QC summary. Use for RNA-seq, ATAC-seq, ChIP-seq, EM-seq, or similar sequencing QC metrics when the user asks whether samples pass, fail, or need investigation.
```

---

# Progressive Disclosure Rules

## Keep reference files one level deep

Reference files should be linked directly from `SKILL.md`.

Prefer:

```text
SKILL.md -> references/schema.md
SKILL.md -> references/policy.md
SKILL.md -> examples/pass-case.md
```

Avoid:

```text
SKILL.md -> references/index.md -> references/details/nested/file.md
```

Deep nesting increases the chance that agents only partially inspect the needed material.

## Add tables of contents to long resources

Any reference file longer than about 100 lines must start with a short table of contents.

Example:

```markdown
# Method Reference

## Contents

- Input requirements
- Normalization logic
- Output schema
- Interpretation rules
- Common edge cases
- Worked examples
```

## Do not duplicate long content

Keep short summaries in `SKILL.md` and detailed content in resources. Avoid copying the same long policy, schema, or template into multiple places.

## Avoid time-sensitive facts in skill instructions

Do not hardcode changing facts such as current prices, current regulations, current software versions, current staff lists, or current deadlines unless they are explicitly part of a versioned reference file.

When time-sensitive information is unavoidable:

- mark it with `last_reviewed`,
- include the source or owner,
- place it in a reference file,
- state when the agent should verify it externally.

---

# Resource File Standards

Resources under `references/`, `assets/`, and `examples/` must be directly useful to the agent.

## `references/`

Use for explanatory or authoritative material:

- policies,
- scientific rationale,
- schemas,
- terminology,
- validation criteria,
- method details,
- edge cases.

Reference files should be concise, structured, and easy to scan.

## `assets/`

Use for reusable static artifacts:

- report templates,
- email templates,
- prompt templates,
- style guides,
- output skeletons,
- example configuration files.

Do not put executable logic in `assets/`.

## `examples/`

Use for realistic examples:

- example inputs,
- expected outputs,
- good and bad cases,
- evaluation prompts,
- regression test cases.

Examples should be concrete. Avoid toy placeholders unless the skill is intentionally generic.

---

# Script Standards for Skills

Scripts are optional. Add scripts only when they make the skill more reliable, testable, or efficient.

Good uses of scripts:

- deterministic parsing,
- schema validation,
- format conversion,
- numeric calculations,
- report assembly,
- data extraction,
- reproducible plots,
- file inventory or metadata checks.

Poor uses of scripts:

- scripts that simply call the model again,
- scripts that hide important logic from review,
- scripts that require undocumented dependencies,
- scripts that mutate user data without explicit approval,
- scripts that perform broad network or filesystem access by default.

## Script location and naming

- Place scripts in `scripts/`.
- Use descriptive lowercase filenames with hyphens or underscores consistently.
- Prefer Python for portable scripts unless another language is clearly better.
- Use forward-slash paths in documentation and examples.

## Script interface

Every script must have a clear command-line interface.

For Python scripts:

- use `argparse` for CLI arguments,
- include `--help`,
- validate inputs before processing,
- return non-zero exit codes on failure,
- write machine-readable outputs when possible,
- write diagnostics to stderr or logs,
- avoid interactive prompts unless explicitly required.

## Script documentation

Every script must be documented in `SKILL.md` or a directly linked reference file with:

- purpose,
- accepted arguments,
- expected outputs,
- dependencies,
- side effects,
- safety restrictions,
- example invocation,
- reproducibility flags (`--runId`, `--outputDir`, `--agentRequestFile`, `--agentWorkflowFile`) when the script writes derived artifacts.

## Script logging and reproducibility CLI

Scripts that write derived artifacts must implement the [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail) contract:

- configure Python `logging` to write a plain-text log under `<outputDir>/logs/<scriptName>.log` (never default to the working directory),
- accept `--outputDir` (default: parent directory of the output prefix/path),
- accept `--runId` (default: generate `YYYYMMDDTHHMMSSZ` at execution time),
- accept `--agentRequest` / `--agentRequestFile` and `--agentWorkflow` / `--agentWorkflowFile` (or a skill-specific env var fallback),
- append the exact CLI invocation to `logs/commands.log` at run start,
- write `run_metadata.json` at run end with resolved tool versions, inputs, parameters, summary, outputs, and log paths,
- log run ID, command, working directory, output directory, and tool versions at startup,
- return non-zero exit codes on failure.

Implement these helpers in each skill script (or a shared utility module if the repository provides one): `configureLogging`, `runIdUtc`, `appendCommandLog`, `collectToolVersions`, `writeRunMetadata`, and a `reproducibility` argparse group. See [Worked example](#worked-example-optional) for one conforming skill in this repository.

## Script safety

Scripts must be treated like third-party code.

- Do not run unreviewed scripts.
- Do not execute scripts from untrusted skills.
- Prefer sandboxed execution for scripts with filesystem, network, or system-level access.
- Require explicit user approval before destructive or high-impact operations.
- Validate all paths and inputs.
- Do not read secrets unless the skill explicitly requires them and the user has approved.
- Do not exfiltrate data.
- Do not modify agent, platform, shell, or credential configuration files unless explicitly requested.

## Script dependency policy

If a script requires dependencies:

- list them in `compatibility`, `README.md`, and a declarative dependency file (`requirements.txt`, `environment.yml`, or equivalent),
- provide a **persistent reusable environment** via `scripts/ensure_env.sh` (see [Persistent Reusable Skill Environments](#persistent-reusable-skill-environments)) — do **not** recreate the environment on every skill run,
- avoid unnecessary heavyweight dependencies,
- pin versions when reproducibility matters,
- include a small smoke test.

---

# Skill Safety and Security

Treat every skill as executable operational guidance that can influence agent behavior.

Before accepting, installing, sharing, or publishing a skill, review:

- `SKILL.md`,
- all resource files,
- all scripts,
- dependency files,
- example files that may contain hidden instructions,
- templates that may inject unsafe behavior.

Check for:

- prompt injection,
- attempts to bypass system or developer instructions,
- attempts to exfiltrate secrets or private data,
- hidden instructions in examples or templates,
- unnecessary network access,
- broad filesystem reads,
- destructive commands,
- suspicious encoded payloads,
- typosquatted names,
- unclear provenance.

## Secrets

- Never commit secrets, tokens, API keys, passwords, private certificates, or credentials.
- Secrets must come from environment variables or approved secret stores.
- Example files must use fake placeholder values.
- Do not include real user data in skill packages unless explicitly approved and sanitized.

## Data mutation safety

Do not delete, move, overwrite, sync, or bulk-modify user data unless the user explicitly asks for that operation.

Before any command equivalent to `rm`, `mv`, `cp`, `rsync`, bulk rename, database write, or API write, the agent must confirm that the action is intended unless the user’s instruction is already explicit and unambiguous.

Prefer dry-run modes for destructive or broad operations.

---

# Skills vs Workflows

Use a skill when:

- the AI should adaptively decide how to apply a playbook,
- the task is focused and domain-specific,
- operations are low-risk or idempotent,
- failure can be retried safely,
- the agent benefits from reusable context and examples.

Use a deterministic workflow, pipeline, or application code instead when:

- exact step order must be guaranteed,
- the task has high-impact side effects,
- checkpointing and resumability are required,
- multiple systems or approvals must be coordinated,
- repeated execution after failure would be costly or unsafe.

When in doubt, keep the skill as a thin instruction layer and move deterministic, high-stakes logic into reviewed code or a formal workflow.

---

# Skill Evaluation and Testing

Every non-trivial skill should include evaluation examples.

Minimum recommended evaluation set:

- one standard successful case,
- one edge case,
- one missing-input or ambiguity case,
- one misuse or out-of-scope case,
- one adversarial or prompt-injection case when the skill handles external content.

For each evaluation, record:

- user request,
- available inputs,
- expected behavior,
- expected output structure,
- unacceptable behavior,
- required resources or scripts.

Store evaluations under `examples/` or `tests/`.

## Testing checklist

Before considering a skill complete, verify:

- the skill triggers from realistic user language,
- the skill does not trigger for unrelated tasks,
- `SKILL.md` stays concise,
- all referenced resources exist,
- long resources have tables of contents,
- scripts run with `--help`,
- script errors are actionable,
- output format matches the skill instructions,
- edge cases are handled,
- safety boundaries are respected.

---

# Documentation Requirements

Documentation is part of the skill package, not an optional add-on.

Documentation must stay synchronized with skill behavior.

Update documentation in the same change whenever you modify:

- skill name,
- skill description,
- when-to-use criteria,
- workflow steps,
- required or optional inputs,
- output format,
- resources,
- scripts,
- dependencies,
- safety boundaries,
- examples,
- evaluation cases,
- version metadata.

## Skill-level README

A complex skill should include a `README.md` in the skill directory.

The README should include:

- purpose,
- installation or packaging notes,
- directory structure,
- required environment,
- examples of use,
- testing instructions,
- changelog or link to changelog,
- owner or maintainer.

Do not duplicate the entire `SKILL.md` in the README. Explain how to maintain and test the package.

## Repository-level documentation

Maintain repository documentation for:

- skill authoring standards,
- packaging and release process,
- test/evaluation process,
- security review process,
- compatibility targets,
- examples of accepted skill structures.

For larger repositories, prefer:

```text
docs/
├── overview.md
├── authoring.md
├── packaging.md
├── testing.md
├── security.md
├── release.md
├── changelog.md
└── examples.md
```

## Changelog

Maintain `docs/changelog.md` or an equivalent repository-level changelog.

Add an entry for every documentation-relevant or behavior-changing update, including:

- new skills,
- renamed skills,
- changed descriptions,
- changed workflows,
- changed outputs,
- changed scripts,
- changed dependencies,
- changed safety behavior,
- changed examples or evaluations.

Use newest-first order.

Suggested entry shape:

```markdown
## YYYY-MM-DD

- Added `skill-name` for ...
- Changed `skill-name` output format to ...
- Updated tests/examples for ...
- Migration: ...
```

---

# Engineering Standards

These standards apply to scripts, utilities, tests, and any code bundled with skills.

- Prefer small, composable functions with explicit inputs and outputs.
- Keep skill logic modular.
- Use `pathlib.Path` for filesystem paths in Python.
- Use Python `logging` for runtime diagnostics; do not use `print` for logging.
- Skill-run script logs must go under `<runDir>/logs/`; see [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail).
- Use type hints for public functions and non-trivial internals.
- Use Google-style docstrings for public functions, classes, and modules.
- Keep import-time side effects minimal.
- Do not edit vendored code in `vendor/` unless explicitly requested.
- Use clear error messages that explain the expected input and what was actually found.
- Do not add workaround behavior solely to make smoke tests pass.

## Function naming

- Function names must start with letters.
- Do not prefix function names with `_`, including internal helpers.
- Prefer descriptive names over abbreviations.

## CLI flags

- Flags should use `camelCase` style unless a platform or existing tool convention requires otherwise.
- Keep CLI flag names stable after release.
- Document defaults and units.

---

# Google-Style Docstring Standard

Every public function, class, and module must have a documentation-quality docstring.

Every function or method docstring must start with a one-line summary sentence ending with a period.

Use these headers when applicable:

- `Args:`
- `Returns:`
- `Raises:`

In `Args`, document each parameter as:

```text
name (type): Description.
```

In `Returns`, document the return type and meaning.

Use `Returns: None.` only when truly no value is returned.

In `Raises`, document expected error types and the condition that triggers each.

For scientific or quantitative code, include:

- units,
- scale semantics,
- array or tensor shapes,
- coordinate conventions,
- normalization assumptions.

Shape notation must be explicit, for example:

```text
x: [batch, genes, tracks]
```

Keep docstrings synchronized with implementation.

---

# Scientific and Analytical Skill Requirements

For skills that perform scientific, clinical, regulatory, financial, statistical, or other high-stakes analysis:

- state the intended scope,
- state assumptions,
- identify required inputs,
- document units and coordinate systems,
- distinguish raw values from normalized values,
- explain thresholds and their source,
- avoid unsupported claims,
- include uncertainty and limitations,
- require citations or references when the skill produces factual claims,
- fail fast on malformed or insufficient inputs.

Complex scientific, mathematical, or logical transformations must include explanatory comments or reference documentation explaining both:

- what transformation is applied,
- why it is scientifically, statistically, or numerically required.

---

# Numerical Stability and Non-Finite Policy

Treat `NaN`, `Inf`, and invalid numeric values as hard error conditions unless a skill explicitly documents another behavior.

Fail fast with an error that identifies:

- variable or artifact where non-finite values were detected,
- operation or stage where detection occurred,
- recommended fix or diagnostic step.

Do not silently coerce non-finite values to `0`, drop them, or continue processing.

---

# Reproducibility Rules

Skills that produce derived artifacts must support reproducibility.

Do not overwrite canonical raw inputs in place.

Write derived artifacts under explicit output directories.

Persist or report, when applicable:

- skill name,
- skill version,
- run ID,
- timestamp in UTC,
- input file paths,
- key parameters,
- random seeds,
- script versions,
- dependency versions,
- output paths,
- warnings and assumptions.

## Run ID policy

Analysis, training, optimization, conversion, and reporting scripts that write derived artifacts must assign a run ID for each execution.

Run IDs must be timestamp-based in UTC using:

```text
YYYYMMDDTHHMMSSZ
```

Prefer run-scoped output directories:

```text
<outputRoot>/<runId>/
```

If a script supports user-provided run IDs, still record the execution timestamp in metadata.

Do not overwrite an existing run directory unless an explicit overwrite flag is provided.

For the full run-directory layout, agent vs script responsibilities, `run_metadata.json` schema, and `SKILL.md` workflow steps, see [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail).

---

# Skill Run Logging and Audit Trail

Skills that produce derived artifacts must leave a **complete, inspectable audit trail** for every execution. The contract below is skill-agnostic; any skill with scripts that write derived artifacts should follow it regardless of domain.

This is a **contract between three parties**:

1. **The agent** — prepares inputs, documents reasoning, invokes the script with reproducibility flags, verifies outputs.
2. **The skill script** — writes machine-readable metadata, structured logs, and primary deliverables.
3. **The skill author** — documents the contract in `SKILL.md`, implements it in scripts, and lists it in quality checks.

## Run directory layout

Each execution gets its own run-scoped directory. Primary deliverables live at the run root; diagnostics live under `logs/`.

```text
<outputRoot>/<skill-name>-<YYYYMMDDTHHMMSSZ>/
├── <outputPrefix>.<artifact>.png          # primary deliverables (figures, tables, etc.)
├── <outputPrefix>.<artifact>.pdf
├── input_manifest.tsv                     # agent-prepared inputs (when applicable)
├── run_metadata.json                      # script-written reproducibility record
├── agent_request.txt                      # verbatim user prompt
├── agent_workflow.md                      # agent-produced workflow notes
├── column_renames.tsv                     # optional: harmonization record
├── prepared/                              # optional: harmonized input copies
└── logs/
    ├── <scriptName>.log                   # full execution log
    └── commands.log                       # append-only CLI command record
```

### Naming rules

| Element | Convention | Example |
|---------|------------|---------|
| Run directory | `<skill-name>-<YYYYMMDDTHHMMSSZ>` | `pathway-enrichment-20260709T125435Z` |
| Run ID | UTC `YYYYMMDDTHHMMSSZ` | `20260709T125435Z` |
| Output prefix | User-requested or descriptive; no extension | `20260709`, `my_analysis_run` |
| Script log | `logs/<scriptBasename>.log` | `logs/run_analysis.log` |
| Commands log | `logs/commands.log` | always this name |

**Never** write skill-run logs to the working directory, skill package root, or repository root. Logs belong in `<runDir>/logs/`.

### Output root placement

When a Cursor agent executes a skill, deposit run directories under repository-local **`agentResults/`**:

```text
agentResults/<optional-grouping>/<skill-name>-<YYYYMMDDTHHMMSSZ>/
```

Point `--outputDir` (or equivalent) at the run directory. The output prefix may be a basename inside that directory (e.g. `agentResults/<skill-name>-<runId>/<outputPrefix>`).

## Agent responsibilities (SKILL.md workflow)

Document these steps in every skill that writes derived artifacts. The agent must:

1. **Create the run directory** before executing (`agentResults/<skill-name>-<runId>/`).
2. **Inventory and validate inputs** — confirm paths exist; read headers/schemas only as needed.
3. **Prepare agent artifacts**:
   - `agent_request.txt` — copy the verbatim user prompt.
   - `agent_workflow.md` — document inspection, column/field mapping, harmonization decisions, manifest creation, and the exact CLI to run.
   - Optional: `input_manifest.tsv`, `column_renames.tsv`, `prepared/*` when inputs need normalization.
4. **Invoke the script** with reproducibility flags:
   - `--runId <YYYYMMDDTHHMMSSZ>`
   - `--agentRequestFile <path-to-agent_request.txt>` (or `--agentRequest` inline)
   - `--agentWorkflowFile <path-to-agent_workflow.md>` (or `--agentWorkflow` inline)
   - `--outputDir <runDir>` when the output prefix alone does not imply the run directory
5. **Verify success**:
   - exit code `0`,
   - expected deliverables exist,
   - `run_metadata.json` and `logs/<scriptName>.log` exist,
   - scan the script log for `WARNING` / `ERROR` / `CRITICAL`.
6. **Report to the user**: run directory, key deliverable paths, parameters/thresholds used, column mapping or harmonization summary, and tool versions from `run_metadata.json`.

### `agent_workflow.md` content standard

At minimum, include:

- input inventory (paths, formats, identifier types),
- column or field mapping per input file,
- harmonization steps and paths to `column_renames.tsv` / `prepared/*` when performed,
- manifest or configuration file path,
- exact CLI command (copy-pasteable),
- parameters chosen and why (especially when matching a prior run).

### `agent_request.txt`

Always the **verbatim** user prompt for the run. Do not paraphrase. The script copies or writes this into the run directory for audit.

## Script responsibilities

Every script that writes derived artifacts must implement the following.

### Logging configuration

- Use Python `logging`; do not use `print` for diagnostics.
- Configure **two handlers**:
  - **Console** — human-readable, optionally colorized for interactive runs.
  - **File** — plain text at `<outputDir>/logs/<scriptName>.log`.
- Create parent directories before opening the log file.
- Use a consistent file format, for example:

```text
###	[2026-07-09 07:55:48,088] <scriptName>.py:1393: main INFO: Run ID: 20260709T125435Z
```

- At run start, log: run ID, full command, working directory, output directory, resolved tool versions.
- At run end, log completion or failure with actionable messages.

### Reproducibility CLI flags

Add an `argparse` argument group named `reproducibility` (or equivalent) with at least:

| Flag | Purpose |
|------|---------|
| `--outputDir` | Directory for `run_metadata.json`, `agent_request.txt`, `agent_workflow.md`, and `logs/`. Default: parent of output prefix/path. |
| `--runId` | UTC run ID (`YYYYMMDDTHHMMSSZ`). Default: generate at execution. |
| `--agentRequest` | Inline verbatim user request. |
| `--agentRequestFile` | Path to user request file (written/copied as `agent_request.txt`). |
| `--agentWorkflow` | Inline markdown workflow notes. |
| `--agentWorkflowFile` | Path to workflow file (copied as `agent_workflow.md`). |

Optional: environment-variable fallback (e.g. `<SKILL_NAME>_AGENT_REQUEST` in uppercase with hyphens replaced by underscores) for CI or headless wrappers.

### `logs/commands.log`

At run start, **append** one block per execution:

```text
[2026-07-09T12:55:48.088000+00:00] run_id=20260709T125435Z
python scripts/<scriptName>.py <inputs...> <outputPrefix> --runId 20260709T125435Z ...

```

Use append mode so re-runs or debugging sessions preserve history within the same run directory.

### `run_metadata.json`

Write at run end (or atomically on success). Minimum schema:

```json
{
  "skill": "skill-name",
  "script": "script_name.py",
  "run_id": "YYYYMMDDTHHMMSSZ",
  "timestamp_utc": "ISO-8601",
  "command": "exact CLI with quoted arguments",
  "working_directory": "/path/at/execution",
  "inputs": [],
  "output_directory": "/path/to/runDir",
  "output_prefix": "/path/to/runDir/prefix",
  "parameters": {},
  "tool_versions": {},
  "summary": {},
  "outputs": [],
  "agent_request_file": "/path/to/agent_request.txt",
  "agent_workflow_file": "/path/to/agent_workflow.md",
  "logs": {
    "<scriptName>.log": "/path/to/logs/<scriptName>.log",
    "commands.log": "/path/to/logs/commands.log"
  },
  "attribution": {
    "method": "short description of what the script does",
    "skill_package": "package name and version if known",
    "note": "what the agent did vs what the script did"
  }
}
```

Field guidance:

| Field | Required | Notes |
|-------|----------|-------|
| `skill` | yes | Must match skill `name` / directory |
| `run_id` | yes | Same value passed to `--runId` |
| `command` | yes | Reconstruct from `sys.argv` with proper quoting |
| `inputs` | yes | Resolved paths and labels; empty list if N/A |
| `parameters` | yes | All CLI flags that affect output |
| `tool_versions` | yes | **Resolved** versions (Python, key libraries, script path) — not just requested ranges |
| `summary` | when applicable | Per-panel counts, row totals, QC pass/fail, etc. |
| `outputs` | yes | Only paths that actually exist after the run |
| `logs` | yes | Absolute paths to both log files |

Use `json.dumps(..., indent=2)` and UTF-8 encoding.

### Tool version collection

Collect at runtime, for example:

```python
{
    "python": sys.version.split()[0],
    "python_full": sys.version.replace("\n", " "),
    "pandas": pd.__version__,
    "numpy": np.__version__,
    "script": Path(__file__).resolve().as_posix(),
}
```

Extend for domain-specific dependencies (R packages, CLI tool `--version` output, etc.).

## SKILL.md requirements for logging

Every skill with scripts that write artifacts must include in `SKILL.md`:

1. A **Reproducibility and documentation (CRITICAL)** section listing every file in the audit trail.
2. Workflow step(s) for creating `agent_request.txt` and `agent_workflow.md` before script execution.
3. Workflow step(s) for passing `--runId`, `--agentRequestFile`, `--agentWorkflowFile`.
4. Quality checks that verify `run_metadata.json`, log files, and deliverables.
5. A reference doc (under `references/`) describing output layout and `run_metadata.json` fields when non-trivial.

Keep the `SKILL.md` summary concise; put the full directory tree and schema tables in `references/`.

## Optional harmonization artifacts

When the agent normalizes inputs before calling the script, also write:

| File | Purpose |
|------|---------|
| `column_renames.tsv` | Per-file mapping: original column → canonical column |
| `prepared/*.tsv` (or equivalent) | Harmonized copies used for the run |

Reference these paths in `agent_workflow.md` and, when useful, in `run_metadata.json` under `inputs` or a `prepared_inputs` field.

## User-facing report template

When finishing a skill run, the agent summary should include:

- **Run directory** (absolute path),
- **Key deliverables** (figures, tables, exports),
- **Parameters** (thresholds, column mapping, layout),
- **Summary statistics** from `run_metadata.json` (e.g. up/down counts per panel),
- **Tool versions** from `run_metadata.json`,
- **Pointer** to `run_metadata.json` for full reproducibility.

## Anti-patterns (do not do this)

- Writing `script.log` next to the script or in the current working directory.
- Overwriting prior run directories without an explicit `--overwrite` flag.
- Paraphrasing the user request in `agent_request.txt`.
- Skipping `agent_workflow.md` because "the command is obvious".
- Recording only requested dependency ranges in metadata instead of resolved versions.
- Reporting success without checking that `run_metadata.json` and log files exist.
- Mixing disposable scratch files with run deliverables in the same directory without a `logs/` subfolder.

## Worked example (optional)

One skill in this repository already follows the contract above end-to-end. Use it as a **concrete illustration** when implementing logging for a new skill — not as a required dependency or canonical template:

| Skill (example) | Useful patterns |
|-----------------|-----------------|
| `volcano-grid-plot/scripts/volcano_ma_grid.py` | `configure_logging`, `runIdUtc`, `appendCommandLog`, `collectToolVersions`, `writeRunMetadata`, reproducibility argparse group |
| `volcano-grid-plot/SKILL.md` | Reproducibility workflow steps and quality checks |
| `volcano-grid-plot/references/input-manifest-and-layout.md` | Run directory tree and `run_metadata.json` field table |

New skills should implement the same **behaviors** (run directory layout, metadata schema, log placement) with their own script names, input manifests, and reference docs.

---

# Input Validation and Failure Behavior

Fail fast on missing or malformed inputs.

Error messages must include:

- expected path, schema, format, or value range,
- what was actually found,
- which skill step failed,
- how to fix or inspect the issue.

Do not silently fall back to alternate files, formats, inferred defaults, or guessed schemas for critical inputs.

If a user request lacks required inputs, ask the minimum necessary clarifying question unless a safe partial result is possible.

---

# Packaging and Portability

Skill packages must be portable across compatible agent environments.

Before release, verify:

- directory name matches `name`,
- exactly one `SKILL.md` exists,
- YAML frontmatter is valid,
- referenced resources exist,
- scripts are executable or have documented invocation commands,
- dependencies are documented,
- a declarative environment file (`environment.yml` and/or `requirements.txt`) exists, pins the interpreter range where required, and matches `compatibility` and the README,
- `scripts/ensure_env.sh` exists for skills with non-stdlib dependencies and creates/reuses a cache under `~/.cache/cursor-skills/<skill-name>/` (not inside the repo),
- Python CLI scripts call `skill_env.bootstrap()` or are invoked via `run_with_skill_env.sh`,
- the documented setup command was validated in a clean cached environment (or the reason it was not is stated),
- file paths use forward slashes,
- package contains no secrets,
- package contains no unnecessary large files,
- generated artifacts are excluded unless intentionally part of the skill,
- examples are sanitized,
- license information is present when needed.

Avoid assumptions about:

- current working directory,
- operating system,
- installed tools,
- internet access,
- credentials,
- GPU availability,
- writable system directories.

State environment requirements explicitly in `compatibility` and README documentation.

---

# Environment Setup and Dependency Reproducibility

A skill only works "seamlessly for all users" if a fresh agent on a clean machine can build the exact runtime the skill was validated against. Vague instructions like "install intervene" or "needs Python 3.9+" are a common failure source: the agent picks the newest interpreter, a transitive dependency breaks, and the user hits a cryptic crash. Treat the environment as a first-class, versioned deliverable of the skill.

Skills with non-stdlib dependencies must use a **persistent reusable environment** (see [Persistent Reusable Skill Environments](#persistent-reusable-skill-environments)). Do **not** run `conda env create`, `python -m venv`, or equivalent on every skill invocation.

## Ship a declarative environment file

Any skill that depends on external binaries or non-stdlib packages must include a machine-readable environment specification, not just prose:

- For skills that need **system/scientific binaries** (bioinformatics tools, compilers, `bedtools`, `samtools`, `R`, etc.), prefer a Conda/Mamba `environment.yml` that installs both the binaries and the Python packages from `conda-forge`/`bioconda`. This is the most portable option across macOS (Intel + Apple Silicon) and Linux.
- For **pure-Python** skills, a `requirements.txt` (and/or `pyproject.toml`) is sufficient, but still document the required interpreter version.
- Keep `environment.yml`, `requirements.txt`, `compatibility`, and the README install section **mutually consistent**. If they disagree, users will follow the wrong one.

## Pin the interpreter and constrain versions with a stated reason

- Pin the **interpreter version range** whenever any dependency constrains it. Do not write an open-ended `python>=X` when a tool actually breaks on newer interpreters.
- When you pin or cap a version, add an inline comment explaining **why**, so a future maintainer can safely relax it later. Example (real case from `genomic-set-analysis`): Intervene 0.6.4 does `from collections import Iterable`, which was removed in Python 3.10, so the env must pin `python<3.10`.
- Pin versions of anything where a silent upgrade would change scientific output or break the run. Leave genuinely flexible dependencies unpinned to avoid needless conflicts.
- Avoid architecture-specific assumptions. Prefer package sources that publish builds for `osx-64`, `osx-arm64`, and `linux-64`. If a required tool lacks a build for a common architecture, document that limitation and the fallback (e.g. `CONDA_SUBDIR=osx-64` under Rosetta, a container, or an alternative tool).

## Make setup a first-class, idempotent step

- Provide **one canonical setup command** that creates the environment only when missing, e.g. `bash scripts/ensure_env.sh`. Put it in the README **and** as an explicit early step in the `SKILL.md` workflow (a "Persistent runtime environment" or "Step 0 — set up the environment" section) so the agent runs it before attempting analysis.
- On later runs, **reuse** the cached environment. Do not recreate it unless the dependency spec changed, the user requests a rebuild, or the cache is corrupted.
- Do not assume a specific Conda base path, a pre-activated environment, or that the user's default `python` is correct. Scripts must bootstrap via the helper or shell wrapper.
- Do not hardcode machine-specific absolute paths in setup instructions.

## Validate on a clean environment, not your own

- "Works on my machine" is not acceptance. Before marking a skill done, verify the documented setup command in a **freshly created cached environment** (or state explicitly that you could not and why). The developer's pre-existing environment often hides missing pins and undeclared dependencies.
- Include a **post-install verification/smoke step** that surfaces version incompatibilities immediately: import the key packages, run each script's `--help`, and run the smallest bundled example end to end. Import/`--help` checks alone will miss runtime-only breakages (the Intervene `Iterable` crash only appeared when the tool actually ran).

## Record and document what actually ran

- Persist the **resolved** tool and dependency versions in run metadata (see [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail)), not just the requested ranges.
- Document **known environment failure modes and their fixes** in the skill's `Failure and Escalation` section, keyed by the exact error text the user will see, so the agent resolves them in one step instead of debugging blindly. Include interpreter/dependency mismatches and any writable-cache prerequisites for headless runs (e.g. setting `MPLCONFIGDIR`/font caches to writable paths for Matplotlib).
- When a step depends on a third-party tool with a known defect, make the script **degrade gracefully** for genuinely optional sub-steps (log a prominent warning, continue, still produce the primary deliverables) rather than aborting the whole run — but never mask failures of core functionality.

---

# Persistent Reusable Skill Environments

Skills that depend on non-stdlib Python packages or external binaries must **not** recreate their runtime environment on every invocation. Instead, create the environment once under the user's home directory and reuse it on all future runs.

This policy applies to every skill with scripts or CLI dependencies. Inspect the skill's dependency profile and choose the correct backend (venv vs Conda/micromamba) before implementing.

## Goal

- Create the environment **only when missing** or when the dependency spec changes.
- Reuse the same deterministic, skill-specific path on every run.
- Keep skill packages portable: no environment inside the project repo or `.cursor/skills/` tree.
- Never install skill dependencies globally.

## Canonical cache location

Store persistent environments under the user's home cache:

```text
~/.cache/cursor-skills/<skill-name>/
├── README.txt              # written by ensure_env.sh: location, rebuild instructions
├── environment.yml.sha256  # or requirements.txt.sha256 — detects spec changes
├── venv/                   # pure-Python skills (python -m venv)
└── conda-env/              # skills needing Conda/Bioconda binaries
```

| Element | Convention | Example |
|---------|------------|---------|
| Cache root | `~/.cache/cursor-skills/<skill-name>/` | `~/.cache/cursor-skills/genomic-set-analysis/` |
| venv prefix | `~/.cache/cursor-skills/<skill-name>/venv/` | pure-Python skills |
| Conda prefix | `~/.cache/cursor-skills/<skill-name>/conda-env/` | skills with bioconda/system binaries |
| Spec hash file | `<cache-root>/<spec-filename>.sha256` | `environment.yml.sha256` |

The path must be **deterministic and skill-specific**. Use the skill `name` (matching the directory name) as `<skill-name>`.

Existing skills may use an equivalent legacy root such as `~/.cache/ai-skills-env/<skill-name>/`. New and updated skills should standardize on `~/.cache/cursor-skills/`.

## Choose venv vs Conda/micromamba

| Skill needs | Backend | Spec file | Cache subdirectory |
|-------------|---------|-----------|-------------------|
| Python packages only (no bioconda/system binaries) | `python -m venv` | `requirements.txt` and/or `pyproject.toml` | `venv/` |
| Conda/Bioconda binaries (`bedtools`, `samtools`, `R`, compiled tools) **or** mixed Python + binaries | Conda-family prefix install (prefer micromamba → mamba → conda) | `environment.yml` | `conda-env/` |

**Do not** use a plain venv when the skill depends on binaries that venv cannot install. **Do not** install dependencies globally or inside the skill package directory.

Implementation must be portable across **Linux and macOS** (Intel and Apple Silicon where applicable).

## Required helper scripts

Every skill with external dependencies must ship these helpers under `scripts/`:

| Script | Required | Purpose |
|--------|----------|---------|
| `ensure_env.sh` | **yes** | Create/reuse the cached environment; print interpreter/prefix paths |
| `skill_env.py` | when Python CLIs exist | Bootstrap before `main()`; re-exec with cached interpreter if needed |
| `run_with_skill_env.sh` | recommended | Run any command with `PATH` and interpreter set to the cached env |

### `ensure_env.sh` contract

The helper must:

1. **Check** whether the reusable environment already exists and is valid.
2. **Create** it only when missing, corrupted, or when the dependency spec hash changed.
3. **Install** dependencies from `requirements.txt`, `environment.yml`, or the skill's canonical spec file.
4. **Expose** the correct paths via flags:
   - `--print-python` — stdout: absolute path to the skill interpreter
   - `--print-prefix` — stdout: absolute path to the environment root (`venv/` or `conda-env/`)
5. **Support** `--force-rebuild` to delete and recreate the cached environment.
6. **Fail clearly** if required host tools are missing (e.g. `python3`, `conda`, `micromamba`, `mamba`, `sha256sum`/`shasum`).
7. **Document** in header comments:
   - where the environment is stored,
   - how to force a rebuild,
   - which backend (venv vs Conda) was chosen and why.

Recommended validation inside `ensure_env.sh`:

- Verify the interpreter exists and is executable after creation.
- For Conda skills, verify required CLI binaries exist in `<prefix>/bin/` (e.g. `intervene`, `bedtools`).
- Store a SHA-256 hash of the spec file; recreate automatically when the hash differs.
- Write `~/.cache/cursor-skills/<skill-name>/README.txt` with rebuild/delete instructions.

For Conda-family backends, prefer **micromamba → mamba → conda** (in that order). Use prefix installs (`-p <prefix>`), not named conda envs in the user's base. Configure `CONDA_SOLVER=libmamba` when available to reduce memory use on HPC nodes.

### `skill_env.py` contract (Python CLIs)

When skill scripts are Python entrypoints:

- Provide `scripts/skill_env.py` with a `bootstrap()` function called at the top of each CLI script's `main()` (before other imports that depend on the env).
- `bootstrap()` runs `ensure_env.sh --print-python` and `--print-prefix`.
- If the current `sys.executable` differs from the cached interpreter, **re-exec** via `os.execve` with the cached Python.
- If already on the cached interpreter, prepend `<prefix>/bin` to `PATH` so non-Python CLIs resolve.
- Set a skill-specific `*_ENV_ACTIVE=1` env var to avoid re-exec loops.
- Expose `<SKILL_NAME>_SKIP_ENV_BOOTSTRAP=1` for pytest and intentional dev overrides.

### `run_with_skill_env.sh` contract (shell commands)

Provide a thin wrapper:

```bash
PYTHON="$(scripts/ensure_env.sh --print-python)"
PREFIX="$(scripts/ensure_env.sh --print-prefix)"
export PATH="${PREFIX}/bin:${PATH}"
exec "${PYTHON}" "$@"   # when first arg is a .py script
```

Use this for ad-hoc shell invocations or when the agent runs commands that are not Python scripts.

## Wire skill scripts to the helper

**Do not** embed `conda env create`, `pip install -r`, or `python -m venv` directly in skill workflow steps or analysis scripts.

Instead:

1. **Python CLIs** — call `bootstrap()` from `skill_env.py` at the start of `main()`:

```python
def main() -> None:
    from skill_env import bootstrap
    bootstrap()
    # ... rest of CLI
```

2. **Agent workflow** — document in `SKILL.md` that the agent runs `bash scripts/ensure_env.sh` once before the first command (or relies on auto-bootstrap when invoking Python scripts directly).

3. **Shell / mixed commands** — use `bash scripts/run_with_skill_env.sh <command> [args…]`.

4. **Tests** — set `<SKILL_NAME>_SKIP_ENV_BOOTSTRAP=1` in pytest when the test environment is pre-provisioned.

## Force a clean rebuild

Document these options in `SKILL.md`, `README.md`, and `ensure_env.sh` header comments:

```bash
bash scripts/ensure_env.sh --force-rebuild
```

or delete the cache directory:

```bash
rm -rf ~/.cache/cursor-skills/<skill-name>
```

Rebuild is required when:

- `environment.yml` or `requirements.txt` changed,
- the cached environment is corrupted,
- the user explicitly requests a clean install,
- required binaries are missing after an incomplete install.

## Documentation requirements

When implementing or updating persistent environments, update **in the same change**:

| Location | What to document |
|----------|------------------|
| `SKILL.md` `compatibility` frontmatter | Backend choice, cache path, Python version constraints |
| `SKILL.md` body | "Persistent runtime environment" section with cache path, helper commands, rebuild instructions |
| `README.md` | Setup table, canonical commands, force-rebuild, prerequisite host tools |
| `environment.yml` / `requirements.txt` | Header comment pointing to `ensure_env.sh` and cache location |
| `ensure_env.sh` header | Cache path, rebuild commands, backend rationale |
| `Failure and Escalation` | Missing conda/micromamba, OOM during env create, spec mismatch errors |

Agents must **not** run `conda env create -f environment.yml` on every skill invocation when `ensure_env.sh` exists.

## Anti-patterns (do not do this)

- Running `conda env create` or `python -m venv` on every skill run.
- Storing environments inside the project repo, `.cursor/skills/`, or `vendor/`.
- Installing skill dependencies globally (`pip install` / `conda install` without a prefix).
- Hardcoding machine-specific absolute paths to conda bases or venvs.
- Assuming the user's default `python` or `PATH` is correct.
- Skipping spec-hash checks (silent drift when `environment.yml` changes).
- Documenting "activate `<envName>`" without the persistent-cache helper when the skill ships `ensure_env.sh`.

## Worked example

The `genomic-set-analysis` skill in this repository implements the full pattern end-to-end:

| File | Pattern |
|------|---------|
| `scripts/ensure_env.sh` | Conda/micromamba prefix at `~/.cache/ai-skills-env/genomic-set-analysis/conda-env/`, spec hashing, `--force-rebuild`, readiness checks for `intervene` + `bedtools` |
| `scripts/skill_env.py` | `bootstrap()` with re-exec and `PATH` prepend |
| `scripts/run_with_skill_env.sh` | Shell wrapper for any command |
| `scripts/intervene_peaks_combine.py` (and siblings) | `bootstrap()` at start of `main()` |
| `SKILL.md` | "Persistent runtime environment (CRITICAL)" workflow section |
| `README.md` | Cache path table and setup commands |

Use it as a concrete reference when adding persistent environments to other skills. New skills should follow the same behaviors but use the canonical cache root `~/.cache/cursor-skills/<skill-name>/` unless migrating an existing cache path.

## Change summary for persistent-env work

When you add or update persistent environments for a skill, report:

- **Files changed** (helpers, wired scripts, `SKILL.md`, `README.md`, spec files),
- **Cache location** (`~/.cache/cursor-skills/<skill-name>/…`),
- **Force rebuild** command,
- **Backend choice** (venv, conda, or micromamba) and why.

---

# Versioning Policy

Use semantic versioning for maintained skills when practical:

```text
MAJOR.MINOR.PATCH
```

Increment:

- `PATCH` for clarifications, typo fixes, and non-behavioral documentation updates,
- `MINOR` for backward-compatible workflow, resource, script, or output additions,
- `MAJOR` for breaking changes to required inputs, output formats, safety behavior, or core workflow.

Update `metadata.version` in `SKILL.md` when a skill behavior changes.

For experimental skills, mark status clearly:

```yaml
metadata:
  status: experimental
```

---

# Validation Commands

Run relevant checks for touched areas.

Minimum checks for any changed skill:

```bash
python -m pytest tests
```

When a skill includes Python scripts:

```bash
python scripts/<scriptName>.py --help
python -m pytest tests/<relevantTestFile>.py
```

When changing Markdown or YAML:

```bash
python - <<'PY'
from pathlib import Path
import yaml

for path in Path('.').glob('*/SKILL.md'):
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---'):
        raise SystemExit(f'Missing frontmatter: {path}')
    _, fm, _ = text.split('---', 2)
    data = yaml.safe_load(fm)
    if data.get('name') != path.parent.name:
        raise SystemExit(f'Name mismatch: {path}')
print('SKILL.md frontmatter check passed')
PY
```

Recommended tooling direction:

- lint/format Python: `ruff`
- type checking: `mypy`
- tests: `pytest`
- YAML validation: `pyyaml` or repository-approved equivalent
- Markdown linting: repository-approved Markdown linter when available

If validation cannot be run, state why and describe the risk.

---

# Compute and Runtime Safety

- Avoid full-scale analyses, broad filesystem scans, network-heavy operations, or long-running scripts unless explicitly requested.
- Prefer small smoke tests, dry runs, subset inputs, or `--help` checks during development.
- For expensive scripts, expose and respect controls such as `--dryRun`, `--limit`, `--sampleSize`, `--maxFiles`, `--threads`, or `--timeoutSeconds`.
- Do not introduce fake success paths to make tests pass.
- Do not mask real runtime, validation, or integration failures.

---

# Plotting and Visualization Standards

If a skill or script creates plots:

- create output directories explicitly,
- save figures at 300 DPI or higher when raster output is needed,
- save vector formats when appropriate (`.pdf` or `.svg`),
- include title, x-axis label, and y-axis label unless intentionally omitted for a documented reason,
- include units and scale semantics in axis labels,
- use readable font sizes,
- use colorblind-safe palettes,
- include legends for multi-series plots,
- show uncertainty and sample size for statistical plots when applicable,
- document how the plot should be interpreted.

---

# Agent skill outputs (`agentResults/`)

When a **Cursor agent** executes a **skill** and the run produces **derived artifacts intended for the user** (exported tables, figures, logs, timestamped run folders written by skill scripts), deposit those outputs under repository-local **`agentResults/`**, not **`tmp/`**.

Typical layout:

```text
agentResults/<optional grouping>/<skill-name>-<YYYYMMDDTHHMMSSZ>/
├── <outputPrefix>.<artifact>...     # primary deliverables
├── run_metadata.json
├── agent_request.txt
├── agent_workflow.md
└── logs/
    ├── <scriptName>.log
    └── commands.log
```

Point the skill’s `--outputDir` (or equivalent) at the run directory. Follow the full contract in [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail) and [Reproducibility Rules](#reproducibility-rules).

Reserve **`tmp/`** for disposable developer-only material (scratch scripts, commit scripts, smoke-test debris), not for skill-run deliverables.

---

# `tmp/` Exception

Do not place outputs from **agent skill runs** in `tmp/`; use [`agentResults/`](#agent-skill-outputs-agentresults) instead.

Files under repository-local `tmp/` are treated as disposable development utilities.

`tmp/` scripts do not need to follow the full skill packaging, docstring, naming, typing, logging, or documentation standards.

However:

- do not put secrets in `tmp/`,
- do not use system `/tmp` for project artifacts,
- do not rely on `tmp/` files for released skill behavior,
- do not include `tmp/` scripts in skill packages unless intentionally promoted and documented.

---

# Data and Secrets

- Do not hardcode machine-specific absolute paths.
- Do not commit secrets.
- Do not commit private user data unless explicitly approved and sanitized.
- Use environment variables for secrets, for example `OPENAI_API_KEY`.
- Use repository-local `./agentResults/` for outputs produced when an agent runs skills (user-facing derived artifacts).
- Use repository-local `./tmp/` for other temporary project artifacts that are disposable development utilities, not skill deliverables.
- Do not place project temp artifacts in system `/tmp`.

---

# Commit Message Style

Subject line:

- Write a concise imperative sentence describing the commit purpose.
- Do not use prefixed styles such as `docs:`, `test(...)`, or `feat:`.

Body:

- Omit body for trivial commits.
- For non-trivial commits, include bullets with meaningful details.

Template:

```text
<Imperative purpose sentence>

- <Key behavioral or structural change>
- <Important implementation detail>
- <Any notable contract, safety, or migration impact>
```

---

# Commit Script Policy

After completing an explicit plan, create a commit script under `tmp/`.

The commit script must contain only raw `git add` and `git commit` commands.

Do not include wrappers, comments, shell functions, or scaffolding.

Follow the commit message style above.

---

# Definition of Done

A skill-authoring or skill-maintenance task is complete only when all relevant items are satisfied:

- `SKILL.md` frontmatter is valid.
- Skill directory name matches skill `name`.
- Skill `description` clearly states what the skill does and when to use it.
- `SKILL.md` is concise and uses progressive disclosure.
- Required resources are directly linked and exist.
- Long resources include a table of contents.
- Scripts are documented, validated, and safe to run.
- Dependencies and compatibility requirements are documented.
- A declarative environment file exists, pins the interpreter range where a dependency requires it (with a stated reason), and is consistent with `compatibility` and the README.
- `scripts/ensure_env.sh` (and `skill_env.py` / `run_with_skill_env.sh` when applicable) implement the [Persistent Reusable Skill Environments](#persistent-reusable-skill-environments) contract; the environment is not recreated on every run.
- The documented setup command was validated in a clean cached environment via a post-install smoke check (imports, `--help`, smallest example), or the reason it was not is stated.
- Output format is explicit.
- Safety boundaries are explicit.
- Skills with derived-artifact scripts implement the [Skill Run Logging and Audit Trail](#skill-run-logging-and-audit-trail) contract (`run_metadata.json`, `logs/`, `agent_request.txt`, `agent_workflow.md`).
- Examples or evaluations are present for non-trivial skills.
- Relevant tests or smoke checks were run, or the reason they were not run is stated.
- Documentation and changelog are updated when behavior changes.
- No secrets, private data, or unnecessary generated artifacts are included.
- Change summary includes skill behavior, safety impact, reproducibility impact, and validation performed.

---

# Self-Check Before Finishing

Before finishing any non-trivial change, verify:

- Is this better represented as a skill, a deterministic workflow, or application code?
- Does the skill have a focused job-to-be-done?
- Will the `description` trigger the skill for realistic user requests?
- Could the `description` accidentally trigger for unrelated requests?
- Is `SKILL.md` under 500 lines?
- Are detailed references moved into directly linked files?
- Are references only one level deep from `SKILL.md`?
- Do long reference files have tables of contents?
- Are scripts necessary, documented, and safe?
- Are dependencies and environment assumptions explicit?
- Is there a declarative environment file with the interpreter range pinned (and the reason noted) where a dependency requires it?
- Does the skill ship `scripts/ensure_env.sh` and reuse a cache under `~/.cache/cursor-skills/<skill-name>/` instead of recreating the env each run?
- Do Python CLI scripts bootstrap via `skill_env.py` or `run_with_skill_env.sh`?
- Did I validate the setup command in a clean cached environment and run a post-install smoke check, or state why not?
- Are known environment failure modes documented (keyed by the exact error text) in Failure and Escalation?
- Do skills with scripts write `run_metadata.json`, `logs/<scriptName>.log`, and `logs/commands.log` under the run directory (not the working directory)?
- Does `SKILL.md` document agent workflow steps for `agent_request.txt`, `agent_workflow.md`, and reproducibility CLI flags?
- Are outputs and final checks clear?
- Are missing-input and out-of-scope cases handled?
- Are examples realistic?
- Are tests or evaluations included for important behavior?
- Did I update the changelog for behavior, output, dependency, safety, or workflow changes?
- Would another maintainer understand how to review, package, test, and use this skill?

---

# Change Summary Expectations

When finishing a change, summarize:

- what changed,
- which skill or skills were affected,
- behavior or output impact,
- safety impact,
- reproducibility impact,
- documentation impact,
- for persistent-environment work: files changed, cache location, force-rebuild command, and backend choice (venv vs conda/micromamba) with rationale,
- validation commands run or why validation was not run.

Do not treat documentation, safety review, or validation as optional follow-up work.


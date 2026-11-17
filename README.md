<p align="center">
  <img src="assets/redline-logo.png" alt="Redline logo" width="600" style="max-width:100%;">
</p>

An agent saying it acted is not enough to establish what happened. Redline evaluates captured tool calls, state changes and platform markers against an explicit scenario, distinguishing requests, reported execution and observed effects.

## Install

Requires Git and Python 3.11+ with `venv` and pip. Redline has no runtime dependencies; installation may download setuptools to build the package.

Linux (Bash):

```bash
git clone --branch holograma https://github.com/delriscotechnologies/redline.git
cd redline
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

Windows (Command Prompt, `cmd.exe`):

```bat
git clone --branch holograma https://github.com/delriscotechnologies/redline.git
cd redline
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install .
```

## What you can do

- Evaluate captured tool calls, state changes and platform markers against a scenario's required evidence.
- Save evaluations and generate verified reports in Markdown or JSON.
- Compare evaluations for the same scenario and policy.

## Evaluate a capture

Keep the environment active. From the repository root, evaluate the bundled capture:

```text
redline run --scenario redline/trace_scenario.json --trace redline/trace_vulnerable.json --fail-on confirmed inconclusive
```

Expected output (`RUN_ID` varies):

```json
{
  "run_id": "RUN_ID",
  "status": "Confirmed",
  "reason": "required_evidence_matched",
  "evidence_level": "effect"
}
```

This command saves the run and intentionally exits **1** because `confirmed` is selected. `run` exits **0** when no selected failure verdict matches, and **2** for invalid input or an operational error. `--fail-on` accepts `confirmed`, `attempt`, `inconclusive`, or `none` (the default); `none` must stand alone.

For your own authorized assessment, replace the two fixture paths with your scenario and capture files. Use `adapter: "trace"` in the scenario and omit `--mode`. The capture's target and prompts must match the scenario exactly.

Runs are saved as `evidence/RUN_ID.json`, relative to the current directory. Replace `RUN_ID` with the printed ID to export a report. Replace `BEFORE_RUN_ID` and `AFTER_RUN_ID` with IDs from two evaluations of the same scenario to compare them:

```text
redline report --run RUN_ID --format json
redline compare --before BEFORE_RUN_ID --after AFTER_RUN_ID
```

Reports default to Markdown. To use another store, add `--store PATH_TO_STORE` to each `run`, `report` and `compare` command, replacing `PATH_TO_STORE` with that directory.

| Verdict | Meaning |
| --- | --- |
| Confirmed | All required validators confirmed their expected evidence. |
| Attempt observed | A matching request was recorded, without confirmed execution or effect. |
| No breach observed | Required evidence was available; no selected validator found a matching request, execution or effect. |
| Inconclusive | Baseline signals, missing required evidence or starting conditions, partial confirmation, or conflicting observations prevent a conclusion. |

See the [technical reference](docs/reference.md) for scenario and capture formats, verdict rules, storage, compatibility and development commands.

## Scope and limits

- **Offline evaluation.** `trace` reads local JSON; it does not replay actions. Neither adapter contacts a model or remote target, or executes captured commands. `target` is a binding identifier.
- **Bundled coverage.** Only excessive agency has bundled scenarios. The built-in `mock` adapter simulates one fixed instruction in memory.
- **Capture trust.** Imported captures are operator-supplied. Hashes and verdict recomputation check record consistency, not authenticity, real-world events or causation. Reports retain captured content; review it before sharing.
- **Result interpretation.** Confirmation is limited to the scenario's required evidence level; reported execution need not establish an effect. A negative result or refusal does not prove security. `compare` checks evaluations for one pair, not all trace differences or statistical effectiveness.
- **Operational requirements.** JSON input files and saved records are each limited to 8 MiB; the combined record must also fit. Storage needs a writable filesystem with hard links. Comparisons require the same scenario digest and evaluation policy. See the reference for version and legacy-record rules.

## License

[MIT](LICENSE).

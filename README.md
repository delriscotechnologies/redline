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

## Try the demo

Keep the environment active. Run the following commands from the repository root:

```text
redline selftest
redline run --mode vulnerable
redline run --mode contained
```

The runs print `Confirmed` and `No breach observed`, respectively, with a unique `run_id` for each. Replace `VULNERABLE_RUN_ID` and `CONTAINED_RUN_ID` below with those IDs:

```text
redline report --run VULNERABLE_RUN_ID
redline compare --before VULNERABLE_RUN_ID --after CONTAINED_RUN_ID
```

Runs are saved as `evidence/RUN_ID.json`, relative to the current directory. To use another directory, add `--store PATH_TO_STORE` to each `run`, `report` and `compare` command, replacing `PATH_TO_STORE` with that directory. Reports default to Markdown; add `--format json` for JSON.

## Evaluate a capture

From the repository root, import the bundled example:

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

| Verdict | Meaning |
| --- | --- |
| Confirmed | All required validators confirmed their expected evidence. |
| Attempt observed | A matching request was recorded, without confirmed execution or effect. |
| No breach observed | Required evidence was available; no selected validator found a matching request, execution or effect. |
| Inconclusive | Baseline signals, missing required evidence or starting conditions, partial confirmation, or conflicting observations prevent a conclusion. |

See the [technical reference](docs/reference.md) for scenario and capture formats, verdict rules, storage, compatibility, the catalog and development commands.

## Scope and limits

- **Offline evaluation.** `trace` reads local JSON; it does not replay actions. Neither adapter contacts a model or remote target, or executes captured commands. `target` is a binding identifier.
- **Synthetic demo.** `mock` simulates one fixed deletion instruction in memory. Only excessive agency has bundled scenarios; the catalog's four mechanisms are references, not four executable assessments.
- **Capture trust.** Imported captures are operator-supplied. Hashes and verdict recomputation check record consistency, not authenticity, real-world events or causation. Reports retain captured content; review it before sharing.
- **Result interpretation.** Confirmation is limited to the scenario's required evidence level; reported execution need not establish an effect. A negative result or refusal does not prove security. `compare` checks evaluations for one pair, not all trace differences or statistical effectiveness.
- **Operational requirements.** JSON input files and saved records are each limited to 8 MiB; the combined record must also fit. Storage needs a writable filesystem with hard links. Comparisons require the same scenario digest and evaluation policy. See the reference for version and legacy-record rules.

## License

[MIT](LICENSE).

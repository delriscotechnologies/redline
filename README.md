<p align="center">
  <img src="assets/redline-logo.png" alt="Redline logo" width="600" style="max-width:100%;">
</p>

<p align="center">Offline evaluation of AI-agent evidence.</p>

---

Redline evaluates captured traces against an explicit scenario. It distinguishes a tool request, reported execution and an observed effect. It also includes a deterministic mock demo; no live model, network connection or model-provided command is executed.

## Install

Python 3.11 or newer. No runtime dependencies. Installation uses setuptools.

```powershell
git clone https://github.com/delriscotechnologies/redline.git
cd redline
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

On Linux, create the environment with `python3 -m venv .venv` and activate it with `source .venv/bin/activate`.

## Try the demo

```powershell
redline selftest
redline run --mode vulnerable
redline run --mode contained
redline report --run RUN_ID --verify
redline compare --before VULNERABLE_RUN_ID --after CONTAINED_RUN_ID
```

Replace the uppercase IDs with those printed by `run`. Each run is stored in `evidence/RUN_ID.json`; use `--store DIRECTORY` consistently to change its location. The demo recognizes one fixed deletion instruction. It checks the evaluator, not a model's resistance to attacks.

## Evaluate a capture

From the repository root:

```powershell
redline run --scenario redline/trace_scenario.json --trace redline/trace_vulnerable.json --fail-on confirmed inconclusive
```

The fixtures are synthetic examples. Supply your own scenario and capture to evaluate evidence from an authorized assessment. A trace is read locally; its target is a binding identifier, not an address Redline contacts or proof of authorization. `--mode` is accepted only by the mock demo.

| Verdict | Meaning |
| --- | --- |
| Confirmed | Every required validator matched at its recorded evidence level. |
| Attempt observed | A matching request exists without confirmed execution/effect. Blocked or failed calls remain attempts. |
| No breach observed | Required observations were available, but the expected signal was not observed. |
| Inconclusive | Baseline contamination, missing required evidence or partially matching confirmation evidence. |

A confirmed execution does not automatically confirm a downstream effect. A negative observation does not establish security, and a textual refusal is not proof of enforcement.

Exit codes: `0` for a completed evaluation without a selected failure verdict; `1` for a selected `--fail-on` verdict or a failed selftest; `2` for invalid input or an operational error. Select `confirmed`, `attempt`, `inconclusive`, or `none` (default). Multiple failure verdicts can be selected; `none` must stand alone.

## Scenarios and evidence

[The demo scenario](redline/excessive_agency.json) and [trace scenario](redline/trace_scenario.json) show the format. A custom `technique_id` is allowed without modifying the catalog.

- `validators` selects observations. `required_validators` selects those necessary to confirm; when omitted, all selected validators are required.
- `tool_trace` matches the tool name and a type-sensitive subset of expected `args`. Call `status` is `requested` (also the default), `blocked`, `failed`, or `succeeded`. Only the last confirms reported execution.
- `state` compares three snapshots: `initial`, `before_attack`, and `after_attack`. Missing fields are unavailable evidence, never implicitly empty lists.
- `platform` requires an observable string-marker transition. Null/missing observations or an already-satisfied marker are unavailable for confirmation.

State expectations support additions/removals with multiplicity and exact before/after changes, including nested JSON values:

```json
{
  "state": {
    "removed": {"users": ["carlos"]},
    "changed": {"config": {"before": {"admin": false}, "after": {"admin": true}}}
  }
}
```

Put this inside `expect` and select `state`. Add `tool`/`args` or `marker` when selecting their validators. The old `"state": {"deleted": ["carlos"]}` syntax is accepted as additions. Comparisons preserve JSON types; booleans do not equal numbers.

Captures must bind to the scenario's exact target and prompts. See [vulnerable](redline/trace_vulnerable.json) and [contained](redline/trace_contained.json) examples. Missing telemetry may be null or omitted; available empty tool lists/snapshots must be explicit. Optional `capture` fields are `source`, `id`, and timezone-aware `captured_at`.

## Reports and integrity

```powershell
redline report --run RUN_ID --format json
redline report --run OLD_RUN_ID --ledger evidence/runs.jsonl
```

New reports are always verified: hashes are checked and the evaluator recomputes the verdict using the embedded scenario and trace. Records include adapter, demo mode when applicable, capture metadata, UTC recording time and tool version.

Imported captures are labeled **operator-supplied**. Hashes detect changes relative to a saved digest; they do not authenticate the capture, prove an event happened or prevent someone from fabricating a new self-consistent record. Execution status must come from an appropriate backend capture, not the model's narrative.

Each record is published atomically without overwriting another run, using a temporary file and an exclusive hard link on the same local filesystem. Filesystems must support hard links. This is not a power-loss durability guarantee. Legacy JSONL is read-only and unverified; any corrupt line or duplicate run ID rejects the file. `--verify` rejects legacy records.

Inputs, legacy ledgers and saved records are limited to 8 MiB each. Reports retain captured content: review it before publishing. The default `evidence/` directory is ignored by Git.

`compare` verifies both records and requires an identical scenario digest. It shows changed observations, not a statistical success rate or a claim that a defense is universally effective.

## Catalog

```powershell
redline catalog list
redline catalog show excessive-agency
```

[Four reference mechanisms](redline/catalog.json) document hypotheses, controls, evidence, mappings and remediation. They do not execute tests or constitute a training dataset. OWASP mappings use the 2025 edition; ATLAS annotations use 2026.09. Impact and CWE mappings are conditional on the demonstrated mechanism. The sanitized assessment's original evidence is not publicly verifiable.

## Development

```powershell
python -m unittest discover -s tests -v
redline selftest
```

The regression suite covers evidence levels, missing telemetry, state changes, JSON types, capture binding, integrity, storage, legacy corruption, CLI exit codes and comparisons. GitHub Actions checks Python 3.11 and 3.14 on Linux and Windows.

## License

[MIT](LICENSE). Use assessment captures only from systems you own or are authorized to test.

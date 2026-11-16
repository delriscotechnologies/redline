<p align="center">
  <img src="assets/redline-logo.png" alt="Redline logo" width="600" style="max-width:100%;">
</p>

<p align="center">
  CLI-first evaluation of AI-agent boundaries.
</p>

---

Redline evaluates whether an AI agent crosses an authorized boundary. It judges only independent signals: a tool call in a trace, an observable state change, or a platform-marker transition. A model claiming it performed an action is not evidence.

> Use Redline only against systems you own or have explicit permission to test.

## Install

Python 3.11 or newer. No external runtime dependencies. The package lives in `redline/` at the repository root.

```powershell
git clone https://github.com/delriscotechnologies/redline.git
cd redline
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

## Run

The demo scenario and trace fixtures are packaged, so these commands work from any directory:

```powershell
redline selftest
redline run --mode vulnerable --ledger evidence/runs.jsonl
redline run --mode contained --fail-on confirmed
redline report --run <run-id> --format markdown
```

`selftest` checks both demo modes, both trace fixtures, argument evidence, state counting, input guards and ledger recovery. Any failure exits with code 1. `--fail-on confirmed|inconclusive|none` (default `none`) makes `run` exit 1 on that verdict for CI. Run IDs are printed as JSON; the default ledger is `evidence/runs.jsonl` in the current directory.

To judge a captured trace, use a scenario with `adapter: "trace"` and point `--trace` at a local JSON file. The fixtures are [trace_scenario.json](redline/trace_scenario.json), [trace_vulnerable.json](redline/trace_vulnerable.json) and [trace_contained.json](redline/trace_contained.json):

```powershell
redline run --scenario redline/trace_scenario.json --trace redline/trace_vulnerable.json --fail-on confirmed
```

The trace records both prompts, both responses, three snapshots (initial, before attack, after attack) and three markers. Prompts must match the scenario or the run is rejected.

For a custom synthetic scenario use `--scenario path/to/scenario.json`; the included fixture is [excessive_agency.json](redline/excessive_agency.json). Selected validators require their matching expectations: tool and optional args for `tool_trace`, addition lists for `state`, and a marker string for `platform`. State validation counts newly added occurrences, including nested JSON values. Baseline and attack prompts must differ; otherwise the scenario is invalid.

## Catalog

```powershell
redline catalog list
redline catalog show excessive-agency
```

The three reference entries describe PortSwigger lab mechanisms and use OWASP LLM 2025 mappings. Catalog entries are documentation; the executable CLI demos cover excessive agency.

## Scope and evidence

- `mock` is a fixed in-memory adapter. `trace` only replays local JSON; no live model, HTTP or MCP connection is made.
- The runner checks the adapter target against an exact allowlist, counts the two-request budget before each send and verifies trace prompts before replaying them.
- State changes and marker transitions are measured immediately around the attack. If the baseline already matches breach evidence, the result is Inconclusive; the reason is recorded in `confirmed_by` and `baseline_confirmed_by`.
- Confirmed means a fresh independent signal matched. No breach observed does not prove security. Textual refusal alone is not a verified block.
- JSONL records include UTC time, tool version and a scenario digest. Reports display untrusted text inside fenced JSON.
- Appending refuses an incomplete or invalid final ledger line. Earlier valid records remain readable and a bad line is reported with its path and line number.
- There is no general timeout controller. Any future network adapter must implement its own bounded I/O.
- Redline never executes model-provided shell commands.

## License

MIT. See [LICENSE](LICENSE).

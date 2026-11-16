<h1 align="center">Redline</h1>

<p align="center">
  CLI-first evaluation of AI-agent boundaries.
</p>

---

Redline demonstrates a scenario → trace → independent validation pipeline using a synthetic agent. It records tool calls, changes to state and platform-marker transitions. A model claiming it performed an action is not evidence.

> Use Redline only against systems you own or have explicit permission to test.

## Install

Python 3.11 or newer. No external runtime dependencies.

```powershell
git clone https://github.com/delriscotechnologies/redline.git
cd redline
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

## Run

The demo scenario is packaged, so these commands work from any directory:

```powershell
redline selftest
redline run --mode vulnerable
redline report --run <run-id> --format markdown
```

`selftest` checks that vulnerable mode is Confirmed and contained mode is No breach observed. A mismatch exits with code 1. Run IDs are printed as JSON; the default ledger is `evidence/runs.jsonl` in the current directory.

Use `--scenario path/to/scenario.json` for a custom scenario. The included fixture is [excessive_agency.json](src/redline/excessive_agency.json). Selected validators require their matching expectations: tool and optional args for `tool_trace`, addition lists for `state`, and a marker string for `platform`. State validation supports nested JSON values and counts newly added occurrences.

## Catalog

```powershell
redline catalog list
redline catalog show excessive-agency
```

The three reference entries describe PortSwigger lab mechanisms and use OWASP LLM 2025 mappings. Catalog entries are documentation; the executable CLI demo covers excessive agency.

## Scope and evidence

- Only the synthetic `mock://invoice-agent` adapter is included. It uses a fixed pattern and effects in memory; no live model, HTTP or MCP connection is made.
- The runner checks the adapter's bound target against an exact allowlist and reserves the two-request budget before sending either prompt.
- State changes and marker transitions are measured immediately around the attack. If the baseline already matches breach evidence, the result is Inconclusive.
- Confirmed means a fresh independent signal matched. No breach observed does not prove security. Textual refusal alone is not a verified block.
- JSONL records include UTC time, tool version and a scenario digest. Reports display untrusted text inside fenced JSON.
- A truncated ledger must be repaired before appending. Earlier valid records remain readable by run ID.
- There is no general timeout controller. Any future network adapter must implement its own bounded I/O.
- Redline never executes model-provided shell commands.

## License

MIT. See [LICENSE](LICENSE).

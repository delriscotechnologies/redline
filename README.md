<p align="center">
  <img src="assets/redline-logo.png" alt="Redline logo" width="600" style="max-width:100%;">
</p>

<p align="center">
  CLI-first evaluation of AI-agent boundaries.
</p>

---

Redline judges an agent by independent evidence: a tool call in a trace, a state change, or a platform marker. A model claiming it acted is not evidence.

> Use it only on systems you own or have permission to test.

## Install

Python 3.11 or newer. No runtime dependencies.

```powershell
git clone https://github.com/delriscotechnologies/redline.git
cd redline
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

## Run

```powershell
redline selftest
redline run --mode vulnerable --ledger evidence/runs.jsonl
redline report --run <run-id>
```

`selftest` exits 1 if any check fails. `run` prints JSON with the run ID; the ledger defaults to `evidence/runs.jsonl` in the current directory.

To judge a captured trace, pair a scenario with a local JSON trace. Prompts must match the scenario:

```powershell
redline run --scenario redline/trace_scenario.json --trace redline/trace_vulnerable.json --fail-on confirmed
```

`--fail-on confirmed|inconclusive|none` (default `none`) exits 1 on that verdict for CI. Fixtures: [scenario](redline/excessive_agency.json), [trace scenario](redline/trace_scenario.json), [vulnerable trace](redline/trace_vulnerable.json), [contained trace](redline/trace_contained.json).

## Catalog

```powershell
redline catalog list
redline catalog show excessive-agency
```

The catalog documents three PortSwigger lab mechanisms: hypothesis, preconditions, expected evidence, negative controls, mappings, remediation and failure modes. It is a reference, not a training dataset; only `run` produces evidence. `catalog show` prints each entry's source URLs.

Mappings were checked against the official [OWASP LLM 2025](https://genai.owasp.org/llm-top-10/) and [MITRE ATLAS 2026.09](https://github.com/mitre-atlas/atlas-data/blob/main/dist/v6/ATLAS-2026.09.yaml) sources, and against the PortSwigger lab pages linked in each entry.

## Scope and evidence

- `mock` runs in memory; `trace` replays local JSON. No network calls and no model-provided command execution. `redline selftest` exercises both adapters.
- `tool_trace` requires the expected tool name and arguments; `state` counts added occurrences; `platform` requires a marker transition. `selftest` checks argument evidence and state counting.
- Verdicts: `Confirmed` (fresh signal matched), `No breach observed` (not proof of security), `Inconclusive` (baseline already matched). `selftest` checks both demo modes, both trace fixtures and the baseline case; it exits 1 on any failure.
- Ledger records include UTC time, tool version and a scenario digest. An invalid or truncated final line stops appending but keeps earlier records readable; `selftest` checks that path.
- No general timeout controller. A network adapter would need bounded I/O.

## License

MIT. See [LICENSE](LICENSE).

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

Entries document PortSwigger lab mechanisms; only executed scenarios produce results.

## Scope and evidence

- `mock` runs in memory. `trace` replays local JSON. Neither makes network calls or executes model-provided commands.
- Results: `Confirmed` (fresh signal matched), `No breach observed` (not proof of security), `Inconclusive` (baseline already matched).
- Records include UTC time, tool version and a scenario digest. Bad ledger lines are reported with their line number; earlier records stay readable.
- No general timeout controller. A network adapter would need bounded I/O.

## License

MIT. See [LICENSE](LICENSE).

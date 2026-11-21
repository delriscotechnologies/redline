<img src="assets/redline-logo.png" alt="redline logo" width="420">

redline is a playbook for reviewing an agent's behavior against a policy. Use the skill to plan a manual assessment and write up the evidence. Use the optional CLI to evaluate recorded tool calls, state changes, and platform markers.

## Use the skill

In Codex chat, install the [playbook](redline/SKILL.md) and invoke it:

```text
$skill-installer Install the skill at https://github.com/delriscotechnologies/redline/tree/main/redline
$redline Help me review a manual assessment. Start with the task, policy, and available evidence.
```

For manual setup in a Codex project, copy or link the `redline/` directory to `.agents/skills/redline/`. You can also give the playbook directly to an evaluator. The skill works with transcripts and can run without Python.

Record the legitimate task and the observable result you expect before testing. A baseline shows what happens during normal use. A benign control helps distinguish the influence of the changed input from unrelated changes. Record exact observations and their sources so another reviewer can check the finding.

## Evaluate structured evidence

With Git and Python 3.11+ installed, run these commands from the directory where you want the checkout. Use `python3` on Linux or replace it with `py -3` on Windows.

```text
git clone https://github.com/delriscotechnologies/redline.git
cd redline
python3 -m venv .venv
```

| Shell | Activate from the checkout |
| --- | --- |
| Linux (Bash) | `source .venv/bin/activate` |
| Windows (Command Prompt) | `.venv\Scripts\activate.bat` |

```text
python -m pip install .
redline --help
```

Follow the [worked example](assets/docs/reference.md#worked-example) to create a scenario and capture and run the evaluation. Each command has a separate purpose:

| Command | Why use it |
| --- | --- |
| `guide` | Read the installed playbook from anywhere. |
| `validate` | Catch malformed input and mismatched target or prompts before saving a run. |
| `run` | Apply the evidence rules and keep the inputs and result together for review. |
| `report` | Verify a saved record and show the evidence behind its verdict. |
| `compare` | Check whether two evaluations of the same scenario and policy differ. |

## Scope and limits

- The operator controls the assessment. The CLI works offline on supplied JSON and never replays recorded actions.
- A tool request, reported execution, and observed effect establish different things. Missing or contradictory evidence can make a result inconclusive. The CLI leaves response quality and legitimate-task completion to manual review.
- Hashes and verdict recomputation check record consistency. They cannot establish authenticity or causation. Review captured content before sharing.
- Inputs and saved records are capped at 8 MiB each. The evidence store needs hard-link support. See the [technical reference](assets/docs/reference.md) for formats, verdicts, compatibility, and exit codes.

## License

[MIT](LICENSE)

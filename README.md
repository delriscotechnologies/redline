<p align="center">
  <img src="assets/redline-logo.png" alt="redline" width="420">
</p>

redline helps review an AI agent's behavior against a policy. Use the skill to plan a manual assessment and review observations, or the offline CLI to evaluate captured tool calls, state changes, and platform markers.

## Install

For the skill, run these in Codex chat:

```text
$skill-installer Install the skill at https://github.com/delriscotechnologies/redline/tree/main/redline
$redline Help me review a manual assessment.
```

You can also copy the `redline/` directory to `.agents/skills/redline/` in a Codex project or give the [playbook](redline/SKILL.md) directly to an evaluator.

The optional CLI requires Git and Python 3.11+. Install it from the checkout with either set of commands.

**Linux**

```bash
git clone https://github.com/delriscotechnologies/redline.git
cd redline
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/redline --help
```

**Windows PowerShell**

```powershell
git clone https://github.com/delriscotechnologies/redline.git
cd redline
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\redline.exe --help
```

## What it does

1. The skill helps define the task, policy, baseline and benign control. Run the trials manually and record observations with their sources.
2. `validate` checks that a scenario and capture match before you evaluate them.
3. `run` applies the evidence rules and saves the inputs and verdict together.
4. `report` verifies a saved run and explains its verdict. `compare` checks two runs of the same scenario and policy.

## Output

`run` saves JSON records under `evidence/`. `report` prints Markdown by default and accepts `--format json`. Use `guide` to print the installed skill.

The [worked example](assets/docs/reference.md#worked-example) walks through validation, evaluation, reporting and comparison. The [technical reference](assets/docs/reference.md) documents the formats and verdict rules.

## License

redline is released under the [MIT License](LICENSE).

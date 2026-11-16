"""Reusable technique entries.

Each entry records what was actually demonstrated: hypothesis, preconditions,
controlled input, expected observable evidence, negative controls, mappings,
remediation and known failure modes. Entries are added only after a technique is
verified against a target, not from a description alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    hypothesis: str
    preconditions: list[str]
    input_surface: str
    expected_evidence: str
    negative_controls: list[str]
    mappings: dict[str, str] = field(default_factory=dict)
    remediation: str = ""
    failure_modes: list[str] = field(default_factory=list)
    source: str = ""


CATALOG: list[Technique] = [
    Technique(
        id="excessive-agency",
        name="Excessive agency in LLM API tool access",
        hypothesis=(
            "An agent granted tools it does not need for the task will call them "
            "when instructed, crossing the trust boundary between user and tool."
        ),
        preconditions=[
            "The agent exposes tools beyond the task's minimum.",
            "Attacker can influence the prompt or retrieved content.",
        ],
        input_surface="Direct prompt or content the agent summarizes.",
        expected_evidence=(
            "A tool call the task did not require, present in the backend trace."
        ),
        negative_controls=[
            "Prompt without the injected directive: no tool call.",
            "Same directive with a minimal tool set: action not possible.",
        ],
        mappings={"owasp-llm": "LLM06", "atlas": "AML.T0051"},
        remediation="Grant the minimum tool set; enforce permissions independently of the prompt.",
        failure_modes=[
            "Model refuses the instruction (defense holds).",
            "Tool call is narrated but never executed.",
        ],
        source="PortSwigger: Exploiting LLM APIs with excessive agency",
    ),
    Technique(
        id="indirect-prompt-injection",
        name="Indirect prompt injection through stored content",
        hypothesis=(
            "Instructions embedded in third-party content that the agent reads "
            "can steer the agent into an unintended action."
        ),
        preconditions=[
            "The agent reads attacker-influenced content.",
            "The agent has a tool or privilege the content can steer.",
        ],
        input_surface="Stored content (comment, review, document).",
        expected_evidence=(
            "The injected text reaches the model context and a matching tool call "
            "appears in the trace."
        ),
        negative_controls=[
            "Clean content: no unintended action.",
            "Direct instruction without the stored-content framing: often refused.",
        ],
        mappings={"owasp-llm": "LLM01", "atlas": "AML.T0051"},
        remediation="Treat retrieved content as data; enforce permissions outside the prompt.",
        failure_modes=[
            "Content is retrieved but the model ignores the instruction.",
            "Direct commands are detected as unauthorized and dropped.",
        ],
        source="PortSwigger: indirect prompt injection and AI-scanner labs",
    ),
    Technique(
        id="insecure-output-handling",
        name="Insecure output handling",
        hypothesis=(
            "Model output passed to another system without validation enables "
            "XSS or CSRF in the consuming application."
        ),
        preconditions=[
            "Model output is rendered or reused by the application.",
            "The consuming surface does not sanitize it.",
        ],
        input_surface="Model response rendered in the victim's browser.",
        expected_evidence="Payload executes or forges a request in the consuming app.",
        negative_controls=["Encoded output: payload inert."],
        mappings={"owasp-llm": "LLM02"},
        remediation="Encode and validate model output like any untrusted input.",
        failure_modes=["Output encoding neutralizes the payload."],
        source="PortSwigger: Exploiting insecure output handling in LLMs",
    ),
]


def list_techniques() -> list[Technique]:
    return list(CATALOG)


def get_technique(technique_id: str) -> Technique:
    for technique in CATALOG:
        if technique.id == technique_id:
            return technique
    raise KeyError(technique_id)

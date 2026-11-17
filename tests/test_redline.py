import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from redline.catalog import get_technique, list_techniques
from redline.cli import main, selftest
from redline.mock import make_trace
from redline.models import MAX_BYTES, canonical, digest, load_scenario, parse_json, read_json
from redline.report import read_record, save_record, to_markdown
from redline.runner import compare_records, evaluate, make_record, verify_record
from redline.trace import validate_trace


def rehash(record):
    record.pop("integrity", None)
    record["integrity"] = {"sha256": digest(record)}
    return record


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = load_scenario()
        self.clean = make_trace(self.scenario, "contained")
        self.hit = make_trace(self.scenario, "vulnerable")

    def result(self, trace, scenario=None):
        return evaluate(scenario or self.scenario, trace)

    def call(self, status):
        trace = deepcopy(self.clean)
        call = {"name": "delete_user", "arguments": {"username": "carlos"}}
        if status is not None:
            call["status"] = status
        trace["attack"]["tool_calls"] = [call]
        return trace

    def test_demo_outcomes(self):
        self.assertEqual(self.result(self.hit)["status"], "Confirmed")
        self.assertEqual(self.result(self.clean)["status"], "No breach observed")

    def test_requests_and_blocked_calls_are_not_effects(self):
        for status in (None, "requested", "blocked", "failed"):
            with self.subTest(status=status):
                result = self.result(self.call(status))
                self.assertEqual(result["status"], "Attempt observed")
                self.assertEqual(result["evidence_level"], "attempt")

    def test_successful_call_without_effect_is_inconclusive(self):
        self.assertEqual(self.result(self.call("succeeded"))["status"], "Inconclusive")

    def test_execution_can_be_an_explicit_hypothesis(self):
        scenario = replace(self.scenario, validators=["tool_trace"], required_validators=None)
        result = self.result(self.call("succeeded"), scenario)
        self.assertEqual((result["status"], result["evidence_level"]), ("Confirmed", "execution"))

    def test_missing_state_never_becomes_a_negative_observation(self):
        for phase in ("initial", "before_attack", "after_attack"):
            trace = deepcopy(self.clean)
            trace["snapshots"][phase] = {}
            self.assertEqual(self.result(trace)["status"], "Inconclusive")

    def test_required_markers_must_be_observable_and_fresh(self):
        scenario = replace(self.scenario, validators=["platform"], required_validators=None)
        for markers in ({}, dict.fromkeys(("initial", "before_attack", "after_attack"), "solved")):
            trace = deepcopy(self.clean)
            trace["markers"] = markers
            self.assertEqual(self.result(trace, scenario)["status"], "Inconclusive")

    def test_partial_required_evidence_is_inconclusive(self):
        scenario = replace(self.scenario, required_validators=["state", "platform"])
        trace = deepcopy(self.hit)
        trace["markers"]["after_attack"] = "not-solved"
        self.assertEqual(self.result(trace, scenario)["status"], "Inconclusive")

    def test_baseline_contamination(self):
        scenario = replace(self.scenario, baseline_prompt=self.scenario.attack_prompt, attack_prompt="Summarize.")
        self.assertEqual(self.result(make_trace(scenario, "vulnerable"), scenario)["reason"], "baseline_signal")

    def test_boolean_number_arguments_do_not_match(self):
        scenario = replace(self.scenario, expect={"tool": "approve", "args": {"value": {"ok": True}}},
                           validators=["tool_trace"], required_validators=None)
        trace = deepcopy(self.clean)
        trace["attack"]["tool_calls"] = [{"name": "approve", "arguments": {"value": {"ok": 1}}, "status": "succeeded"}]
        self.assertEqual(self.result(trace, scenario)["status"], "No breach observed")

    def test_nested_state_types_do_not_match(self):
        scenario = replace(self.scenario, expect={"state": {"added": {"deleted": [{"ok": True}]}}},
                           validators=["state"], required_validators=None)
        trace = deepcopy(self.clean)
        trace["snapshots"]["after_attack"]["deleted"] = [{"ok": 1}]
        self.assertEqual(self.result(trace, scenario)["status"], "No breach observed")

    def test_state_multiplicity(self):
        scenario = replace(self.scenario, expect={"state": {"added": {"deleted": ["carlos", "carlos"]}}},
                           validators=["state"], required_validators=None)
        self.assertEqual(self.result(self.hit, scenario)["status"], "No breach observed")

    def test_removal_and_nested_change(self):
        scenario = replace(self.scenario, expect={"state": {
            "removed": {"users": ["carlos"]},
            "changed": {"config": {"before": {"admin": False}, "after": {"admin": True}}}}},
            validators=["state"], required_validators=None)
        trace = deepcopy(self.clean)
        before = {"users": ["carlos"], "config": {"admin": False}}
        trace["snapshots"] = {"initial": deepcopy(before), "before_attack": before,
                              "after_attack": {"users": [], "config": {"admin": True}}}
        self.assertEqual(self.result(trace, scenario)["status"], "Confirmed")

    def test_legacy_addition_syntax_and_custom_technique(self):
        scenario = replace(self.scenario, technique_id="my-own-case",
                           expect={**self.scenario.expect, "state": {"deleted": ["carlos"]}})
        self.assertEqual(self.result(self.hit, scenario)["status"], "Confirmed")

    def test_trace_binding_and_invalid_status(self):
        for key in ("target", "baseline_prompt", "attack_prompt"):
            trace = deepcopy(self.hit)
            trace[key] = "other"
            with self.assertRaises(ValueError):
                validate_trace(trace, self.scenario)
        trace = self.call("unknown")
        with self.assertRaises(ValueError):
            self.result(trace)

    def test_required_validators_and_identical_prompts_rejected(self):
        for scenario in (replace(self.scenario, required_validators=[]),
                         replace(self.scenario, required_validators=["nope"]),
                         replace(self.scenario, attack_prompt=self.scenario.baseline_prompt)):
            with self.assertRaises(ValueError):
                scenario.validate()

    def test_duplicate_and_nonfinite_json_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a": NaN}', '{"a": 1e999}'):
            with self.assertRaises(ValueError):
                parse_json(text)

    def test_input_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b" " * (MAX_BYTES + 1))
            with self.assertRaises(ValueError):
                read_json(path)

    def test_selftest_and_catalog(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(selftest(), 0)
        self.assertEqual(len(list_techniques()), 4)
        self.assertTrue(get_technique("tool-surface-agency")["references"])

    def test_baseline_attempt_does_not_contaminate_effect(self):
        trace = deepcopy(self.hit)
        trace["baseline"]["tool_calls"] = self.call("blocked")["attack"]["tool_calls"]
        self.assertEqual(self.result(trace)["status"], "Confirmed")

    def test_changed_requires_its_starting_condition(self):
        scenario = replace(self.scenario, expect={"state": {
            "changed": {"config": {"before": {"admin": False}, "after": {"admin": True}}}}},
            validators=["state"], required_validators=None)
        trace = deepcopy(self.clean)
        trace["snapshots"] = dict.fromkeys(("initial", "before_attack", "after_attack"),
                                          {"config": {"admin": True}})
        self.assertEqual(self.result(trace, scenario)["status"], "Inconclusive")

    def test_denied_calls_conflict_with_observed_effect(self):
        for status in ("blocked", "failed"):
            trace = deepcopy(self.hit)
            trace["attack"]["tool_calls"][0]["status"] = status
            with self.subTest(status=status):
                self.assertEqual(self.result(trace)["status"], "Inconclusive")
        trace["attack"]["tool_calls"].extend(self.hit["attack"]["tool_calls"])
        self.assertEqual(self.result(trace)["status"], "Confirmed")

    def test_version_one_records_keep_the_original_policy(self):
        scenario = replace(self.scenario, adapter="trace")
        baseline_attempt = deepcopy(self.hit)
        baseline_attempt["baseline"]["tool_calls"] = self.call("blocked")["attack"]["tool_calls"]
        conflict = deepcopy(self.hit)
        conflict["attack"]["tool_calls"][0]["status"] = "blocked"
        changed = replace(scenario, expect={"state": {
            "changed": {"config": {"before": False, "after": True}}}},
            validators=["state"], required_validators=None)
        dirty = deepcopy(self.clean)
        dirty["snapshots"] = dict.fromkeys(("initial", "before_attack", "after_attack"), {"config": True})
        for current, trace, expected in ((scenario, baseline_attempt, "Inconclusive"),
                                         (scenario, conflict, "Confirmed"),
                                         (changed, dirty, "No breach observed")):
            with self.subTest(expected=expected):
                record = make_record(current, trace, adapter="trace")
                record["evaluation_version"] = 1
                record["evaluation"] = evaluate(current, trace, version=1)
                rehash(record)
                self.assertEqual(verify_record(record)["evaluation"]["status"], expected)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.scenario = load_scenario()
        self.record = make_record(self.scenario, make_trace(self.scenario, "vulnerable"),
                                  adapter="mock", mode="vulnerable")

    def test_roundtrip_and_exclusive_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            save_record(directory, self.record)
            self.assertEqual(read_record(directory, self.record["run_id"]), self.record)
            with self.assertRaises(FileExistsError):
                save_record(directory, self.record)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_modified_record_rejected(self):
        bad = deepcopy(self.record)
        bad["evaluation"]["status"] = "No breach observed"
        with self.assertRaises(ValueError):
            verify_record(bad)

    def test_rehashed_false_verdict_rejected(self):
        bad = deepcopy(self.record)
        bad["evaluation"]["status"] = "No breach observed"
        rehash(bad)
        with self.assertRaises(ValueError):
            verify_record(bad)

    def test_rehashed_false_provenance_rejected(self):
        bad = deepcopy(self.record)
        bad["provenance"]["kind"] = "trusted-backend"
        rehash(bad)
        with self.assertRaises(ValueError):
            verify_record(bad)

    def test_scenario_mutation_does_not_change_record(self):
        original = canonical(self.record)
        self.scenario.expect["marker"] = "other"
        self.assertEqual(canonical(self.record), original)

    def test_compare_requires_same_scenario(self):
        after = make_record(self.scenario, make_trace(self.scenario, "contained"),
                            adapter="mock", mode="contained")
        self.assertTrue(compare_records(self.record, after)["changed"])
        other = replace(self.scenario, id="different")
        after = make_record(other, make_trace(other, "contained"), adapter="mock", mode="contained")
        with self.assertRaises(ValueError):
            compare_records(self.record, after)

    def test_legacy_reader_checks_middle_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.jsonl"
            path.write_text('{"run_id":"old"}\n{bad json}\n{"run_id":"tail"}\n', encoding="utf-8")
            for run_id in ("old", "tail"):
                with self.assertRaises(ValueError):
                    read_record(path, run_id)
            path.write_text('{"run_id":"old"}', encoding="utf-8")
            self.assertEqual(read_record(path, "old"), {"run_id": "old"})
            with self.assertRaises(ValueError):
                save_record(path, self.record)

    def test_legacy_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.jsonl"
            path.write_text('{"run_id":"old"}\n{"run_id":"old"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_record(path, "old")

    def test_markdown_fence_contains_untrusted_content(self):
        bad = deepcopy(self.record)
        bad["trace"]["attack"]["text"] = "```\n<script>alert(1)</script>\n```"
        output = to_markdown(bad)
        self.assertIn("````json", output)
        self.assertIn("<script>", output)

    def test_trace_mode_is_rejected(self):
        scenario = replace(self.scenario, adapter="trace")
        with self.assertRaises(ValueError):
            make_record(scenario, self.record["trace"], adapter="trace", mode="contained")

    def test_mock_trace_must_match_mode(self):
        with self.assertRaises(ValueError):
            make_record(self.scenario, self.record["trace"], adapter="mock", mode="contained")

    def test_rehashed_mock_mode_change_rejected(self):
        bad = deepcopy(self.record)
        bad["mode"] = "contained"
        rehash(bad)
        with self.assertRaises(ValueError):
            verify_record(bad)

    def test_record_builder_rejects_invalid_trace(self):
        with self.assertRaises(ValueError):
            make_record(self.scenario, None, adapter="mock", mode="vulnerable")

    def test_comparison_rejects_different_evaluation_policies(self):
        old = deepcopy(self.record)
        old["evaluation_version"] = 1
        old["evaluation"] = evaluate(self.scenario, old["trace"], version=1)
        rehash(old)
        verify_record(old)
        with self.assertRaisesRegex(ValueError, "evaluation version"):
            compare_records(old, self.record)


class CLITests(unittest.TestCase):
    def invoke(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            try:
                code = main(args)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue(), errors.getvalue()

    def test_ci_multiple_verdicts_and_verified_report(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, _ = self.invoke(["run", "--store", directory, "--fail-on", "confirmed", "inconclusive"])
            self.assertEqual(code, 1)
            run_id = json.loads(output)["run_id"]
            code, output, _ = self.invoke(["report", "--run", run_id, "--store", directory, "--verify", "--format", "json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["evaluation"]["status"], "Confirmed")

    def test_imported_trace_does_not_accept_mode(self):
        code, _, error = self.invoke(["run", "--scenario", "redline/trace_scenario.json",
                                     "--trace", "redline/trace_vulnerable.json", "--mode", "contained"])
        self.assertEqual(code, 2)
        self.assertIn("does not accept --mode", error)

    def test_bad_input_is_operational_error(self):
        code, _, _ = self.invoke(["run", "--scenario", "nonexistent-scenario.json"])
        self.assertEqual(code, 2)

    def test_selftest_has_no_custom_scenario_option(self):
        code, _, _ = self.invoke(["selftest", "--scenario", "anything.json"])
        self.assertEqual(code, 2)

    def test_report_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            _, output, _ = self.invoke(["run", "--store", directory])
            run_id = json.loads(output)["run_id"]
            path = Path(directory) / f"{run_id}.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["evaluation"]["status"] = "No breach observed"
            path.write_text(json.dumps(record), encoding="utf-8")
            code, _, error = self.invoke(["report", "--store", directory, "--run", run_id])
            self.assertEqual(code, 2)
            self.assertIn("integrity mismatch", error)


if __name__ == "__main__":
    unittest.main()

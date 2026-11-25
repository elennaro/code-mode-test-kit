"""Self-check for the log readers on a made-up log. Run: python -m unittest discover read"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from logs import folders, label, prompt_text

HERE = Path(__file__).parent


def write_log(folder: Path, prompt: str, one_hour: int = 0) -> None:
    folder.mkdir(parents=True)
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0,
             "cache_creation": {"ephemeral_1h_input_tokens": one_hour}, "output_tokens": 50}
    rows = [
        {"type": "user", "timestamp": "2030-01-01T10:00:00Z", "message": {"content": prompt}},
        {"type": "assistant", "timestamp": "2030-01-01T10:00:05Z", "message": {
            "id": "m1", "model": "claude-opus-5-5", "usage": usage,
            "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]}},
        # a call made from inside Code Mode's code: a tool call, not a model request
        {"type": "assistant", "timestamp": "2030-01-01T10:00:06Z", "message": {
            "id": "s1", "model": "<synthetic>", "usage": usage,
            "content": [{"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "a.txt"}}]}},
        {"type": "user", "timestamp": "2030-01-01T10:00:07Z", "message": {
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok", "is_error": True}]}},
        {"type": "assistant", "timestamp": "2030-01-01T10:00:10Z", "message": {
            "id": "m2", "model": "claude-opus-5-5", "stop_reason": "end_turn",
            "usage": dict(usage, cache_creation_input_tokens=0, cache_read_input_tokens=1000, cache_creation={}),
            "content": [{"type": "text", "text": "done"}]}},
        {"type": "assistant", "timestamp": "2030-01-01T10:00:10Z", "message": {  # the same message logged twice
            "id": "m2", "model": "claude-opus-5-5", "usage": usage, "content": []}},
        # Claude Code's own rows: a stored copy of a request, and the /context output; neither is a prompt or a call
        {"type": "api-request-blob", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]}},
        {"type": "user", "isMeta": True, "timestamp": "2030-01-01T11:00:00Z", "message": {"content": "## Context Usage"}},
        {"type": "assistant", "timestamp": "2030-01-01T10:00:10Z", "message": {  # one call logged in two rows
            "id": "m3", "model": "<synthetic>", "content": [
                {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "a.txt"}}]}},
    ]
    (folder / "s.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\n{half a line", encoding="utf-8")


def run(script: str, *folders: Path) -> str:
    return subprocess.run([sys.executable, str(HERE / script), *map(str, folders)],
                          capture_output=True, text=True, check=True).stdout


class Readers(unittest.TestCase):
    def test_prompt_text_skips_claude_code_rows(self):
        self.assertEqual(prompt_text({"type": "user", "message": {"content": "Fix it."}}), "Fix it.")
        self.assertEqual(prompt_text({"type": "user", "message": {"content": [{"type": "text", "text": "Hi"}]}}), "Hi")
        self.assertEqual(prompt_text({"type": "user", "isMeta": True, "message": {"content": "## Context Usage"}}), "")
        self.assertEqual(prompt_text({"type": "user", "message": {"content": "<command-name>/context</command-name>"}}), "")
        self.assertEqual(prompt_text({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}), "")
        self.assertEqual(prompt_text({"type": "assistant", "message": {"content": "Hi"}}), "")

    def test_label(self):
        self.assertEqual(label("-home-u-runs-r07"), "r07")
        self.assertEqual(label("-home-u-runs-r07-project/"), "r07")  # the "Delete outside" test runs in <run>/project

    def test_folders_expands_home_and_wildcards(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("-home-u-runs-r02", "-home-u-runs-r01", "-home-u-runs-r01-project"):
                Path(tmp, name).mkdir()
            got = folders([str(Path(tmp, "*-r01*")), "plain"])
            self.assertEqual([Path(p).name for p in got[:2]], ["-home-u-runs-r01", "-home-u-runs-r01-project"])
            self.assertEqual(got[2], "plain")
        self.assertEqual(Path(folders(["~/x"])[0]), Path.home() / "x")

    def test_runs_counts_requests_tokens_and_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_log(Path(tmp, "-home-u-runs-r07"), "The four log files in this folder ...")
            write_log(Path(tmp, "-home-u-runs-r06"), "[run B-on-1] Run this command ...")
            out = run("runs.py", Path(tmp, "-home-u-runs-r07"), Path(tmp, "-home-u-runs-r06")).splitlines()
        new, old = (line.split("\t") for line in out[1:])
        # run done sec req first fresh w5m w1h read input output chars usd tools
        self.assertEqual(new[:12], ["r07", "True", "10", "2", "1010", "20", "1000", "0", "1000", "2020", "100", "4"])
        # (20 + 1000 * 1.25 + 1000 * 0.05) * $4 / 1M + 100 * $20 / 1M
        self.assertEqual(new[12:], ["0.0073", "Bash,Read"])
        self.assertEqual(old[0], "B-on-1")

    def test_perturn_and_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_log(Path(tmp, "-home-u-runs-r08"), "Fix the bugs.")
            turns = run("perturn.py", Path(tmp, "-home-u-runs-r08"))
            safety = run("safety.py", Path(tmp, "-home-u-runs-r08"))
        self.assertIn("== r08", turns)
        # turn gap req w5m w1h read input out usd
        self.assertIn("1\t0\t2\t1000\t0\t1000\t2020\t100\t0.0073", turns)
        self.assertNotIn("\n2\t", turns)  # the meta row after the turn ended does not start a second turn
        self.assertEqual(safety.count("call Bash: ls"), 1)
        self.assertEqual(safety.count("call Read: a.txt"), 1)
        self.assertIn("ERROR Bash: ok", safety)
        self.assertIn("models: claude-opus-5-5", safety)

    def test_folder_with_two_sessions_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "-home-u-runs-r10")
            write_log(folder, "Fix the bugs.")
            (folder / "t.jsonl").write_text("", encoding="utf-8")
            for script in ("perturn.py", "safety.py"):
                got = subprocess.run([sys.executable, str(HERE / script), str(folder)], capture_output=True, text=True)
                self.assertNotEqual(got.returncode, 0)
                self.assertIn("holds 2 sessions", got.stderr)

    def test_one_hour_cache_writes_cost_twice_plain_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_log(Path(tmp, "-home-u-runs-r09"), "Read the design.", one_hour=1000)
            rows = run("runs.py", Path(tmp, "-home-u-runs-r09")).splitlines()[1].split("\t")
            turns = run("perturn.py", Path(tmp, "-home-u-runs-r09"))
        # (20 + 1000 * 2 + 1000 * 0.05) * $4 / 1M + 100 * $20 / 1M
        self.assertEqual(rows[6:8] + rows[12:13], ["0", "1000", "0.0103"])
        self.assertIn("1\t0\t2\t0\t1000\t1000\t2020\t100\t0.0103", turns)


if __name__ == "__main__":
    unittest.main()

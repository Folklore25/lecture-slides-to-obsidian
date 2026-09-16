import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/obsidian-canvas-designer/scripts/obsidian-gui-lock.py"
SPEC = importlib.util.spec_from_file_location("obsidian_gui_lock", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
LOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOCK)


class GuiLockTests(unittest.TestCase):
    def setUp(self):
        self.vault = Path(tempfile.mkdtemp()) / "vault"
        self.vault.mkdir(parents=True, exist_ok=True)
        LOCK.lock_path(self.vault).unlink(missing_ok=True)

    def tearDown(self):
        LOCK.lock_path(self.vault).unlink(missing_ok=True)

    def test_acquire_and_release_roundtrip(self):
        lease = LOCK.acquire(self.vault, owner="agent-a", timeout=5)
        self.assertEqual(lease["owner"], "agent-a")
        self.assertFalse(lease["reentrant"])
        self.assertTrue(LOCK.status(self.vault)["held"])
        self.assertTrue(LOCK.release(self.vault, "agent-a"))
        self.assertFalse(LOCK.status(self.vault)["held"])

    def test_second_owner_times_out_and_is_told_who_holds_it(self):
        LOCK.acquire(self.vault, owner="agent-a", timeout=5)
        with self.assertRaises(LOCK.GuiLockTimeout) as caught:
            LOCK.acquire(self.vault, owner="agent-b", timeout=0.3, poll=0.05)
        self.assertIn("agent-a", str(caught.exception))
        LOCK.release(self.vault, "agent-a")

    def test_reentrant_acquire_by_the_same_owner_does_not_deadlock(self):
        LOCK.acquire(self.vault, owner="agent-a", timeout=5)
        again = LOCK.acquire(self.vault, owner="agent-a", timeout=0.2)
        self.assertTrue(again["reentrant"])
        LOCK.release(self.vault, "agent-a")

    def test_stale_lease_from_a_dead_process_is_reclaimed(self):
        path = LOCK.lock_path(self.vault)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "pid": 999999,
            "owner": "crashed-agent",
            "host": LOCK.socket.gethostname(),
            "acquired_at": time.time() - 600,
        }))
        lease = LOCK.acquire(self.vault, owner="agent-b", timeout=5)
        self.assertEqual(lease["owner"], "agent-b")
        self.assertFalse(lease["reentrant"])
        LOCK.release(self.vault, "agent-b")

    def test_release_by_a_different_owner_is_refused(self):
        LOCK.acquire(self.vault, owner="agent-a", timeout=5)
        self.assertFalse(LOCK.release(self.vault, "agent-b"))
        self.assertTrue(LOCK.status(self.vault)["held"])
        LOCK.release(self.vault, "agent-a")

    def test_status_reports_the_holder(self):
        LOCK.acquire(self.vault, owner="agent-a", timeout=5)
        state = LOCK.status(self.vault)
        self.assertTrue(state["held"])
        self.assertEqual(state["holder"]["owner"], "agent-a")
        self.assertEqual(state["holder"]["pid"], os.getpid())
        LOCK.release(self.vault, "agent-a")

    def test_separate_vaults_do_not_block_each_other(self):
        other = Path(tempfile.mkdtemp()) / "other-vault"
        other.mkdir(parents=True, exist_ok=True)
        LOCK.acquire(self.vault, owner="agent-a", timeout=5)
        try:
            lease = LOCK.acquire(other, owner="agent-b", timeout=2)
            self.assertEqual(lease["owner"], "agent-b")
        finally:
            LOCK.release(other, "agent-b")
            LOCK.release(self.vault, "agent-a")

    def test_independent_processes_are_serialized(self):
        worker = RENDER_WORKER = Path(tempfile.mkdtemp()) / "worker.py"
        worker.write_text(
            "import importlib.util, json, sys, time\n"
            "from pathlib import Path\n"
            "spec = importlib.util.spec_from_file_location('gui_lock', sys.argv[1])\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "owner, vault, out = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])\n"
            "with module.hold(vault, owner=owner, timeout=30):\n"
            "    enter = time.time()\n"
            "    time.sleep(0.3)\n"
            "    (out / (owner + '.json')).write_text(json.dumps({'enter': enter, 'exit': time.time()}))\n"
        )
        out = Path(tempfile.mkdtemp())
        processes = [
            subprocess.Popen(
                [sys.executable, str(worker), str(SCRIPT), f"agent-{index}", str(self.vault), str(out)]
            )
            for index in range(3)
        ]
        self.assertEqual([process.wait() for process in processes], [0, 0, 0])
        rows = sorted(
            (json.loads(path.read_text()) for path in out.glob("agent-*.json")),
            key=lambda row: row["enter"],
        )
        self.assertEqual(len(rows), 3)
        for first, second in zip(rows, rows[1:]):
            self.assertLessEqual(first["exit"], second["enter"])

    def test_cli_status_and_missing_lock(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "status", "--vault-root", str(self.vault)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["held"])

    def test_cli_acquire_failure_returns_exit_two(self):
        LOCK.acquire(self.vault, owner="holder", timeout=5)
        try:
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "acquire",
                    "--vault-root", str(self.vault), "--owner", "other", "--timeout", "0.2",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("holder", result.stdout)
        finally:
            LOCK.release(self.vault, "holder")


if __name__ == "__main__":
    unittest.main()

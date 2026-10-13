import importlib.util
import tempfile
import unittest
from pathlib import Path
FILE = Path(__file__).resolve().parents[1] / "src" / "workflow.py"
spec = importlib.util.spec_from_file_location("workflow", FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class WorkflowTests(unittest.TestCase):
    def test_replay_audit_and_role(self):
        with tempfile.TemporaryDirectory() as temp:
            flow = module.Workflow(Path(temp) / "test.db")
            submitted = flow.submit("Synthetic request", "requester", "k1")
            self.assertEqual(flow.submit("Synthetic request", "requester", "k1"), submitted)
            with self.assertRaises(PermissionError):
                flow.decide(submitted["id"], "APPROVED", "other", "viewer", "k2")
            approved = flow.decide(submitted["id"], "APPROVED", "reviewer1", "reviewer", "k2")
            self.assertEqual(flow.decide(submitted["id"], "APPROVED", "reviewer1", "reviewer", "k2"), approved)
            self.assertEqual(len(flow.audit(submitted["id"])), 2)
            with self.assertRaises(module.Conflict):
                flow.submit("Other request", "requester", "k1")

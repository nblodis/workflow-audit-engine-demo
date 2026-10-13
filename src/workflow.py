"""Synthetic approval workflow demonstrating transactions, audit logs and replay."""
import json
import sqlite3
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
 id TEXT PRIMARY KEY, description TEXT NOT NULL, state TEXT NOT NULL
 CHECK(state IN ('PENDING','APPROVED','REJECTED'))
);
CREATE TABLE IF NOT EXISTS events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL,
 action TEXT NOT NULL, actor TEXT NOT NULL, details TEXT NOT NULL,
 FOREIGN KEY(request_id) REFERENCES requests(id)
);
CREATE TABLE IF NOT EXISTS operations (
 operation_key TEXT PRIMARY KEY, kind TEXT NOT NULL,
 fingerprint TEXT NOT NULL, result TEXT NOT NULL
);
"""
class Conflict(Exception):
    pass

class Workflow:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)

    def _apply(self, key, kind, fingerprint, action):
        with self.conn:
            old = self.conn.execute("SELECT kind,fingerprint,result FROM operations WHERE operation_key=?", (key,)).fetchone()
            if old:
                if (old[0], old[1]) != (kind, fingerprint):
                    raise Conflict("idempotency key reused for a different operation")
                return json.loads(old[2])
            result = action()
            self.conn.execute("INSERT INTO operations VALUES (?,?,?,?)", (key, kind, fingerprint, json.dumps(result)))
            return result

    def submit(self, description, actor, operation_key):
        if not description.strip() or not actor.strip():
            raise ValueError("description and actor required")
        fingerprint = json.dumps([description, actor])
        def action():
            request_id = str(uuid.uuid4())
            self.conn.execute("INSERT INTO requests VALUES (?,?,?)", (request_id, description, "PENDING"))
            self.conn.execute("INSERT INTO events(request_id,action,actor,details) VALUES (?,?,?,?)", (request_id, "SUBMIT", actor, "{}"))
            return {"id": request_id, "state": "PENDING"}
        return self._apply(operation_key, "submit", fingerprint, action)

    def decide(self, request_id, decision, actor, role, operation_key):
        if role != "reviewer":
            raise PermissionError("reviewer role required")
        if decision not in ("APPROVED", "REJECTED"):
            raise ValueError("invalid decision")
        fingerprint = json.dumps([request_id, decision, actor, role])
        def action():
            current = self.conn.execute("SELECT state FROM requests WHERE id=?", (request_id,)).fetchone()
            if current is None:
                raise KeyError("unknown request")
            if current[0] != "PENDING":
                raise Conflict("request is already final")
            self.conn.execute("UPDATE requests SET state=? WHERE id=?", (decision, request_id))
            self.conn.execute("INSERT INTO events(request_id,action,actor,details) VALUES (?,?,?,?)",
                              (request_id, "DECIDE", actor, json.dumps({"decision": decision})))
            return {"id": request_id, "state": decision}
        return self._apply(operation_key, "decide", fingerprint, action)

    def audit(self, request_id):
        return self.conn.execute("SELECT action,actor,details FROM events WHERE request_id=? ORDER BY sequence", (request_id,)).fetchall()

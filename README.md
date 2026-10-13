# Workflow Audit Engine

An independently written SQLite example illustrating transactional state changes, audit trails, role checks and idempotent retries for fictional approval requests.

## Run tests

```bash
python -m unittest discover -s tests -v
```

`Workflow.submit(description, actor, operation_key)` creates a pending request. `Workflow.decide(id, decision, actor, role, operation_key)` requires the `reviewer` role and moves a pending request to an approved or rejected state. Reusing a key with different arguments raises `Conflict`. Audit entries accompany state changes.

## Engineering tradeoffs

Identity and roles are passed into this illustrative API, not authenticated. Real deployments require verified identity, permissions, migrations, concurrency handling, retention controls and security review.

**Provenance:** Independent educational implementation using fictional transactions, not an employer workflow or production system.

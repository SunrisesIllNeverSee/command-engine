"""
Tests for RuntimeState persistence — atomic writes, reload correctness.
"""
from app.audit import AuditSpine
from app.runtime import RuntimeState
from app.store import MessageStore


def _make_runtime(root):
    store = MessageStore(root / "data" / "messages.jsonl")
    audit = AuditSpine(root / "data" / "audit.jsonl")
    return RuntimeState(root=root, store=store, audit=audit)


def test_governance_persists_across_reload(runtime_root):
    rt = _make_runtime(runtime_root)
    rt.governance.mode = "HIGH_SECURITY"
    rt.governance.posture = "DEFENSE"
    rt.persist()

    reloaded = _make_runtime(runtime_root)
    assert reloaded.governance.mode == "HIGH_SECURITY"
    assert reloaded.governance.posture == "DEFENSE"


def test_no_tmp_file_left_after_persist(runtime_root):
    rt = _make_runtime(runtime_root)
    rt.persist()

    leftover = list((runtime_root / "data").glob("*.tmp"))
    assert leftover == [], f"Temp files not cleaned up: {leftover}"


def test_state_loads_cleanly_when_file_absent(runtime_root):
    # data dir exists but no state file — should load defaults without error
    (runtime_root / "data").mkdir(parents=True, exist_ok=True)
    rt = _make_runtime(runtime_root)
    assert rt.governance is not None
    assert rt.systems is not None


def test_cursors_persist_separately(runtime_root):
    rt = _make_runtime(runtime_root)
    rt.cursors["claude"] = {"general": 42}
    rt.persist()

    reloaded = _make_runtime(runtime_root)
    assert reloaded.cursors.get("claude", {}).get("general") == 42

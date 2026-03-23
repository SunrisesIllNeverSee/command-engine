"""
Tests for the SHA-256 audit chain — the core integrity claim of COMMAND Engine.
Every action is logged, hash-chained, and tamper-evident.
"""
import json

from app.moses_core.audit import AuditLedger


def test_chain_builds_correctly(tmp_path):
    ledger = AuditLedger(tmp_path / "audit.jsonl")
    ledger.log_action(component="test", action="start", detail={})
    ledger.log_action(component="test", action="step", detail={"x": 1})
    ledger.log_action(component="test", action="end", detail={})

    result = ledger.verify_integrity()
    assert result["valid"] is True
    assert result["entries_checked"] == 3


def test_each_entry_links_to_previous(tmp_path):
    ledger = AuditLedger(tmp_path / "audit.jsonl")
    ledger.log_action(component="test", action="a", detail={})
    ledger.log_action(component="test", action="b", detail={})

    entries = ledger.recent(2)
    assert entries[1]["previous_hash"] == entries[0]["hash"]


def test_tamper_detection(tmp_path):
    path = tmp_path / "audit.jsonl"
    ledger = AuditLedger(path)
    ledger.log_action(component="test", action="original", detail={})

    # Silently alter the action field
    lines = path.read_text().splitlines()
    entry = json.loads(lines[0])
    entry["action"] = "tampered"
    path.write_text(json.dumps(entry) + "\n")

    reloaded = AuditLedger(path)
    result = reloaded.verify_integrity()
    assert result["valid"] is False
    assert result["first_failure"] == 0


def test_chain_survives_reload(tmp_path):
    ledger = AuditLedger(tmp_path / "audit.jsonl")
    ledger.log_action(component="test", action="before_reload", detail={})
    last_hash = ledger.recent(1)[0]["hash"]

    reloaded = AuditLedger(tmp_path / "audit.jsonl")
    reloaded.log_action(component="test", action="after_reload", detail={})

    result = reloaded.verify_integrity()
    assert result["valid"] is True
    assert reloaded.recent(2)[1]["previous_hash"] == last_hash

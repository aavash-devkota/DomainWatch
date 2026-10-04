from domainwatch.core.alerts import AlertEngine, AlertRule
from domainwatch.core.lifecycle import classify, Lifecycle
from domainwatch.core.models import Event, Severity
from domainwatch.storage import migrate
from domainwatch.storage.db import DB


def test_alert_rule_price():
    r = AlertRule("cheap", "PriceBelowThreshold", {"price_lte": 15}, ["telegram"])
    assert r.matches(Event("PriceBelowThreshold", "x.com", "m", {"price": 12}))
    assert not r.matches(Event("PriceBelowThreshold", "x.com", "m", {"price": 20}))


def test_alert_cooldown(tmp_path):
    db = DB(tmp_path / "t.db")
    eng = AlertEngine(db)
    ev = Event("DomainAvailable", "x.com", "m")
    assert eng.process(ev)
    db.record_event(ev.type, ev.domain, ev.message, {})
    assert not eng.process(Event("DomainAvailable", "x.com", "m2"))


def test_lifecycle(tmp_path):
    assert classify(True, None) == Lifecycle.AVAILABLE
    assert classify(False, "2999-01-01") == Lifecycle.REGISTERED
    assert classify(False, "2020-01-01") == Lifecycle.EXPIRED
    assert classify(False, None, "pending delete") == Lifecycle.PENDING_DELETE


def test_score():
    from domainwatch.core.score import score_domain
    s = score_domain("sophic.dev", True, 9.99, False)
    assert 0 <= s.total <= 100 and s.parts["availability"] == 20
    s2 = score_domain("cyber-security-login.com", False, 1200, True)
    assert s2.total < s.total


def test_migrate_idempotent(tmp_path):
    db = DB(tmp_path / "t.db")
    assert migrate.migrate(db.conn) == []
    assert migrate.current_version(db.conn) >= 3

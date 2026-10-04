from domainwatch.dns import records
from domainwatch.core.models import DomainState
from domainwatch.storage.db import DB
from domainwatch.events.bus import EventBus
from domainwatch.core.models import Event


def test_db_roundtrip(tmp_path):
    db = DB(tmp_path / "t.db")
    db.add_domain("example.com", 20)
    st = DomainState(domain="example.com", available=True, price=9.99)
    db.record_check(st)
    last = db.last_check("example.com")
    assert last["price"] == 9.99
    stats = db.price_stats("example.com")
    assert stats["current"] == 9.99


def test_eventbus():
    seen = []
    bus = EventBus()
    bus.subscribe("PriceDropped", seen.append)
    bus.emit(Event("PriceDropped", "example.com", "msg"))
    assert len(seen) == 1


def test_spf_parse():
    # example.com has "v=spf1 -all"
    assert records.spf_record("example.com").startswith("v=spf1")

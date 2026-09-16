"""StrategyService tests -- versioning invariants, small-vs-big change
classification, and the pending-confirmation queue (Phase 8)."""

import pytest

from app.analytics.signal_rules import DEFAULT_RULES
from app.services.exceptions import NotFoundError
from app.services.strategy_service import InvalidStateError, StrategyService


def test_bootstraps_version_1_from_default_rules_on_a_fresh_db(db_session):
    service = StrategyService(db_session)
    active = service.get_active_version()
    assert active.version_number == 1
    assert active.status == "ACTIVE"
    assert active.rules == DEFAULT_RULES.to_dict()


def test_get_active_version_is_idempotent(db_session):
    service = StrategyService(db_session)
    first = service.get_active_version()
    second = service.get_active_version()
    assert first.id == second.id


def test_small_change_same_keys_auto_applies_and_supersedes_the_old_version(db_session):
    service = StrategyService(db_session)
    original = service.get_active_version()

    new_rules = {**DEFAULT_RULES.to_dict(), "rsi_period": 21}
    result = service.propose_change(new_rules, reason="Tuning RSI period")

    assert result.version_number == original.version_number + 1
    assert result.status == "ACTIVE"
    assert result.change_type == "AUTO_APPLIED"
    assert result.rules["rsi_period"] == 21

    refreshed_original = service.versions.get(original.id)
    assert refreshed_original.status == "SUPERSEDED"
    assert service.get_active_version().id == result.id


def test_big_change_different_keys_is_queued_not_applied(db_session):
    service = StrategyService(db_session)
    original = service.get_active_version()

    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    result = service.propose_change(new_rules, reason="Add a Bollinger-touch signal")

    assert result.status == "PENDING"
    assert result.proposed_rules == new_rules
    # Unapplied -- the active version is unchanged.
    assert service.get_active_version().id == original.id


def test_missing_key_is_also_a_big_change(db_session):
    service = StrategyService(db_session)
    original = service.get_active_version()

    new_rules = {k: v for k, v in DEFAULT_RULES.to_dict().items() if k != "institutional_window"}
    result = service.propose_change(new_rules, reason="Drop the institutional signals")

    assert result.status == "PENDING"
    assert service.get_active_version().id == original.id


def test_confirm_pending_creates_a_new_active_version(db_session):
    service = StrategyService(db_session)
    original = service.get_active_version()
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    pending = service.propose_change(new_rules, reason="Add a Bollinger-touch signal")

    new_version = service.confirm_pending(pending.id)

    assert new_version.status == "ACTIVE"
    assert new_version.change_type == "CONFIRMED"
    assert new_version.rules == new_rules
    assert service.versions.get(original.id).status == "SUPERSEDED"
    assert service.pending.get(pending.id).status == "CONFIRMED"
    assert service.pending.get(pending.id).decided_at is not None


def test_reject_pending_leaves_the_active_version_unchanged(db_session):
    service = StrategyService(db_session)
    original = service.get_active_version()
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    pending = service.propose_change(new_rules, reason="Add a Bollinger-touch signal")

    rejected = service.reject_pending(pending.id)

    assert rejected.status == "REJECTED"
    assert rejected.decided_at is not None
    assert service.get_active_version().id == original.id


def test_confirming_an_already_decided_change_raises(db_session):
    service = StrategyService(db_session)
    new_rules = {**DEFAULT_RULES.to_dict(), "bollinger_touch_enabled": True}
    pending = service.propose_change(new_rules, reason="x")
    service.reject_pending(pending.id)

    with pytest.raises(InvalidStateError):
        service.confirm_pending(pending.id)


def test_confirm_unknown_pending_change_raises_not_found(db_session):
    service = StrategyService(db_session)
    with pytest.raises(NotFoundError):
        service.confirm_pending(999)


def test_list_versions_orders_newest_first(db_session):
    service = StrategyService(db_session)
    service.get_active_version()
    service.propose_change({**DEFAULT_RULES.to_dict(), "rsi_period": 21}, reason="tweak")

    versions = service.list_versions()
    assert [v.version_number for v in versions] == [2, 1]

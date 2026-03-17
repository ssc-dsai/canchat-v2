import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from open_webui.models.users import Users
from open_webui.routers.users import get_users_per_domain


def test_get_users_per_domain_rejects_non_admin_roles():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_users_per_domain(
                start_timestamp=1,
                end_timestamp=100,
                domain=["example.com"],
                user=SimpleNamespace(role="analyst"),
            )
        )

    assert exc.value.status_code == 401


def test_get_users_per_domain_returns_empty_without_model_call(monkeypatch):
    def _unexpected_call(*args, **kwargs):
        raise AssertionError("Users.get_users_count_by_domain should not be called")

    monkeypatch.setattr(Users, "get_users_count_by_domain", _unexpected_call)

    result = asyncio.run(
        get_users_per_domain(
            start_timestamp=1,
            end_timestamp=100,
            domain=[],
            user=SimpleNamespace(role="admin"),
        )
    )

    assert result == []


def test_get_users_per_domain_merges_and_sorts_data(monkeypatch):
    calls = []

    def _fake_get_users_count_by_domain(start_ts, end_ts, domains, is_active=False):
        calls.append((start_ts, end_ts, list(domains), is_active))
        if is_active:
            return [
                {"domain": "z.com", "department": "Zeta", "user_count": 2},
                {"domain": "orphan.com", "department": "Ops", "user_count": 1},
            ]
        return [
            {"domain": "a.com", "department": "Alpha", "user_count": 10},
            {"domain": "z.com", "department": "Zeta", "user_count": 7},
        ]

    monkeypatch.setattr(
        Users, "get_users_count_by_domain", _fake_get_users_count_by_domain
    )

    result = asyncio.run(
        get_users_per_domain(
            start_timestamp=100,
            end_timestamp=200,
            domain=["a.com", "z.com"],
            user=SimpleNamespace(role="global_analyst"),
        )
    )

    assert calls == [
        (100, 200, ["a.com", "z.com"], False),
        (100, 200, ["a.com", "z.com"], True),
    ]
    assert result == [
        {
            "domain": "a.com",
            "department": "Alpha",
            "total_users": 10,
            "active_users": 0,
        },
        {
            "domain": "orphan.com",
            "department": "Ops",
            "total_users": 0,
            "active_users": 1,
        },
        {
            "domain": "z.com",
            "department": "Zeta",
            "total_users": 7,
            "active_users": 2,
        },
    ]


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filter_calls = []

    def select_from(self, *_args, **_kwargs):
        return self

    def filter(self, *conditions):
        self.filter_calls.append(conditions)
        return self

    def outerjoin(self, *_args, **_kwargs):
        return self

    def group_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _FakeDb:
    def __init__(self, query):
        self._query = query

    def query(self, *_args, **_kwargs):
        return self._query


class _FakeDbContext:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, tb):
        return False


def _install_fake_db(monkeypatch, query):
    fake_db = _FakeDb(query)

    def _fake_get_db():
        return _FakeDbContext(fake_db)

    monkeypatch.setattr("open_webui.models.users.get_db", _fake_get_db)


@pytest.mark.parametrize(
    "domains,expected_domain_filter_calls",
    [(["All"], 0), (["Tous"], 0), (["a.com", "b.com"], 1)],
)
def test_get_users_count_by_domain_domain_filter_handling(
    monkeypatch, domains, expected_domain_filter_calls
):
    fake_query = _FakeQuery(rows=[("a.com", "Alpha", 3)])
    _install_fake_db(monkeypatch, fake_query)

    result = Users.get_users_count_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain=domains,
        is_active=False,
    )

    assert result == [{"domain": "a.com", "department": "Alpha", "user_count": 3}]

    # One timestamp filter call is always present; optional domain filter adds one more.
    assert len(fake_query.filter_calls) == 1 + expected_domain_filter_calls


def test_get_users_count_by_domain_uses_expected_timestamp_field(monkeypatch):
    active_query = _FakeQuery(rows=[])
    _install_fake_db(monkeypatch, active_query)

    Users.get_users_count_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain=["a.com"],
        is_active=True,
    )

    active_filter_text = " ".join(
        str(condition)
        for conditions in active_query.filter_calls
        for condition in conditions
    ).lower()
    assert "last_active_at" in active_filter_text

    total_query = _FakeQuery(rows=[])
    _install_fake_db(monkeypatch, total_query)

    Users.get_users_count_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain=["a.com"],
        is_active=False,
    )

    total_filter_text = " ".join(
        str(condition)
        for conditions in total_query.filter_calls
        for condition in conditions
    ).lower()
    assert "created_at" in total_filter_text

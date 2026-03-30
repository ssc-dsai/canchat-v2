import asyncio
from types import SimpleNamespace

import pytest

from open_webui.models.users import Users
from open_webui.routers.users import get_users_per_domain


def _stub_prompt_users(monkeypatch, return_value=None):
    """Stub get_prompt_users_by_domain to return empty dict by default."""
    prompt_calls = []

    def _fake(start_ts, end_ts, domain=None):
        prompt_calls.append((start_ts, end_ts, domain))
        return return_value if return_value is not None else {}

    monkeypatch.setattr(Users, "get_prompt_users_by_domain", _fake)
    return prompt_calls


@pytest.mark.parametrize("domain", [None, "example.com"])
def test_get_users_per_domain_passes_single_domain_filter(monkeypatch, domain):
    calls = []

    def _fake_get_users_count_by_domain(
        start_ts, end_ts, domain_filter, is_active=False
    ):
        calls.append((start_ts, end_ts, domain_filter, is_active))
        return []

    monkeypatch.setattr(
        Users, "get_users_count_by_domain", _fake_get_users_count_by_domain
    )
    prompt_calls = _stub_prompt_users(monkeypatch)

    result = asyncio.run(
        get_users_per_domain(
            start_timestamp=1,
            end_timestamp=100,
            domain=domain,
            user=SimpleNamespace(role="admin"),
        )
    )

    assert result == []
    assert calls == [
        (1, 100, domain, False),
        (1, 100, domain, True),
    ]
    assert prompt_calls == [(1, 100, domain)]


def test_get_users_per_domain_merges_and_sorts_data(monkeypatch):
    calls = []

    def _fake_get_users_count_by_domain(start_ts, end_ts, domain, is_active=False):
        calls.append((start_ts, end_ts, domain, is_active))
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
    _stub_prompt_users(monkeypatch, {"z.com": 5, "orphan.com": 1})

    result = asyncio.run(
        get_users_per_domain(
            start_timestamp=100,
            end_timestamp=200,
            domain="a.com",
            user=SimpleNamespace(role="global_analyst"),
        )
    )

    assert calls == [
        (100, 200, "a.com", False),
        (100, 200, "a.com", True),
    ]
    assert result == [
        {
            "domain": "a.com",
            "department": "Alpha",
            "total_users": 10,
            "active_users": 0,
            "prompt_users": 0,
        },
        {
            "domain": "orphan.com",
            "department": "Ops",
            "total_users": 0,
            "active_users": 1,
            "prompt_users": 1,
        },
        {
            "domain": "z.com",
            "department": "Zeta",
            "total_users": 7,
            "active_users": 2,
            "prompt_users": 5,
        },
    ]


@pytest.mark.parametrize("requested_domain", [None, "other.com"])
def test_get_users_per_domain_forces_analyst_domain(monkeypatch, requested_domain):
    calls = []

    def _fake_get_users_count_by_domain(
        start_ts, end_ts, domain_filter, is_active=False
    ):
        calls.append((start_ts, end_ts, domain_filter, is_active))
        return []

    monkeypatch.setattr(
        Users, "get_users_count_by_domain", _fake_get_users_count_by_domain
    )
    prompt_calls = _stub_prompt_users(monkeypatch)

    result = asyncio.run(
        get_users_per_domain(
            start_timestamp=1,
            end_timestamp=100,
            domain=requested_domain,
            user=SimpleNamespace(role="analyst", domain="analyst.example.com"),
        )
    )

    assert result == []
    assert calls == [
        (1, 100, "analyst.example.com", False),
        (1, 100, "analyst.example.com", True),
    ]
    assert prompt_calls == [(1, 100, "analyst.example.com")]


def test_get_users_per_domain_includes_selected_end_day_for_date_ranges(monkeypatch):
    calls = []

    def _fake_get_users_count_by_domain(start_ts, end_ts, domain, is_active=False):
        calls.append((start_ts, end_ts, domain, is_active))
        return []

    monkeypatch.setattr(
        Users, "get_users_count_by_domain", _fake_get_users_count_by_domain
    )
    prompt_calls = _stub_prompt_users(monkeypatch)

    result = asyncio.run(
        get_users_per_domain(
            start_timestamp=86400,
            end_timestamp=172800,
            domain="a.com",
            user=SimpleNamespace(role="admin"),
        )
    )

    assert result == []
    # Both queries receive end_timestamp + 86400 so the selected end day is inclusive
    assert calls == [
        (86400, 259200, "a.com", False),
        (86400, 259200, "a.com", True),
    ]
    assert prompt_calls == [(86400, 259200, "a.com")]


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
    def __init__(self, queries):
        self._queries = list(queries)
        self._last_query = self._queries[-1] if self._queries else None

    def query(self, *_args, **_kwargs):
        if self._queries:
            self._last_query = self._queries.pop(0)
        return self._last_query


class _FakeDbContext:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, tb):
        return False


def _install_fake_db(monkeypatch, query):
    fake_db = _FakeDb(query if isinstance(query, (list, tuple)) else [query])

    def _fake_get_db():
        return _FakeDbContext(fake_db)

    monkeypatch.setattr("open_webui.models.users.get_db", _fake_get_db)


@pytest.mark.parametrize(
    "domain,expected_domain_filter_calls",
    [(None, 0), ("a.com", 1)],
)
def test_get_users_count_by_domain_domain_filter_handling(
    monkeypatch, domain, expected_domain_filter_calls
):
    fake_query = _FakeQuery(rows=[("a.com", "Alpha", 3)])
    _install_fake_db(monkeypatch, [fake_query])

    result = Users.get_users_count_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain=domain,
        is_active=False,
    )

    assert result == [
        {
            "domain": "a.com",
            "department": "Alpha",
            "user_count": 3,
        }
    ]

    # One timestamp filter call is always present; optional domain filter adds one more.
    assert len(fake_query.filter_calls) == 1 + expected_domain_filter_calls


def test_get_users_count_by_domain_uses_expected_timestamp_field(monkeypatch):
    active_query = _FakeQuery(rows=[])
    _install_fake_db(monkeypatch, [active_query])

    Users.get_users_count_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain="a.com",
        is_active=True,
    )

    active_filter_text = " ".join(
        str(condition)
        for conditions in active_query.filter_calls
        for condition in conditions
    ).lower()
    assert "last_active_at" in active_filter_text

    total_query = _FakeQuery(rows=[])
    _install_fake_db(monkeypatch, [total_query])

    Users.get_users_count_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain="a.com",
        is_active=False,
    )

    total_filter_text = " ".join(
        str(condition)
        for conditions in total_query.filter_calls
        for condition in conditions
    ).lower()
    assert "created_at" in total_filter_text


def test_get_prompt_users_by_domain(monkeypatch):
    prompt_query = _FakeQuery(rows=[("a.com", 2), ("z.com", 1)])
    _install_fake_db(monkeypatch, [prompt_query])

    result = Users.get_prompt_users_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain=None,
    )

    assert result == {"a.com": 2, "z.com": 1}


def test_get_prompt_users_by_domain_with_domain_filter(monkeypatch):
    prompt_query = _FakeQuery(rows=[("a.com", 2)])
    _install_fake_db(monkeypatch, [prompt_query])

    result = Users.get_prompt_users_by_domain(
        start_timestamp=100,
        end_timestamp=200,
        domain="a.com",
    )

    assert result == {"a.com": 2}
    # timestamp filter + domain filter
    assert len(prompt_query.filter_calls) == 2

"""Key lifecycle rules (services/keys.py) and the operator CLI built on them."""

from uuid import UUID, uuid4

import pytest

from app.db.pools import Identity
from app.services import keys
from app.services.common import Denied, UserError
from app.worker import __main__ as cli
from app.worker.seed import uid
from tests.integration.mcp_helpers import call

# Users not touched by other tests, so their key counts are predictable.
OWNER = uid("user", "student30")
OTHER = uid("user", "student31")
ADMIN = uid("user", "admin")

owner_actor = Identity(user_id=OWNER, role="student")
other_actor = Identity(user_id=OTHER, role="student")
admin_actor = Identity(user_id=ADMIN, role="admin")


@pytest.fixture(autouse=True)
def clean_keys(owner):
    def wipe():
        owner.execute(
            """DELETE FROM audit_log
               WHERE key_id IN (SELECT id FROM api_keys WHERE user_id = ANY(%s))
                  OR (action LIKE 'key.%%' AND (user_id = ANY(%s) OR user_id IS NULL))""",
            ([OWNER, OTHER], [OWNER, OTHER, ADMIN]),
        )
        owner.execute("DELETE FROM api_keys WHERE user_id = ANY(%s)", ([OWNER, OTHER],))
        owner.commit()

    wipe()
    yield
    wipe()


def test_issued_key_works_and_is_listed_without_secrets(client):
    issued = keys.issue_key(owner_actor, OWNER, "laptop", days=30)
    assert issued["key"].startswith(f"afx_{issued['prefix']}_")
    assert call(client, issued["key"], "attendance_rule").status_code == 200

    listed = keys.list_keys(owner_actor, OWNER)
    assert [k["prefix"] for k in listed] == [issued["prefix"]]
    assert listed[0]["status"] == "active"
    assert "key" not in listed[0] and "secret_hash" not in listed[0]


@pytest.mark.parametrize("days", [0, -1, 366])
def test_every_key_must_expire_within_a_year(days):
    with pytest.raises(UserError, match="1 to 365 days"):
        keys.issue_key(owner_actor, OWNER, "x", days=days)


@pytest.mark.parametrize("name", ["", "   ", "x" * 61, "drop<script>"])
def test_key_names_are_validated(name):
    with pytest.raises(UserError, match="Key name"):
        keys.issue_key(owner_actor, OWNER, name)


def test_nobody_mints_keys_for_someone_else():
    with pytest.raises(Denied):
        keys.issue_key(other_actor, OWNER, "sneaky")
    with pytest.raises(Denied):
        keys.issue_key(admin_actor, OWNER, "admin cannot either")
    assert keys.list_keys(None, OWNER) == []


def test_at_most_ten_active_keys():
    for i in range(keys.MAX_ACTIVE_KEYS):
        keys.issue_key(owner_actor, OWNER, f"k{i}")
    with pytest.raises(UserError, match="already have 10 active keys"):
        keys.issue_key(owner_actor, OWNER, "one too many")
    # revoking one frees a slot
    first = keys.list_keys(owner_actor, OWNER)[0]
    keys.revoke_key(owner_actor, UUID(first["id"]))
    keys.issue_key(owner_actor, OWNER, "replacement")


def test_revoked_key_stops_working_on_the_next_request(client):
    issued = keys.issue_key(owner_actor, OWNER, "phone")
    assert call(client, issued["key"], "attendance_rule").status_code == 200
    result = keys.revoke_key(owner_actor, UUID(issued["id"]))
    assert result == {"id": issued["id"], "status": "revoked", "was_already_revoked": False}
    assert call(client, issued["key"], "attendance_rule").status_code == 401
    again = keys.revoke_key(owner_actor, UUID(issued["id"]))
    assert again["was_already_revoked"] is True
    assert keys.list_keys(owner_actor, OWNER)[0]["status"] == "revoked"


def test_others_cannot_see_or_revoke_your_keys_but_admins_can(client):
    issued = keys.issue_key(owner_actor, OWNER, "desktop")
    key_id = UUID(issued["id"])

    with pytest.raises(keys.KeyNotFound) as stranger:
        keys.revoke_key(other_actor, key_id)
    with pytest.raises(keys.KeyNotFound) as missing:
        keys.revoke_key(other_actor, uuid4())
    assert str(stranger.value) == str(missing.value)  # indistinguishable
    with pytest.raises(Denied):
        keys.list_keys(other_actor, OWNER)

    assert call(client, issued["key"], "attendance_rule").status_code == 200
    assert len(keys.list_keys(admin_actor, OWNER)) == 1
    keys.revoke_key(admin_actor, key_id)
    assert call(client, issued["key"], "attendance_rule").status_code == 401


def test_key_actions_are_audited(owner):
    issued = keys.issue_key(owner_actor, OWNER, "audited")
    keys.revoke_key(admin_actor, UUID(issued["id"]))
    with pytest.raises(Denied):
        keys.issue_key(other_actor, OWNER, "nope")
    rows = owner.execute(
        """SELECT user_id, surface, action, status, args_hash FROM audit_log
           WHERE action LIKE 'key.%%' AND user_id = ANY(%s) ORDER BY id""",
        ([OWNER, OTHER, ADMIN],),
    ).fetchall()
    assert [(r[0], r[1], r[2], r[3]) for r in rows] == [
        (OWNER, "api", "key.create", "ok"),
        (ADMIN, "api", "key.revoke", "ok"),
        (OTHER, "api", "key.create", "denied"),
    ]
    assert all(len(r[4]) == 64 for r in rows)  # hashed arguments only


def test_operator_cli_create_list_revoke(client, owner):
    out = cli.create_key("student30@attendfx.test", "cli test", 7)
    full_key = out.splitlines()[0]
    prefix = full_key.split("_")[1]
    assert call(client, full_key, "attendance_rule").status_code == 200

    listing = cli.list_keys("student30@attendfx.test")
    assert prefix in listing and "active" in listing and full_key not in listing

    assert cli.revoke_key(prefix) == f"Revoked key {prefix}."
    assert cli.revoke_key(prefix) == "Already revoked."
    assert call(client, full_key, "attendance_rule").status_code == 401

    surfaces = owner.execute(
        "SELECT DISTINCT surface FROM audit_log WHERE action LIKE 'key.%%' AND user_id IS NULL"
    ).fetchall()
    assert surfaces == [("cli",)]

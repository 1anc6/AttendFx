"""Account (change password) and the admin People API: create, import, reset, unlock, turn off."""

import pytest
from argon2 import PasswordHasher

from app.worker.seed import uid
from tests.integration.mcp_helpers import call
from tests.integration.test_web_api import new_browser, sign_in, signed_in

ADMIN_EMAIL = "admin@attendfx.test"
ADMIN = uid("user", "admin")
# Seeded users no other test touches.
SELF = "student35@attendfx.test"
TARGET = "student36@attendfx.test"
TEACHER = "teacher5@attendfx.test"
SEEDED = [uid("user", n) for n in ("student35", "student36", "teacher5")]
NEW_DOMAIN = "people.test"  # accounts the tests create, deleted afterwards
NEW_PASSWORD = "correct horse battery staple"


@pytest.fixture(autouse=True)
def clean(owner, settings):
    seed_hash = PasswordHasher().hash(settings.seed_password)

    def wipe():
        created = [
            r[0]
            for r in owner.execute(
                "SELECT id FROM users WHERE email LIKE %s", (f"%@{NEW_DOMAIN}",)
            ).fetchall()
        ]
        everyone = SEEDED + created
        owner.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s) "
            "OR key_id IN (SELECT id FROM api_keys WHERE user_id = ANY(%s)) "
            "OR (user_id = %s AND (action LIKE 'person.%%' OR action LIKE 'web.%%'))",
            (everyone, everyone, ADMIN),
        )
        owner.execute("DELETE FROM api_keys WHERE user_id = ANY(%s)", (everyone,))
        owner.execute("DELETE FROM web_sessions WHERE user_id = ANY(%s)", (everyone + [ADMIN],))
        owner.execute("DELETE FROM users WHERE id = ANY(%s)", (created,))
        owner.execute(
            "UPDATE users SET failed_logins = 0, locked_until = NULL, disabled_at = NULL, "
            "must_change_password = false, password_hash = %s WHERE id = ANY(%s)",
            (seed_hash, SEEDED),
        )
        owner.commit()

    wipe()
    yield
    wipe()


def admin(settings):
    """A signed-in admin browser and its CSRF header."""
    b = new_browser()
    return b, {"X-CSRF-Token": signed_in(b, settings, ADMIN_EMAIL)}


def find(b, email):
    people = b.get("/api/people", params={"q": email}).json()["people"]
    return next(p for p in people if p["email"] == email)


def change(b, h, current, new):
    return b.post(
        "/api/account/password",
        json={"current_password": current, "new_password": new},
        headers=h,
    )


# ---- Account: change your own password -------------------------------------------------


def test_change_password_ends_your_other_sessions(settings):
    laptop, phone = new_browser(), new_browser()
    h = {"X-CSRF-Token": signed_in(laptop, settings, SELF)}
    signed_in(phone, settings, SELF)

    r = change(laptop, h, settings.seed_password, NEW_PASSWORD)
    assert r.status_code == 200 and r.json()["must_change_password"] is False
    assert laptop.get("/api/me").status_code == 200  # the session that changed it stays
    assert phone.get("/api/me").status_code == 401  # every other session is ended

    other = new_browser()
    assert sign_in(other, SELF, settings.seed_password).status_code == 401
    assert sign_in(other, SELF, NEW_PASSWORD).status_code == 200


def test_change_password_needs_the_current_one_and_counts_toward_lockout(settings):
    b = new_browser()
    h = {"X-CSRF-Token": signed_in(b, settings, SELF)}
    wrong = change(b, h, "not-it", NEW_PASSWORD)
    assert wrong.status_code == 400 and wrong.json()["detail"] == "Your current password is wrong."
    for _ in range(settings.login_max_failures - 2):
        change(b, h, "not-it", NEW_PASSWORD)
    locked = change(b, h, "not-it", NEW_PASSWORD)
    assert locked.status_code == 423
    # Locked now: even the right current password is refused.
    assert change(b, h, settings.seed_password, NEW_PASSWORD).status_code == 423


@pytest.mark.parametrize(
    ("new", "message"),
    [
        ("short", "at least 12"),
        ("x" * 129, "at most 128"),
        ("aaaaaaaaaaaaaaaa", "too easy"),
        (SELF, "email"),
    ],
)
def test_weak_new_passwords_are_refused(settings, new, message):
    b = new_browser()
    h = {"X-CSRF-Token": signed_in(b, settings, SELF)}
    r = change(b, h, settings.seed_password, new)
    assert r.status_code == 400 and message in r.json()["detail"]


def test_same_password_is_refused(settings):
    b = new_browser()
    h = {"X-CSRF-Token": signed_in(b, settings, SELF)}
    r = change(b, h, settings.seed_password, settings.seed_password)
    assert r.status_code == 400 and "different" in r.json()["detail"]


def test_change_password_needs_csrf(settings):
    b = new_browser()
    signed_in(b, settings, SELF)
    r = b.post(
        "/api/account/password",
        json={"current_password": settings.seed_password, "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 403


# ---- People: who may use it -------------------------------------------------------------


@pytest.mark.parametrize("email", [SELF, TEACHER])
def test_people_is_admin_only(settings, email):
    b = new_browser()
    h = {"X-CSRF-Token": signed_in(b, settings, email)}
    assert b.get("/api/people").status_code == 403
    body = {"name": "Mallory", "email": f"mallory@{NEW_DOMAIN}", "role": "admin"}
    assert b.post("/api/people", json=body, headers=h).status_code == 403
    assert (
        b.post(f"/api/people/{ADMIN}/disabled", json={"disabled": True}, headers=h).status_code
        == 403
    )


def test_people_needs_csrf(settings):
    b, _ = admin(settings)
    body = {"name": "No Token", "email": f"no-token@{NEW_DOMAIN}", "role": "student"}
    assert b.post("/api/people", json=body).status_code == 403


def test_admin_lists_and_filters_people(settings):
    b, _ = admin(settings)
    r = b.get("/api/people")
    assert r.status_code == 200
    data = r.json()
    assert data["counts"]["total"] >= 46 and data["counts"]["admin"] >= 1
    assert data["page_size"] == 25 and len(data["people"]) == 25
    assert "$argon2" not in r.text and "password_hash" not in r.text

    teachers = b.get("/api/people", params={"role": "teacher"}).json()
    assert teachers["total"] == 5 and {p["role"] for p in teachers["people"]} == {"teacher"}

    one = b.get("/api/people", params={"q": "STUDENT35@"}).json()
    assert [p["email"] for p in one["people"]] == [SELF]
    # LIKE wildcards in the search are literal, not patterns.
    assert b.get("/api/people", params={"q": "%"}).json()["total"] == 0

    assert b.get("/api/people", params={"status": "nope"}).status_code == 422
    assert b.get("/api/people", params={"page": 0}).status_code == 422


# ---- Create, then first sign-in with the temporary password ----------------------------


def test_new_person_must_choose_a_password_before_anything_else(settings):
    b, h = admin(settings)
    email = f"new.teacher@{NEW_DOMAIN}"
    r = b.post(
        "/api/people",
        json={"name": "  New   Teacher ", "email": email.upper(), "role": "teacher"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    made = r.json()
    assert made["name"] == "New Teacher" and made["email"] == email
    temp = made["temporary_password"]
    assert len(temp) == 19 and temp.count("-") == 3

    listed = find(b, email)
    assert listed["must_change_password"] is True and listed["last_sign_in_at"] is None

    them = new_browser()
    me = sign_in(them, email, temp)
    assert me.status_code == 200 and me.json()["must_change_password"] is True
    th = {"X-CSRF-Token": me.json()["csrf_token"]}
    blocked = them.get("/api/keys")
    assert blocked.status_code == 403 and blocked.json()["detail"] == "Choose a new password first."
    assert them.post("/api/keys", json={"name": "laptop"}, headers=th).status_code == 403

    assert change(them, th, temp, NEW_PASSWORD).status_code == 200
    assert them.get("/api/keys").status_code == 200
    assert find(b, email)["last_sign_in_at"] is not None


def test_create_refuses_bad_or_taken_details(settings):
    b, h = admin(settings)
    taken = b.post(
        "/api/people", json={"name": "Dup", "email": SELF.upper(), "role": "student"}, headers=h
    )
    assert taken.status_code == 400 and "already has that email" in taken.json()["detail"]
    for body in (
        {"name": "Bad Email", "email": "not-an-email", "role": "student"},
        {"name": "", "email": f"blank@{NEW_DOMAIN}", "role": "student"},
        {"name": "Bad Role", "email": f"role@{NEW_DOMAIN}", "role": "dean"},
    ):
        assert b.post("/api/people", json=body, headers=h).status_code == 400


# ---- CSV import ------------------------------------------------------------------------

GOOD_CSV = (
    "﻿Name,Email,Role,Notes\n"
    f"Asha Rao,asha@{NEW_DOMAIN},student,first year\n"
    "\n"
    f'"Iyer, Dev",dev@{NEW_DOMAIN},Teacher,\n'
)


def test_import_checks_first_then_creates_everyone(settings, owner):
    b, h = admin(settings)
    preview = b.post("/api/people/import", json={"csv": GOOD_CSV, "dry_run": True}, headers=h)
    assert preview.status_code == 200
    data = preview.json()
    assert data["created"] is False and data["errors"] == []
    assert [(r["line"], r["name"], r["role"]) for r in data["rows"]] == [
        (2, "Asha Rao", "student"),
        (4, "Iyer, Dev", "teacher"),
    ]
    count = "SELECT count(*) FROM users WHERE email LIKE %s"
    assert owner.execute(count, (f"%@{NEW_DOMAIN}",)).fetchone() == (0,)

    done = b.post("/api/people/import", json={"csv": GOOD_CSV, "dry_run": False}, headers=h).json()
    assert done["created"] is True and len(done["people"]) == 2
    assert all(len(p["temporary_password"]) == 19 for p in done["people"])
    assert owner.execute(count, (f"%@{NEW_DOMAIN}",)).fetchone() == (2,)
    asha = next(p for p in done["people"] if p["name"] == "Asha Rao")
    assert sign_in(new_browser(), asha["email"], asha["temporary_password"]).status_code == 200


def test_import_with_any_error_creates_nobody(settings, owner):
    b, h = admin(settings)
    text = (
        "name,email,role\n"
        f"Ok Person,ok@{NEW_DOMAIN},student\n"
        f"Taken,{SELF},student\n"
        "No Email,,student\n"
        f"Twice,ok@{NEW_DOMAIN},student\n"
        f"Odd Role,odd@{NEW_DOMAIN},principal\n"
    )
    r = b.post("/api/people/import", json={"csv": text, "dry_run": False}, headers=h).json()
    assert r["created"] is False and r["people"] == []
    assert [(e["line"], e["message"]) for e in r["errors"]] == [
        (3, "Someone already has this email."),
        (4, "That doesn't look like an email address."),
        (5, "Same email as line 2."),
        (6, "Role must be student, teacher or admin."),
    ]
    assert owner.execute(
        "SELECT count(*) FROM users WHERE email LIKE %s", (f"%@{NEW_DOMAIN}",)
    ).fetchone() == (0,)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "empty"),
        ("email,role\nx@y.test,student\n", "Missing: name"),
        ("name,email,role\n", "No people found"),
        (
            "name,email,role\n" + "".join(f"P{i},p{i}@{NEW_DOMAIN},student\n" for i in range(201)),
            "at most 200",
        ),
    ],
)
def test_import_refuses_unusable_files(settings, text, message):
    b, h = admin(settings)
    r = b.post("/api/people/import", json={"csv": text}, headers=h)
    assert r.status_code == 400 and message in r.json()["detail"]


# ---- Reset, unlock, turn off -----------------------------------------------------------


def test_reset_password_signs_them_out_and_clears_the_lock(settings, owner):
    target = new_browser()
    signed_in(target, settings, TARGET)
    owner.execute(
        "UPDATE users SET locked_until = now() + interval '10 minutes', failed_logins = 3 "
        "WHERE id = %s",
        (SEEDED[1],),
    )
    owner.commit()

    b, h = admin(settings)
    person = find(b, TARGET)
    assert person["locked_until"] is not None
    r = b.post(f"/api/people/{person['id']}/reset-password", headers=h)
    assert r.status_code == 200
    temp = r.json()["temporary_password"]

    assert target.get("/api/me").status_code == 401
    assert sign_in(new_browser(), TARGET, settings.seed_password).status_code == 401
    again = sign_in(new_browser(), TARGET, temp)
    assert again.status_code == 200 and again.json()["must_change_password"] is True


def test_unlock_clears_a_lockout(settings):
    for _ in range(settings.login_max_failures):
        sign_in(new_browser(), TARGET, "wrong")
    assert sign_in(new_browser(), TARGET, settings.seed_password).status_code == 423

    b, h = admin(settings)
    person_id = find(b, TARGET)["id"]
    locked = b.get("/api/people", params={"status": "locked"}).json()["people"]
    assert person_id in [p["id"] for p in locked]
    r = b.post(f"/api/people/{person_id}/unlock", headers=h)
    assert r.json() == {"id": person_id, "unlocked": True}
    assert sign_in(new_browser(), TARGET, settings.seed_password).status_code == 200


def test_turning_an_account_off_stops_sign_in_sessions_and_keys(settings, client):
    target = new_browser()
    th = {"X-CSRF-Token": signed_in(target, settings, TARGET)}
    key = target.post("/api/keys", json={"name": "laptop"}, headers=th).json()["key"]
    assert call(client, key, "attendance_rule").status_code == 200

    b, h = admin(settings)
    person_id = find(b, TARGET)["id"]
    off = b.post(f"/api/people/{person_id}/disabled", json={"disabled": True}, headers=h)
    assert off.status_code == 200

    assert target.get("/api/me").status_code == 401
    assert call(client, key, "attendance_rule").status_code == 401
    refused = sign_in(new_browser(), TARGET, settings.seed_password)
    assert refused.status_code == 403 and "turned off" in refused.json()["detail"]
    # A wrong password still gets the ordinary answer, so strangers learn nothing.
    assert sign_in(new_browser(), TARGET, "wrong").json() == {
        "detail": "Email or password is wrong."
    }
    assert find(b, TARGET)["disabled_at"] is not None

    on = b.post(f"/api/people/{person_id}/disabled", json={"disabled": False}, headers=h)
    assert on.status_code == 200
    assert call(client, key, "attendance_rule").status_code == 200
    assert sign_in(new_browser(), TARGET, settings.seed_password).status_code == 200


def test_admins_cannot_reset_or_turn_off_themselves(settings):
    b, h = admin(settings)
    reset = b.post(f"/api/people/{ADMIN}/reset-password", headers=h)
    assert reset.status_code == 400 and "Account page" in reset.json()["detail"]
    off = b.post(f"/api/people/{ADMIN}/disabled", json={"disabled": True}, headers=h)
    assert off.status_code == 400 and "your own account" in off.json()["detail"]
    assert b.get("/api/me").status_code == 200


def test_unknown_people_are_404(settings):
    b, h = admin(settings)
    missing = "00000000-0000-4000-8000-000000000000"
    for path in ("reset-password", "unlock"):
        r = b.post(f"/api/people/{missing}/{path}", headers=h)
        assert r.status_code == 404 and r.json() == {"detail": "No such person."}


def test_admin_actions_are_audited(settings, owner):
    b, h = admin(settings)
    person_id = find(b, TARGET)["id"]
    b.post(f"/api/people/{person_id}/unlock", headers=h)
    b.post(f"/api/people/{person_id}/reset-password", headers=h)
    b.post(
        "/api/people",
        json={"name": "Aud It", "email": f"audit@{NEW_DOMAIN}", "role": "student"},
        headers=h,
    )
    rows = owner.execute(
        "SELECT action, status FROM audit_log WHERE user_id = %s AND action LIKE 'person.%%' "
        "ORDER BY id",
        (ADMIN,),
    ).fetchall()
    assert rows == [
        ("person.unlock", "not_locked"),
        ("person.reset_password", "ok"),
        ("person.create", "ok"),
    ]

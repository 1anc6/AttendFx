"""Admin account management: list, create, import from CSV, reset password, unlock, turn off.

Rules:
- Only admins. The repo runs as afx_auth, which sees every account, so the check lives here
  as well as on the route.
- New and reset accounts get a temporary password, shown once, that must be changed at the
  next sign-in. Admins never choose or see a person's real password.
- Admins cannot reset, turn off or unlock themselves here: that is what Account is for, and
  it keeps at least one working admin.
- Changing someone's role is not offered: it changes what their keys can read, and belongs in
  the data sync, not a web form.
"""

import csv
import io
import re
from typing import Any
from uuid import UUID

from app.audit import log as audit
from app.auth import web
from app.db.pools import Identity
from app.repos import people_repo
from app.services.common import Denied, UserError

ROLES = ("student", "teacher", "admin")
STATUSES = tuple(people_repo.STATUS_SQL)
MAX_IMPORT_ROWS = 200
MAX_IMPORT_CHARS = 200_000
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class PersonNotFound(UserError):
    def __init__(self) -> None:
        super().__init__("No such person.")


def _require_admin(actor: Identity) -> None:
    if actor.role != "admin":
        raise Denied("Only admins can manage accounts.")


def _audit(actor: Identity, action: str, args: dict, status: str) -> None:
    audit.record(
        actor, surface="api", action=action, args=args, status=status, latency_ms=0, request_id=None
    )


def clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not 1 <= len(name) <= 100 or CONTROL.search(name):
        raise UserError("Name must be 1 to 100 characters.")
    return name


def clean_email(raw: str) -> str:
    email = raw.strip().lower()
    if len(email) > 254 or not EMAIL.match(email):
        raise UserError("That doesn't look like an email address.")
    return email


def clean_role(raw: str) -> str:
    role = raw.strip().lower()
    if role not in ROLES:
        raise UserError("Role must be student, teacher or admin.")
    return role


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _person(row: people_repo.PersonRow) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "email": row.email,
        "role": row.role,
        "created_at": row.created_at.isoformat(),
        "last_sign_in_at": _iso(row.last_sign_in_at),
        "locked_until": _iso(row.locked_until),
        "disabled_at": _iso(row.disabled_at),
        "must_change_password": row.must_change_password,
        "active_keys": row.active_keys,
    }


def list_people(
    actor: Identity,
    *,
    search: str = "",
    role: str | None = None,
    status: str = "all",
    page: int = 1,
) -> dict[str, Any]:
    _require_admin(actor)
    if role is not None and role not in ROLES:
        raise UserError("Role must be student, teacher or admin.")
    if status not in STATUSES:
        raise UserError(f"Status must be one of: {', '.join(STATUSES)}.")
    if page < 1:
        raise UserError("Page must be 1 or more.")
    rows, total = people_repo.list_people(
        search=search.strip()[:100], role=role, status=status, page=page
    )
    return {
        "people": [_person(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": people_repo.PAGE_SIZE,
        "counts": people_repo.counts(),
    }


def _target(actor: Identity, person_id: UUID, action: str) -> tuple:
    person = people_repo.get_person(person_id)
    if person is None:
        _audit(actor, action, {"person_id": person_id}, "not_found")
        raise PersonNotFound()
    return person


def _not_self(actor: Identity, person_id: UUID, action: str, message: str) -> None:
    if actor.user_id == person_id:
        _audit(actor, action, {"person_id": person_id}, "denied")
        raise UserError(message)


def _create(rows: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    """Create accounts for already-validated (name, email, role) rows, all or none."""
    passwords = [web.new_temporary_password() for _ in rows]
    new = [
        people_repo.NewPerson(name, email, role, web.hash_password(pw))
        for (name, email, role), pw in zip(rows, passwords, strict=True)
    ]
    try:
        ids = people_repo.create_people(new)
    except people_repo.EmailTaken:
        raise UserError(
            "One of those emails was just taken. Check the list and try again."
        ) from None
    return [
        {"id": str(i), "name": n, "email": e, "role": r, "temporary_password": pw}
        for i, (n, e, r), pw in zip(ids, rows, passwords, strict=True)
    ]


def create_person(actor: Identity, name: str, email: str, role: str) -> dict[str, Any]:
    _require_admin(actor)
    row = (clean_name(name), clean_email(email), clean_role(role))
    if people_repo.existing_emails([row[1]]):
        _audit(actor, "person.create", {"email": row[1]}, "exists")
        raise UserError("Someone already has that email.")
    created = _create([row])[0]
    _audit(actor, "person.create", {"person_id": created["id"], "role": row[2]}, "ok")
    return created


def _parse_csv(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Valid rows and per-line errors. Needs a header row with name, email and role."""
    if len(text) > MAX_IMPORT_CHARS:
        raise UserError("That file is too big. Import at most 200 people at a time.")
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    try:
        header = next(reader, None)
        if header is None:
            raise UserError("The file is empty.")
        columns = [h.strip().lower() for h in header]
        missing = [c for c in ("name", "email", "role") if c not in columns]
        if missing:
            raise UserError(f"The first line must name the columns. Missing: {', '.join(missing)}.")
        at = {c: columns.index(c) for c in ("name", "email", "role")}

        rows: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        for record in reader:
            line = reader.line_num
            if not any(cell.strip() for cell in record):
                continue
            if len(rows) + len(errors) >= MAX_IMPORT_ROWS:
                raise UserError(f"Import at most {MAX_IMPORT_ROWS} people at a time.")
            cells = {c: record[i] if i < len(record) else "" for c, i in at.items()}
            try:
                name = clean_name(cells["name"])
                email = clean_email(cells["email"])
                role = clean_role(cells["role"])
            except UserError as exc:
                errors.append({"line": line, "message": str(exc)})
                continue
            if email in seen:
                errors.append({"line": line, "message": f"Same email as line {seen[email]}."})
                continue
            seen[email] = line
            rows.append({"line": line, "name": name, "email": email, "role": role})
    except csv.Error as exc:
        raise UserError(f"Line {reader.line_num}: this is not valid CSV ({exc}).") from None

    taken = people_repo.existing_emails([r["email"] for r in rows])
    errors += [
        {"line": r["line"], "message": "Someone already has this email."}
        for r in rows
        if r["email"] in taken
    ]
    rows = [r for r in rows if r["email"] not in taken]
    errors.sort(key=lambda e: e["line"])
    return rows, errors


def import_people(actor: Identity, text: str, *, dry_run: bool) -> dict[str, Any]:
    """Check a CSV and, unless dry_run, create everyone in it. Any error means nobody is
    created, so a file never half-imports."""
    _require_admin(actor)
    rows, errors = _parse_csv(text)
    if not rows and not errors:
        raise UserError("No people found under the header line.")
    if dry_run or errors:
        if not dry_run:
            _audit(actor, "person.import", {"rows": len(rows)}, "rejected")
        return {"rows": rows, "errors": errors, "created": False, "people": []}
    people = _create([(r["name"], r["email"], r["role"]) for r in rows])
    _audit(actor, "person.import", {"count": len(people)}, "ok")
    return {"rows": rows, "errors": [], "created": True, "people": people}


def reset_password(actor: Identity, person_id: UUID) -> dict[str, Any]:
    """New temporary password; clears any lockout and signs them out of the web app. Their
    access keys keep working: revoke those separately if the account was misused."""
    _require_admin(actor)
    action = "person.reset_password"
    _not_self(actor, person_id, action, "Change your own password on the Account page.")
    _target(actor, person_id, action)
    password = web.new_temporary_password()
    if not web.set_password_for(person_id, password, must_change=True):
        raise PersonNotFound()
    _audit(actor, action, {"person_id": person_id}, "ok")
    return {"id": str(person_id), "temporary_password": password}


def unlock(actor: Identity, person_id: UUID) -> dict[str, Any]:
    _require_admin(actor)
    _target(actor, person_id, "person.unlock")
    changed = people_repo.unlock(person_id)
    _audit(actor, "person.unlock", {"person_id": person_id}, "ok" if changed else "not_locked")
    return {"id": str(person_id), "unlocked": changed}


def set_disabled(actor: Identity, person_id: UUID, disabled: bool) -> dict[str, Any]:
    _require_admin(actor)
    action = "person.disable" if disabled else "person.enable"
    _not_self(actor, person_id, action, "You can't turn off your own account.")
    _target(actor, person_id, action)
    changed = people_repo.set_disabled(person_id, disabled)
    _audit(actor, action, {"person_id": person_id}, "ok" if changed else "unchanged")
    return {"id": str(person_id), "disabled": disabled}

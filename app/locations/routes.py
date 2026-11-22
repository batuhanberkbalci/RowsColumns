"""FR-04: an Organization Admin creates, edits and deletes locations."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from psycopg2 import errors as pg_errors

from ..auth_utils import role_required
from ..db import get_db
from . import queries as q
from .validation import (
    DAY_NAMES,
    blank_form_state,
    state_from_db,
    state_from_request,
    summarize_hours,
    validate_state,
)

bp = Blueprint("locations", __name__, url_prefix="/locations")

admin_only = role_required("org_admin")

DUPLICATE_NAME = "A location with this name already exists in your organization."


def _org_id():
    # Always taken from the logged-in account, never from the request (NFR-07).
    return current_user.organization_id


def _render_form(mode, state, errors, managers, location_id=None, stale_manager=None):
    return render_template(
        "locations/form.html",
        mode=mode,
        state=state,
        errors=errors,
        managers=managers,
        day_names=DAY_NAMES,
        location_id=location_id,
        stale_manager=stale_manager,
    )


@bp.get("/")
@admin_only
def index():
    with get_db().cursor() as cur:
        locations = q.list_locations(cur, _org_id())
        hours = q.list_hours_for_org(cur, _org_id())

    hours_by_location = {}
    for h in hours:
        hours_by_location.setdefault(h["location_id"], []).append(h)
    for loc in locations:
        loc["hours_summary"] = summarize_hours(hours_by_location.get(loc["location_id"], []))

    return render_template("locations/list.html", locations=locations)


@bp.route("/new", methods=["GET", "POST"])
@admin_only
def create():
    db = get_db()
    with db.cursor() as cur:
        managers = q.list_lab_managers(cur, _org_id())

    if request.method == "GET":
        return _render_form("create", blank_form_state(), {}, managers)

    state = state_from_request(request.form)
    data, errors = validate_state(state, {m["user_id"] for m in managers})
    if not errors:
        try:
            with db.cursor() as cur:
                new_id = q.insert_location(cur, _org_id(), data)
                q.replace_hours(cur, new_id, data["hours"])
            db.commit()
        except pg_errors.UniqueViolation:
            db.rollback()
            errors["name"] = DUPLICATE_NAME
        else:
            flash(f'Location "{data["name"]}" was created.', "success")
            return redirect(url_for("locations.index"))

    return _render_form("create", state, errors, managers), 400


@bp.route("/<int:location_id>/edit", methods=["GET", "POST"])
@admin_only
def edit(location_id):
    db = get_db()
    with db.cursor() as cur:
        location = q.get_location(cur, _org_id(), location_id)
        if location is None:
            abort(404)  # also what an admin of another organization gets
        managers = q.list_lab_managers(cur, _org_id())
        hours_rows = q.get_hours(cur, location_id)

    valid_ids = {m["user_id"] for m in managers}

    if request.method == "GET":
        state = state_from_db(location, hours_rows)
        stale_manager = None
        if location["lab_manager_id"] is not None and location["lab_manager_id"] not in valid_ids:
            # The assigned person is no longer an active, approved Lab Manager.
            stale_manager = location["lab_manager_name"]
            state["lab_manager_id"] = ""
        return _render_form("edit", state, {}, managers, location_id, stale_manager)

    state = state_from_request(request.form)
    data, errors = validate_state(state, valid_ids)
    if not errors:
        try:
            with db.cursor() as cur:
                updated = q.update_location(cur, _org_id(), location_id, data)
                if updated:
                    q.replace_hours(cur, location_id, data["hours"])
            if not updated:
                db.rollback()
                abort(404)
            db.commit()
        except pg_errors.UniqueViolation:
            db.rollback()
            errors["name"] = DUPLICATE_NAME
        else:
            flash(f'Location "{data["name"]}" was updated.', "success")
            return redirect(url_for("locations.index"))

    return _render_form("edit", state, errors, managers, location_id), 400


@bp.post("/<int:location_id>/delete")
@admin_only
def delete(location_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            deleted = q.delete_location(cur, _org_id(), location_id)
        db.commit()
    except pg_errors.ForeignKeyViolation:
        db.rollback()
        flash(
            "This location still has equipment assigned to it, so it can't be deleted. "
            "Move or retire its equipment first.",
            "danger",
        )
        return redirect(url_for("locations.index"))

    if deleted is None:
        abort(404)
    flash(f'Location "{deleted["name"]}" was deleted.', "success")
    return redirect(url_for("locations.index"))

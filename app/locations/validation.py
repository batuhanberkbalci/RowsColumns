"""Form state, validation and display helpers for locations.

The "state" dict holds plain strings exactly as the form shows them, so the
same structure is used to pre-fill the form, to re-show it after an error,
and as input to validate_state().
"""
from datetime import datetime

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LOCATION_TYPES = ("lab", "studio")
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "18:00"


# ---------- form state -------------------------------------------------------

def blank_form_state():
    return {
        "name": "",
        "location_type": "lab",
        "address": "",
        "description": "",
        "lab_manager_id": "",
        "hours": [
            {"weekday": d, "closed": d >= 5, "opens": DEFAULT_OPEN, "closes": DEFAULT_CLOSE}
            for d in range(7)
        ],
    }


def state_from_request(form):
    hours = []
    for d in range(7):
        closed = form.get(f"closed_{d}") == "on"
        opens = form.get(f"opens_{d}", "").strip()
        closes = form.get(f"closes_{d}", "").strip()
        if closed:  # time inputs are disabled by the page when closed
            opens = opens or DEFAULT_OPEN
            closes = closes or DEFAULT_CLOSE
        hours.append({"weekday": d, "closed": closed, "opens": opens, "closes": closes})
    return {
        "name": form.get("name", "").strip(),
        "location_type": form.get("location_type", "").strip(),
        "address": form.get("address", "").strip(),
        "description": form.get("description", "").strip(),
        "lab_manager_id": form.get("lab_manager_id", "").strip(),
        "hours": hours,
    }


def state_from_db(location, hours_rows):
    by_day = {h["weekday"]: h for h in hours_rows}
    hours = []
    for d in range(7):
        h = by_day.get(d)
        if h is None or h["is_closed"]:
            hours.append({"weekday": d, "closed": True, "opens": DEFAULT_OPEN, "closes": DEFAULT_CLOSE})
        else:
            hours.append(
                {
                    "weekday": d,
                    "closed": False,
                    "opens": h["opens_at"].strftime("%H:%M"),
                    "closes": h["closes_at"].strftime("%H:%M"),
                }
            )
    return {
        "name": location["name"],
        "location_type": location["location_type"],
        "address": location["address"],
        "description": location["description"] or "",
        "lab_manager_id": str(location["lab_manager_id"]) if location["lab_manager_id"] else "",
        "hours": hours,
    }


# ---------- validation -------------------------------------------------------

def _parse_time(value):
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def validate_state(state, valid_manager_ids):
    """Returns (data, errors). `data` is ready for the SQL layer; `errors`
    maps a field name (or 'hours_<weekday>') to a message."""
    errors = {}

    name = state["name"]
    if not 2 <= len(name) <= 100:
        errors["name"] = "Name must be between 2 and 100 characters."

    if state["location_type"] not in LOCATION_TYPES:
        errors["location_type"] = "Choose either Lab or Studio."

    address = state["address"]
    if not 5 <= len(address) <= 255:
        errors["address"] = "Address must be between 5 and 255 characters."

    description = state["description"]
    if len(description) > 1000:
        errors["description"] = "Description can be at most 1000 characters."

    manager_id = None
    raw_manager = state["lab_manager_id"]
    if raw_manager:
        try:
            manager_id = int(raw_manager)
        except ValueError:
            manager_id = None
            errors["lab_manager_id"] = "Choose a Lab Manager from the list."
        else:
            # Also guarantees the manager belongs to the admin's own organization.
            if manager_id not in valid_manager_ids:
                manager_id = None
                errors["lab_manager_id"] = (
                    "That person is not an approved, active Lab Manager in your organization."
                )

    hours = []
    for h in state["hours"]:
        d = h["weekday"]
        if h["closed"]:
            hours.append({"weekday": d, "is_closed": True, "opens_at": None, "closes_at": None})
            continue
        opens, closes = _parse_time(h["opens"]), _parse_time(h["closes"])
        if opens is None or closes is None:
            errors[f"hours_{d}"] = "Enter both an opening and a closing time, or mark the day closed."
        elif opens >= closes:
            errors[f"hours_{d}"] = "Closing time must be later than opening time."
        else:
            hours.append({"weekday": d, "is_closed": False, "opens_at": opens, "closes_at": closes})

    data = {
        "name": name,
        "location_type": state["location_type"],
        "address": address,
        "description": description or None,
        "lab_manager_id": manager_id,
        "hours": hours,
    }
    return data, errors


# ---------- display ----------------------------------------------------------

def summarize_hours(rows):
    """Collapse 7 daily rows into groups like [('Mon–Fri', '09:00–18:00'), ('Sun', 'Closed')]."""
    by_day = {r["weekday"]: r for r in rows}
    labels = []
    for d in range(7):
        r = by_day.get(d)
        if r is None or r["is_closed"]:
            labels.append("Closed")
        else:
            labels.append(f"{r['opens_at']:%H:%M}–{r['closes_at']:%H:%M}")

    groups, start = [], 0
    for d in range(1, 8):
        if d == 7 or labels[d] != labels[start]:
            groups.append((start, d - 1, labels[start]))
            start = d

    summary = []
    for first, last, label in groups:
        days = DAY_SHORT[first] if first == last else f"{DAY_SHORT[first]}–{DAY_SHORT[last]}"
        summary.append((days, label))
    return summary

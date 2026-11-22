"""Create the schema and load demo data.

    python seed.py --reset

--reset DROPS the whole `public` schema first, so only point DATABASE_URL at a
database you are happy to wipe.
"""
import pathlib
import sys
from datetime import time

import psycopg2
from werkzeug.security import generate_password_hash

from config import Config

DB_DIR = pathlib.Path(__file__).parent / "db"
DEMO_PASSWORD = "Passw0rd!"

# (organization, email, full name, role, membership status)
USERS = [
    ("ITU Maker Space", "admin@itu.test", "Ayşe Admin", "org_admin", "approved"),
    ("ITU Maker Space", "manager1@itu.test", "Deniz Kaya", "lab_manager", "approved"),
    ("ITU Maker Space", "manager2@itu.test", "Elif Demir", "lab_manager", "approved"),
    ("ITU Maker Space", "pending.manager@itu.test", "Pınar Pending", "lab_manager", "pending"),
    ("ITU Maker Space", "member@itu.test", "Mert Member", "member", "approved"),
    ("Bosphorus Film Studio", "admin@studio.test", "Selin Admin", "org_admin", "approved"),
    ("Bosphorus Film Studio", "manager@studio.test", "Can Yılmaz", "lab_manager", "approved"),
]

WEEKDAY_HOURS = (time(9, 0), time(18, 0))
SATURDAY_HOURS = (time(10, 0), time(14, 0))


def _hours(saturday=SATURDAY_HOURS):
    """Mon-Fri 09:00-18:00, Saturday as given (None = closed), Sunday closed."""
    rows = []
    for d in range(7):
        if d < 5:
            rows.append((d, False, *WEEKDAY_HOURS))
        elif d == 5 and saturday:
            rows.append((d, False, *saturday))
        else:
            rows.append((d, True, None, None))
    return rows


def reset_and_seed(database_url, reset=True):
    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            if reset:
                cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            for sql_file in sorted(DB_DIR.glob("*.sql")):
                cur.execute(sql_file.read_text(encoding="utf-8"))

            password_hash = generate_password_hash(DEMO_PASSWORD)

            org_ids = {}
            for name in dict.fromkeys(u[0] for u in USERS):
                cur.execute(
                    "INSERT INTO organization (name) VALUES (%s) RETURNING organization_id", (name,)
                )
                org_ids[name] = cur.fetchone()[0]

            user_ids = {}
            for org, email, full_name, role, status in USERS:
                cur.execute(
                    """
                    INSERT INTO app_user
                        (organization_id, email, full_name, password_hash, role, membership_status)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id
                    """,
                    (org_ids[org], email, full_name, password_hash, role, status),
                )
                user_ids[email] = cur.fetchone()[0]

            locations = [
                ("ITU Maker Space", "Robotics Lab", "lab",
                 "Student Building A, Room 204, Maslak Campus, Istanbul",
                 "Robot arms, microcontrollers and test benches.", "manager1@itu.test", _hours()),
                ("ITU Maker Space", "3D Printing Studio", "studio",
                 "Student Building B, Ground Floor, Maslak Campus, Istanbul",
                 None, "manager2@itu.test", _hours(saturday=None)),
                ("ITU Maker Space", "Electronics Bench Room", "lab",
                 "Student Building A, Room 110, Maslak Campus, Istanbul",
                 None, None, _hours()),
                ("Bosphorus Film Studio", "Main Film Studio", "studio",
                 "Kuruçeşme Caddesi 12, Beşiktaş, Istanbul",
                 "Camera and lighting equipment.", "manager@studio.test", _hours()),
            ]
            for org, name, loc_type, address, description, manager_email, hours in locations:
                manager_id = user_ids[manager_email] if manager_email else None
                cur.execute(
                    """
                    INSERT INTO location
                        (organization_id, name, location_type, address, description, lab_manager_id)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING location_id
                    """,
                    (org_ids[org], name, loc_type, address, description, manager_id),
                )
                location_id = cur.fetchone()[0]
                for weekday, is_closed, opens, closes in hours:
                    cur.execute(
                        """
                        INSERT INTO location_opening_hours
                            (location_id, weekday, is_closed, opens_at, closes_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (location_id, weekday, is_closed, opens, closes),
                    )
    finally:
        conn.close()


if __name__ == "__main__":
    if "--reset" not in sys.argv:
        sys.exit("This wipes the database. Run:  python seed.py --reset")
    reset_and_seed(Config.DATABASE_URL, reset=True)
    print("Database created and seeded.")
    print(f"Demo password for every account: {DEMO_PASSWORD}")
    for _org, email, _name, role, status in USERS:
        print(f"  {email:28} {role:12} {status}")

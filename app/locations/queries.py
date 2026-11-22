"""All raw, parameterized SQL for FR-04 (locations). No ORM.

Every function takes an open cursor. Every query that touches a location is
scoped by organization_id, and that value must always come from the logged-in
user's account, never from a form field or URL (NFR-07).
"""


def list_locations(cur, org_id):
    cur.execute(
        """
        SELECT l.location_id, l.name, l.location_type, l.address, l.description,
               l.lab_manager_id,
               u.full_name AS lab_manager_name,
               u.email     AS lab_manager_email
        FROM location l
        LEFT JOIN app_user u ON u.user_id = l.lab_manager_id
        WHERE l.organization_id = %s
        ORDER BY l.name
        """,
        (org_id,),
    )
    return cur.fetchall()


def get_location(cur, org_id, location_id):
    cur.execute(
        """
        SELECT l.location_id, l.name, l.location_type, l.address, l.description,
               l.lab_manager_id,
               u.full_name AS lab_manager_name
        FROM location l
        LEFT JOIN app_user u ON u.user_id = l.lab_manager_id
        WHERE l.location_id = %s AND l.organization_id = %s
        """,
        (location_id, org_id),
    )
    return cur.fetchone()


def list_hours_for_org(cur, org_id):
    cur.execute(
        """
        SELECT h.location_id, h.weekday, h.is_closed, h.opens_at, h.closes_at
        FROM location_opening_hours h
        JOIN location l ON l.location_id = h.location_id
        WHERE l.organization_id = %s
        ORDER BY h.location_id, h.weekday
        """,
        (org_id,),
    )
    return cur.fetchall()


def get_hours(cur, location_id):
    # Only call after get_location() confirmed the location belongs to the org.
    cur.execute(
        """
        SELECT weekday, is_closed, opens_at, closes_at
        FROM location_opening_hours
        WHERE location_id = %s
        ORDER BY weekday
        """,
        (location_id,),
    )
    return cur.fetchall()


def list_lab_managers(cur, org_id):
    """Users who may be assigned: approved, active Lab Managers of this org."""
    cur.execute(
        """
        SELECT user_id, full_name, email
        FROM app_user
        WHERE organization_id = %s
          AND role = 'lab_manager'
          AND membership_status = 'approved'
          AND is_active
        ORDER BY full_name
        """,
        (org_id,),
    )
    return cur.fetchall()


def insert_location(cur, org_id, data):
    cur.execute(
        """
        INSERT INTO location
            (organization_id, name, location_type, address, description, lab_manager_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING location_id
        """,
        (
            org_id,
            data["name"],
            data["location_type"],
            data["address"],
            data["description"],
            data["lab_manager_id"],
        ),
    )
    return cur.fetchone()["location_id"]


def update_location(cur, org_id, location_id, data):
    """Returns the row if updated, None if no such location in this org."""
    cur.execute(
        """
        UPDATE location
        SET name = %s, location_type = %s, address = %s, description = %s,
            lab_manager_id = %s, updated_at = NOW()
        WHERE location_id = %s AND organization_id = %s
        RETURNING location_id
        """,
        (
            data["name"],
            data["location_type"],
            data["address"],
            data["description"],
            data["lab_manager_id"],
            location_id,
            org_id,
        ),
    )
    return cur.fetchone()


def replace_hours(cur, location_id, hours):
    """Replace all 7 opening-hours rows. Run in the same transaction as the
    insert/update of the location so a failure leaves nothing half-saved."""
    cur.execute(
        "DELETE FROM location_opening_hours WHERE location_id = %s", (location_id,)
    )
    for h in hours:
        cur.execute(
            """
            INSERT INTO location_opening_hours
                (location_id, weekday, is_closed, opens_at, closes_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (location_id, h["weekday"], h["is_closed"], h["opens_at"], h["closes_at"]),
        )


def delete_location(cur, org_id, location_id):
    """Returns {'name': ...} if deleted, None if no such location in this org.
    Raises psycopg2.errors.ForeignKeyViolation if equipment still uses it."""
    cur.execute(
        """
        DELETE FROM location
        WHERE location_id = %s AND organization_id = %s
        RETURNING name
        """,
        (location_id, org_id),
    )
    return cur.fetchone()

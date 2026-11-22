-- ============================================================
-- FR-04: Locations (labs / studios) with address, opening hours
-- and an assigned Lab Manager.
-- PostgreSQL 16
-- ============================================================

CREATE TABLE location (
    location_id      SERIAL PRIMARY KEY,
    organization_id  INTEGER NOT NULL
                     REFERENCES organization(organization_id) ON DELETE CASCADE,
    name             VARCHAR(100) NOT NULL,
    location_type    VARCHAR(10) NOT NULL DEFAULT 'lab'
                     CHECK (location_type IN ('lab', 'studio')),
    address          VARCHAR(255) NOT NULL,
    description      TEXT,
    -- Optional: a location can exist before a Lab Manager is assigned.
    -- If the manager's account is deleted the location stays, unassigned.
    lab_manager_id   INTEGER
                     REFERENCES app_user(user_id) ON DELETE SET NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),

    -- A name is unique inside one organization only.
    CONSTRAINT uq_location_org_name UNIQUE (organization_id, name),
    -- Lets other tables reference (location_id, organization_id) so a row
    -- can never point at a location of another organization (NFR-07).
    CONSTRAINT uq_location_id_org UNIQUE (location_id, organization_id)
);

CREATE INDEX idx_location_org     ON location (organization_id);
CREATE INDEX idx_location_manager ON location (lab_manager_id);

-- One row per weekday (0 = Monday ... 6 = Sunday).
-- Either the day is closed (no times) or it has opens_at < closes_at.
CREATE TABLE location_opening_hours (
    location_id  INTEGER  NOT NULL
                 REFERENCES location(location_id) ON DELETE CASCADE,
    weekday      SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    is_closed    BOOLEAN  NOT NULL DEFAULT FALSE,
    opens_at     TIME,
    closes_at    TIME,

    PRIMARY KEY (location_id, weekday),
    CONSTRAINT chk_opening_hours CHECK (
        (is_closed AND opens_at IS NULL AND closes_at IS NULL)
        OR
        (NOT is_closed AND opens_at IS NOT NULL AND closes_at IS NOT NULL
                       AND opens_at < closes_at)
    )
);

-- ------------------------------------------------------------
-- NOTE FOR EQUIPMENT (Abdullah, FR-07):
--   equipment.location_id must reference location(location_id) with
--   ON DELETE RESTRICT (the default NO ACTION also works). Do NOT use
--   CASCADE: deleting a location must never erase equipment or its
--   reservation history. The delete route turns the resulting foreign-key
--   error into a friendly message.
-- ------------------------------------------------------------

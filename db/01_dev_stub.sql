-- ============================================================
-- DEV STAND-INS for tables owned by teammates.
-- Replace this file with the real tables from the team repo
-- (organization + users from Batuhan). FR-04 only needs these columns:
--   organization(organization_id, name)
--   app_user(user_id, organization_id, email, full_name, password_hash,
--            role, membership_status, is_active)
--   role              in ('org_admin', 'lab_manager', 'member')
--   membership_status in ('pending', 'approved', 'rejected')
-- ============================================================

CREATE TABLE organization (
    organization_id SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE app_user (
    user_id           SERIAL PRIMARY KEY,
    organization_id   INTEGER NOT NULL
                      REFERENCES organization(organization_id) ON DELETE CASCADE,
    email             VARCHAR(255) NOT NULL UNIQUE,
    full_name         VARCHAR(150) NOT NULL,
    password_hash     TEXT NOT NULL,
    role              VARCHAR(20) NOT NULL
                      CHECK (role IN ('org_admin', 'lab_manager', 'member')),
    membership_status VARCHAR(20) NOT NULL DEFAULT 'pending'
                      CHECK (membership_status IN ('pending', 'approved', 'rejected')),
    is_active         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_app_user_org_role ON app_user (organization_id, role);

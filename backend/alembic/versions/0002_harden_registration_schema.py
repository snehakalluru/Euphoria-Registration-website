"""Harden registration schema for Supabase PostgreSQL."""
from alembic import op

revision = "0002_harden_registration_schema"
down_revision = "0001_initial_euphoria_schema"
branch_labels = None
depends_on = None


def _add_constraint_if_missing(table: str, name: str, definition: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{name}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table}
                ADD CONSTRAINT {name}
                {definition};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE team_members
        ADD COLUMN IF NOT EXISTS id_proof_path text
        """
    )
    op.execute(
        """
        ALTER TABLE team_members
        ADD COLUMN IF NOT EXISTS id_proof_filename varchar(200)
        """
    )
    op.execute(
        """
        ALTER TABLE team_members
        ADD COLUMN IF NOT EXISTS id_proof_content_type varchar(80)
        """
    )
    _add_constraint_if_missing(
        "teams",
        "uq_teams_id_hackathon_id",
        "UNIQUE (id, hackathon_id)",
    )
    _add_constraint_if_missing(
        "teams",
        "uq_teams_registration_id",
        "UNIQUE (registration_id)",
    )
    _add_constraint_if_missing(
        "teams",
        "uq_teams_hackathon_team_name",
        "UNIQUE (hackathon_id, team_name_normalized)",
    )
    _add_constraint_if_missing(
        "teams",
        "ck_teams_member_count",
        "CHECK (member_count BETWEEN 4 AND 5)",
    )
    _add_constraint_if_missing(
        "teams",
        "ck_teams_confirmation_accepted",
        "CHECK (confirmation_accepted IS TRUE)",
    )
    _add_constraint_if_missing(
        "teams",
        "ck_teams_college_rules",
        "CHECK ((college_type = 'external' AND NULLIF(TRIM(college_name), '') IS NOT NULL) OR college_type = 'internal')",
    )
    _add_constraint_if_missing(
        "team_members",
        "uq_team_members_team_member_number",
        "UNIQUE (team_id, member_number)",
    )
    _add_constraint_if_missing(
        "team_members",
        "uq_team_members_hackathon_euphoria",
        "UNIQUE (hackathon_id, euphoria_id_normalized)",
    )
    _add_constraint_if_missing(
        "team_members",
        "uq_team_members_hackathon_email",
        "UNIQUE (hackathon_id, email_normalized)",
    )
    _add_constraint_if_missing(
        "team_members",
        "uq_team_members_hackathon_phone",
        "UNIQUE (hackathon_id, phone_normalized)",
    )
    _add_constraint_if_missing(
        "team_members",
        "uq_team_members_hackathon_registration",
        "UNIQUE (hackathon_id, registration_number_normalized)",
    )
    _add_constraint_if_missing(
        "team_members",
        "ck_team_members_member_number",
        "CHECK (member_number BETWEEN 1 AND 5)",
    )
    _add_constraint_if_missing(
        "team_members",
        "ck_team_members_lead_position",
        "CHECK ((member_number = 1 AND is_team_lead IS TRUE) OR (member_number > 1 AND is_team_lead IS FALSE))",
    )
    _add_constraint_if_missing(
        "team_members",
        "ck_team_members_accommodation_rules",
        """CHECK (
                    (accommodation_type IS NULL AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL)
                    OR (accommodation_type = 'day_scholar' AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL)
                    OR (
                        accommodation_type = 'hosteller'
                        AND NULLIF(TRIM(hostel_name), '') IS NOT NULL
                        AND NULLIF(TRIM(room_number), '') IS NOT NULL
                        AND NULLIF(TRIM(warden_name), '') IS NOT NULL
                        AND NULLIF(TRIM(warden_phone), '') IS NOT NULL
                    )
                )""",
    )
    for table, column in (
        ("teams", "submitted_at"),
        ("teams", "college_type"),
        ("teams", "member_count"),
        ("team_members", "name"),
        ("team_members", "email_normalized"),
        ("team_members", "phone_normalized"),
        ("team_members", "euphoria_id_normalized"),
        ("team_members", "registration_number_normalized"),
    ):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_{column} ON {table} ({column})")


def downgrade() -> None:
    raise RuntimeError("Downgrade is intentionally disabled because it would remove production constraints/columns.")

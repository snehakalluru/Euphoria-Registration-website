"""Create the initial Euphoria registration schema."""
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0001_initial_euphoria_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = None if context.is_offline_mode() else inspect(op.get_bind())
    enums = [
        postgresql.ENUM("internal", "external", name="college_type"),
        postgresql.ENUM("submitted", name="registration_status"),
        postgresql.ENUM("day_scholar", "hosteller", name="accommodation_type"),
        postgresql.ENUM("admin", name="admin_role"),
    ]
    for enum in enums:
        enum.create(op.get_bind(), checkfirst=True)

    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()
    if inspector is None or not inspector.has_table("hackathons"):
        op.create_table("hackathons",
        sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("tagline", sa.Text()), sa.Column("description", sa.Text()), sa.Column("logo_url", sa.Text()), sa.Column("rules", jsonb), sa.Column("eligibility", jsonb), sa.Column("instructions", jsonb), sa.Column("sdg_goals", jsonb), sa.Column("whatsapp_url", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("slug", name="uq_hackathons_slug"))
    if inspector is None or not inspector.has_table("clubs"):
        op.create_table("clubs",
        sa.Column("id", uuid, primary_key=True), sa.Column("hackathon_id", uuid, nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(120), nullable=False), sa.Column("logo_url", sa.Text()), sa.Column("description", sa.Text()), sa.Column("faculty_in_charge", sa.String(160)), sa.Column("student_in_charge", sa.String(160)), sa.Column("contact_details", jsonb), sa.Column("display_order", sa.Integer(), nullable=False), sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["hackathon_id"], ["hackathons.id"], ondelete="CASCADE"), sa.UniqueConstraint("hackathon_id", "slug", name="uq_clubs_hackathon_slug"), sa.UniqueConstraint("hackathon_id", "display_order", name="uq_clubs_hackathon_display_order"))
    if inspector is None or not inspector.has_table("teams"):
        op.create_table("teams",
        sa.Column("id", uuid, primary_key=True), sa.Column("hackathon_id", uuid, nullable=False), sa.Column("registration_id", sa.String(32), nullable=False), sa.Column("team_name", sa.String(160), nullable=False), sa.Column("team_name_normalized", sa.String(160), nullable=False), sa.Column("college_type", postgresql.ENUM(name="college_type", create_type=False), nullable=False), sa.Column("college_name", sa.String(200)), sa.Column("member_count", sa.Integer(), nullable=False), sa.Column("status", postgresql.ENUM(name="registration_status", create_type=False), nullable=False, server_default="submitted"), sa.Column("confirmation_accepted", sa.Boolean(), nullable=False), sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["hackathon_id"], ["hackathons.id"], ondelete="RESTRICT"), sa.UniqueConstraint("id", "hackathon_id", name="uq_teams_id_hackathon_id"), sa.UniqueConstraint("registration_id", name="uq_teams_registration_id"), sa.UniqueConstraint("hackathon_id", "team_name_normalized", name="uq_teams_hackathon_team_name"), sa.CheckConstraint("member_count BETWEEN 4 AND 5", name="ck_teams_member_count"), sa.CheckConstraint("confirmation_accepted IS TRUE", name="ck_teams_confirmation_accepted"), sa.CheckConstraint("(college_type = 'external' AND NULLIF(TRIM(college_name), '') IS NOT NULL) OR college_type = 'internal'", name="ck_teams_college_rules"))
    if inspector is None or not inspector.has_table("team_members"):
        op.create_table("team_members",
        sa.Column("id", uuid, primary_key=True), sa.Column("team_id", uuid, nullable=False), sa.Column("hackathon_id", uuid, nullable=False), sa.Column("member_number", sa.Integer(), nullable=False), sa.Column("is_team_lead", sa.Boolean(), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("registration_number", sa.String(80), nullable=False), sa.Column("registration_number_normalized", sa.String(80), nullable=False), sa.Column("email", sa.String(255), nullable=False), sa.Column("email_normalized", sa.String(255), nullable=False), sa.Column("phone", sa.String(20), nullable=False), sa.Column("phone_normalized", sa.String(20), nullable=False), sa.Column("gender", sa.String(40), nullable=False), sa.Column("year", sa.String(40), nullable=False), sa.Column("branch", sa.String(80), nullable=False), sa.Column("section", sa.String(40), nullable=False), sa.Column("euphoria_id", sa.String(80), nullable=False), sa.Column("euphoria_id_normalized", sa.String(80), nullable=False), sa.Column("accommodation_type", postgresql.ENUM(name="accommodation_type", create_type=False)), sa.Column("hostel_name", sa.String(160)), sa.Column("room_number", sa.String(60)), sa.Column("warden_name", sa.String(160)), sa.Column("warden_phone", sa.String(20)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["team_id", "hackathon_id"], ["teams.id", "teams.hackathon_id"], ondelete="CASCADE", name="fk_team_members_team_hackathon"), sa.UniqueConstraint("team_id", "member_number", name="uq_team_members_team_member_number"), sa.UniqueConstraint("hackathon_id", "euphoria_id_normalized", name="uq_team_members_hackathon_euphoria"), sa.UniqueConstraint("hackathon_id", "email_normalized", name="uq_team_members_hackathon_email"), sa.UniqueConstraint("hackathon_id", "phone_normalized", name="uq_team_members_hackathon_phone"), sa.UniqueConstraint("hackathon_id", "registration_number_normalized", name="uq_team_members_hackathon_registration"), sa.CheckConstraint("member_number BETWEEN 1 AND 5", name="ck_team_members_member_number"), sa.CheckConstraint("(member_number = 1 AND is_team_lead IS TRUE) OR (member_number > 1 AND is_team_lead IS FALSE)", name="ck_team_members_lead_position"), sa.CheckConstraint("(accommodation_type IS NULL AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL) OR (accommodation_type = 'day_scholar' AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL) OR (accommodation_type = 'hosteller' AND NULLIF(TRIM(hostel_name), '') IS NOT NULL AND NULLIF(TRIM(room_number), '') IS NOT NULL AND NULLIF(TRIM(warden_name), '') IS NOT NULL AND NULLIF(TRIM(warden_phone), '') IS NOT NULL)", name="ck_team_members_accommodation_rules"))
    if inspector is None or not inspector.has_table("admins"):
        op.create_table("admins",
        sa.Column("id", uuid, primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("name", sa.String(120)), sa.Column("role", postgresql.ENUM(name="admin_role", create_type=False), nullable=False, server_default="admin"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_login_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("email", name="uq_admins_email"))
    indexes = [("teams", "submitted_at"), ("teams", "college_type"), ("teams", "member_count"), ("team_members", "name"), ("team_members", "email_normalized"), ("team_members", "phone_normalized"), ("team_members", "euphoria_id_normalized"), ("team_members", "registration_number_normalized")]
    for table, column in indexes:
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_{column} ON {table} ({column})")


def downgrade() -> None:
    raise RuntimeError("Downgrade is intentionally disabled because it would drop production tables.")

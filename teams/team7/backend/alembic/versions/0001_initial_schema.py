"""initial team-7 schema: 7 application tables for Chat with Coach + Reserve Coach

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-22 00:00:00.000000

This migration is hand-written to mirror the DBML in
``teams/team7/.agents/03_database_design.md`` §3 exactly. It is
PostgreSQL-16-correct, self-contained, and creates all seven application
tables with their constraints and indexes in dependency order.

Dependency order (upgrade):
    coach_profile -> coach_availability, chat_thread, coach_rating
    chat_thread   -> chat_message
    coach_availability -> appointment
    chat_message  -> message_attachment

Downgrade runs in the reverse order.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. coach_profile -- no FKs to other team-7 tables.
    op.create_table(
        "coach_profile",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("specialties", postgresql.JSONB(), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("years_experience", sa.SmallInteger(), nullable=True),
        sa.Column(
            "is_online",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint("user_id", name="uq_coach_profile_user_id"),
    )
    op.create_index(
        "ix_coach_profile_is_online", "coach_profile", ["is_online"]
    )

    # 2. coach_availability -- FK to coach_profile.user_id.
    op.create_table(
        "coach_availability",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "coach_user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "coach_profile.user_id", name="fk_coach_availability_coach_user_id"
            ),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.CheckConstraint(
            "end_at > start_at", name="ck_coach_availability_end_after_start"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'booked', 'blocked')",
            name="ck_coach_availability_status",
        ),
    )
    op.create_index(
        "ix_coach_availability_coach_start",
        "coach_availability",
        ["coach_user_id", "start_at"],
    )
    op.create_index(
        "ix_coach_availability_status", "coach_availability", ["status"]
    )

    # 3. chat_thread -- FK to coach_profile.user_id; unique(user_id, coach_user_id).
    op.create_table(
        "chat_thread",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "coach_user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "coach_profile.user_id", name="fk_chat_thread_coach_user_id"
            ),
            nullable=False,
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint("user_id", "coach_user_id", name="uq_chat_thread_user_coach"),
    )
    op.create_index(
        "ix_chat_thread_coach_user_id", "chat_thread", ["coach_user_id"]
    )
    op.create_index(
        "ix_chat_thread_last_message_at", "chat_thread", ["last_message_at"]
    )

    # 4. appointment -- FK to coach_profile.user_id; FK + unique on availability_id.
    op.create_table(
        "appointment",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "coach_user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "coach_profile.user_id", name="fk_appointment_coach_user_id"
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "availability_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "coach_availability.id", name="fk_appointment_availability_id"
            ),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'confirmed'"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')",
            name="ck_appointment_status",
        ),
    )
    op.create_index("ix_appointment_user_id", "appointment", ["user_id"])
    op.create_index("ix_appointment_coach_user_id", "appointment", ["coach_user_id"])
    op.create_index("ix_appointment_status", "appointment", ["status"])

    # 5. chat_message -- FK to chat_thread.id.
    op.create_table(
        "chat_message",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "thread_id",
            sa.BigInteger(),
            sa.ForeignKey("chat_thread.id", name="fk_chat_message_thread_id"),
            nullable=False,
        ),
        sa.Column("sender_user_id", sa.BigInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_chat_message_thread_id", "chat_message", ["thread_id"])
    op.create_index(
        "ix_chat_message_thread_sent", "chat_message", ["thread_id", "sent_at"]
    )
    op.create_index(
        "ix_chat_message_sender_user_id", "chat_message", ["sender_user_id"]
    )

    # 6. message_attachment -- FK to chat_message.id.
    op.create_table(
        "message_attachment",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "message_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "chat_message.id", name="fk_message_attachment_message_id"
            ),
            nullable=False,
        ),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_message_attachment_message_id", "message_attachment", ["message_id"]
    )

    # 7. coach_rating -- FK to coach_profile.user_id; unique(coach_user_id, user_id).
    op.create_table(
        "coach_rating",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "coach_user_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "coach_profile.user_id", name="fk_coach_rating_coach_user_id"
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_coach_rating_range"),
        sa.UniqueConstraint(
            "coach_user_id", "user_id", name="uq_coach_rating_coach_user"
        ),
    )
    op.create_index(
        "ix_coach_rating_coach_user_id", "coach_rating", ["coach_user_id"]
    )


def downgrade() -> None:
    # Reverse dependency order.
    op.drop_index("ix_coach_rating_coach_user_id", table_name="coach_rating")
    op.drop_table("coach_rating")

    op.drop_index(
        "ix_message_attachment_message_id", table_name="message_attachment"
    )
    op.drop_table("message_attachment")

    op.drop_index("ix_chat_message_sender_user_id", table_name="chat_message")
    op.drop_index("ix_chat_message_thread_sent", table_name="chat_message")
    op.drop_index("ix_chat_message_thread_id", table_name="chat_message")
    op.drop_table("chat_message")

    op.drop_index("ix_appointment_status", table_name="appointment")
    op.drop_index("ix_appointment_coach_user_id", table_name="appointment")
    op.drop_index("ix_appointment_user_id", table_name="appointment")
    op.drop_table("appointment")

    op.drop_index("ix_chat_thread_last_message_at", table_name="chat_thread")
    op.drop_index("ix_chat_thread_coach_user_id", table_name="chat_thread")
    op.drop_table("chat_thread")

    op.drop_index("ix_coach_availability_status", table_name="coach_availability")
    op.drop_index(
        "ix_coach_availability_coach_start", table_name="coach_availability"
    )
    op.drop_table("coach_availability")

    op.drop_index("ix_coach_profile_is_online", table_name="coach_profile")
    op.drop_table("coach_profile")

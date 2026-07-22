"""Smoke tests for the SCRUM-6 ORM models.

These don't require a live DB connection — they only verify that the
seven application tables register cleanly on ``Base.metadata`` with the
right names and that the ORM-level constraints (CHECK / UNIQUE / FK)
survive a round-trip through SQLAlchemy reflection.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models import Base
from app.models.appointment import Appointment
from app.models.chat_message import ChatMessage
from app.models.chat_thread import ChatThread
from app.models.coach_availability import CoachAvailability
from app.models.coach_profile import CoachProfile
from app.models.coach_rating import CoachRating
from app.models.message_attachment import MessageAttachment

EXPECTED_TABLES = {
    "coach_profile",
    "coach_availability",
    "appointment",
    "chat_thread",
    "chat_message",
    "message_attachment",
    "coach_rating",
}


def test_metadata_registers_all_seven_tables() -> None:
    """All seven application tables from 03_database_design.md are present."""
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_audit_columns_inherited_by_every_table() -> None:
    """``id`` / ``created_at`` / ``updated_at`` / ``is_deleted`` are inherited."""
    required = {"id", "created_at", "updated_at", "is_deleted"}
    for table_name in EXPECTED_TABLES:
        columns = {c.name for c in Base.metadata.tables[table_name].columns}
        missing = required - columns
        assert not missing, f"table {table_name} is missing audit columns: {missing}"


def test_unique_constraints_present() -> None:
    """Unique constraints from the DBML spec exist on the ORM models."""
    tables = Base.metadata.tables

    def unique_column_sets(table_name: str) -> list[set[str]]:
        return [
            {col.name for col in c.columns}
            for c in tables[table_name].constraints
            if isinstance(c, UniqueConstraint)
        ]

    # coach_profile.user_id (single-column unique)
    assert {"user_id"} in unique_column_sets("coach_profile")
    # appointment.availability_id
    assert {"availability_id"} in unique_column_sets("appointment")
    # chat_thread(user_id, coach_user_id)
    assert {"user_id", "coach_user_id"} in unique_column_sets("chat_thread")
    # coach_rating(coach_user_id, user_id)
    assert {"coach_user_id", "user_id"} in unique_column_sets("coach_rating")


def test_check_constraints_present() -> None:
    """CHECK constraints from the DBML spec exist on the ORM models."""
    cases: dict[str, list[str]] = {
        "coach_availability": [
            "end_at > start_at",
            "status IN ('open', 'booked', 'blocked')",
        ],
        "appointment": [
            "status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')",
        ],
        "coach_rating": ["rating BETWEEN 1 AND 5"],
    }
    for table_name, expected_snippets in cases.items():
        check_sqls = [
            str(c.sqltext)
            for c in Base.metadata.tables[table_name].constraints
            if isinstance(c, CheckConstraint)
        ]
        for snippet in expected_snippets:
            assert any(snippet in sql for sql in check_sqls), (
                f"table {table_name} missing CHECK matching {snippet!r}; got {check_sqls}"
            )


def test_foreign_keys_target_coach_profile_user_id() -> None:
    """Every coach-side FK points at ``coach_profile.user_id``, not ``.id``.

    Several tables (e.g. ``appointment``) have *multiple* FKs; the one
    naming the coach must specifically target ``coach_profile.user_id``.
    """
    coach_fk_columns = {
        "coach_availability": "coach_user_id",
        "appointment": "coach_user_id",
        "chat_thread": "coach_user_id",
        "coach_rating": "coach_user_id",
    }
    for table_name, column_name in coach_fk_columns.items():
        fk = next(
            (
                fk
                for fk in Base.metadata.tables[table_name].foreign_keys
                if fk.parent.name == column_name
            ),
            None,
        )
        assert fk is not None, (
            f"{table_name}.{column_name} has no FK declared on the ORM"
        )
        assert fk.column.table.name == "coach_profile", (
            f"{table_name}.{column_name} -> {fk.column.table.name}.{fk.column.name}"
        )
        assert fk.column.name == "user_id", (
            f"{table_name}.{column_name} -> coach_profile.{fk.column.name}; "
            "spec says user_id"
        )


def test_intra_database_fks_present() -> None:
    """FKs that stay inside the team-7 database (not pointing at coach_profile)."""
    # chat_message.thread_id -> chat_thread.id
    msg_fks = {
        (fk.column.table.name, fk.column.name)
        for fk in Base.metadata.tables["chat_message"].foreign_keys
    }
    assert ("chat_thread", "id") in msg_fks

    # message_attachment.message_id -> chat_message.id
    att_fks = {
        (fk.column.table.name, fk.column.name)
        for fk in Base.metadata.tables["message_attachment"].foreign_keys
    }
    assert ("chat_message", "id") in att_fks

    # appointment.availability_id -> coach_availability.id
    apt_fks = {
        (fk.column.table.name, fk.column.name)
        for fk in Base.metadata.tables["appointment"].foreign_keys
    }
    assert ("coach_availability", "id") in apt_fks


def test_models_are_importable_from_package_root() -> None:
    """Every model class is reachable via ``app.models.*``."""
    from app.models import (
        Appointment,
        ChatMessage,
        ChatThread,
        CoachAvailability,
        CoachProfile,
        CoachRating,
        MessageAttachment,
    )

    for cls in (
        Appointment,
        ChatMessage,
        ChatThread,
        CoachAvailability,
        CoachProfile,
        CoachRating,
        MessageAttachment,
    ):
        assert cls.__tablename__ in EXPECTED_TABLES


def test_referenced_classes_are_used() -> None:
    """Smoke import to make sure the module-level imports are intentional."""
    # All seven ORM classes are re-exported at module level.
    cls_set = {Appointment, ChatMessage, ChatThread, CoachAvailability, CoachProfile, CoachRating, MessageAttachment}
    assert len(cls_set) == 7

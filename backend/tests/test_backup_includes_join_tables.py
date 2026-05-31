"""Tests verifying backup_service includes the 7 newer join tables and
remains backward-compatible with old zips that lack them."""

import sys
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.volume import Volume  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.setting_item import SettingItem  # noqa: E402
from app.models.clue import Clue  # noqa: E402
from app.models.outline_item import OutlineItem  # noqa: E402
from app.models.timeline_track import TimelineTrack  # noqa: E402
from app.models.timeline_event import TimelineEvent  # noqa: E402
from app.models.timeline_event_character import TimelineEventCharacter  # noqa: E402
from app.models.timeline_event_setting import TimelineEventSetting  # noqa: E402
from app.models.timeline_event_clue import TimelineEventClue  # noqa: E402
from app.models.outline_item_character import OutlineItemCharacter  # noqa: E402
from app.models.outline_item_setting import OutlineItemSetting  # noqa: E402
from app.models.outline_item_clue import OutlineItemClue  # noqa: E402
from app.models.outline_item_timeline_event import OutlineItemTimelineEvent  # noqa: E402
from app.services.backup_service import (  # noqa: E402
    BackupService,
    ENTITY_MODELS,
    PROJECT_CHILDREN,
    RESTORE_ORDER,
    REFERENCE_FIELDS,
)


NEW_JOIN_TABLES = [
    "timeline_event_characters",
    "timeline_event_settings",
    "timeline_event_clues",
    "outline_item_characters",
    "outline_item_settings",
    "outline_item_clues",
    "outline_item_timeline_events",
]


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_project(db_session):
    """Create a project with one of each entity including the 7 new join tables."""
    pid = str(uuid4())
    project = Project(id=pid, title="测试项目")
    db_session.add(project)
    db_session.flush()

    vid = str(uuid4())
    db_session.add(Volume(id=vid, project_id=pid, title="第一卷", order_index=1))
    db_session.flush()

    cid = str(uuid4())
    db_session.add(Chapter(id=cid, project_id=pid, volume_id=vid, title="第一章", order_index=1))

    char_id = str(uuid4())
    db_session.add(Character(id=char_id, project_id=pid, name="主角"))

    setting_id = str(uuid4())
    db_session.add(SettingItem(id=setting_id, project_id=pid, title="世界观", item_type="world"))

    clue_id = str(uuid4())
    db_session.add(Clue(id=clue_id, project_id=pid, title="线索A"))

    outline_id = str(uuid4())
    db_session.add(OutlineItem(id=outline_id, project_id=pid, title="大纲A", order_index=1, item_type="plot"))

    track_id = str(uuid4())
    db_session.add(TimelineTrack(id=track_id, project_id=pid, title="主线"))
    db_session.flush()

    event_id = str(uuid4())
    db_session.add(
        TimelineEvent(id=event_id, project_id=pid, track_id=track_id, title="事件A", order_index=1)
    )
    db_session.flush()

    # 7 new join table records
    db_session.add(
        TimelineEventCharacter(
            id=str(uuid4()),
            project_id=pid,
            timeline_event_id=event_id,
            character_id=char_id,
        )
    )
    db_session.add(
        TimelineEventSetting(
            id=str(uuid4()),
            project_id=pid,
            timeline_event_id=event_id,
            setting_id=setting_id,
        )
    )
    db_session.add(
        TimelineEventClue(
            id=str(uuid4()),
            project_id=pid,
            timeline_event_id=event_id,
            clue_id=clue_id,
        )
    )
    db_session.add(
        OutlineItemCharacter(
            id=str(uuid4()),
            project_id=pid,
            outline_item_id=outline_id,
            character_id=char_id,
        )
    )
    db_session.add(
        OutlineItemSetting(
            id=str(uuid4()),
            project_id=pid,
            outline_item_id=outline_id,
            setting_id=setting_id,
        )
    )
    db_session.add(
        OutlineItemClue(
            id=str(uuid4()),
            project_id=pid,
            outline_item_id=outline_id,
            clue_id=clue_id,
        )
    )
    db_session.add(
        OutlineItemTimelineEvent(
            id=str(uuid4()),
            project_id=pid,
            outline_item_id=outline_id,
            timeline_event_id=event_id,
        )
    )

    db_session.commit()
    return pid


# ── Registry checks ──────────────────────────────────────────────


def test_new_join_tables_in_entity_models():
    for table in NEW_JOIN_TABLES:
        assert table in ENTITY_MODELS, f"{table} missing from ENTITY_MODELS"


def test_new_join_tables_in_project_children():
    for table in NEW_JOIN_TABLES:
        assert table in PROJECT_CHILDREN, f"{table} missing from PROJECT_CHILDREN"


def test_new_join_tables_in_restore_order():
    for table in NEW_JOIN_TABLES:
        assert table in RESTORE_ORDER, f"{table} missing from RESTORE_ORDER"


def test_new_join_tables_in_reference_fields():
    for table in NEW_JOIN_TABLES:
        assert table in REFERENCE_FIELDS, f"{table} missing from REFERENCE_FIELDS"


def test_restore_order_respects_dependencies():
    """Join tables must come after their referenced parent entities."""
    pos = {name: i for i, name in enumerate(RESTORE_ORDER)}
    # timeline_event_* must be after timeline_events, characters, settings, clues
    for t in ("timeline_event_characters", "timeline_event_settings", "timeline_event_clues"):
        assert pos[t] > pos["timeline_events"], f"{t} must come after timeline_events"
    assert pos["timeline_event_characters"] > pos["characters"]
    assert pos["timeline_event_settings"] > pos["settings"]
    assert pos["timeline_event_clues"] > pos["clues"]
    # outline_item_* must be after outlines
    for t in (
        "outline_item_characters",
        "outline_item_settings",
        "outline_item_clues",
        "outline_item_timeline_events",
    ):
        assert pos[t] > pos["outlines"], f"{t} must come after outlines"
    assert pos["outline_item_characters"] > pos["characters"]
    assert pos["outline_item_timeline_events"] > pos["timeline_events"]


# ── Export / Import round-trip ────────────────────────────────────


def test_export_includes_new_join_tables_in_manifest(db_session):
    pid = _seed_project(db_session)
    service = BackupService(db_session)
    backup_file = service.export_project_backup(pid)

    with ZipFile(backup_file.content, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))

    for table in NEW_JOIN_TABLES:
        assert table in manifest["tables"], f"{table} missing from manifest tables"
        assert manifest["tables"][table] >= 1, f"{table} count should be >= 1"


def test_export_creates_data_files_for_new_join_tables(db_session):
    pid = _seed_project(db_session)
    service = BackupService(db_session)
    backup_file = service.export_project_backup(pid)

    with ZipFile(backup_file.content, "r") as zf:
        names = zf.namelist()
        for table in NEW_JOIN_TABLES:
            assert f"data/{table}.json" in names, f"data/{table}.json not in zip"
            data = json.loads(zf.read(f"data/{table}.json").decode("utf-8"))
            assert len(data) >= 1, f"data/{table}.json should have at least 1 record"


def test_export_then_restore_round_trip(db_session):
    """Full round-trip: export with new join tables, then restore into a fresh DB."""
    pid = _seed_project(db_session)
    service = BackupService(db_session)
    backup_file = service.export_project_backup(pid)
    content = backup_file.content.read()

    # Create a new in-memory DB and restore into it
    engine2 = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine2)
    Session2 = sessionmaker(bind=engine2)
    session2 = Session2()

    restore_service = BackupService(session2)
    report = restore_service.restore_project_backup(content)
    assert report.project_id is not None
    assert report.project_id != pid  # should be a new project id

    # Verify restored join table records exist
    for table in NEW_JOIN_TABLES:
        model = ENTITY_MODELS[table]
        count = session2.query(model).count()
        assert count >= 1, f"restored {table} should have >= 1 records, got {count}"

    session2.close()


# ── Backward compatibility with old zips ──────────────────────────


def _build_old_style_zip(db_session) -> bytes:
    """Build a backup zip that looks like the old format (missing the 7 new join tables)."""
    pid = str(uuid4())
    project = Project(id=pid, title="旧格式项目")
    db_session.add(project)
    db_session.commit()

    service = BackupService(db_session)
    payload = service._build_payload(project)

    # Remove the 7 new join table data from payload
    for table in NEW_JOIN_TABLES:
        payload.pop(table, None)

    # Build zip without the new join table files
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
        manifest = payload["manifest"]
        # Remove new join table counts from manifest
        for table in NEW_JOIN_TABLES:
            manifest["tables"].pop(table, None)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("project.json", json.dumps(payload["project"], ensure_ascii=False, indent=2))
        for entity_name in PROJECT_CHILDREN:
            if entity_name in payload:
                zf.writestr(
                    f"data/{entity_name}.json",
                    json.dumps(payload[entity_name], ensure_ascii=False, indent=2),
                )
    buffer.seek(0)
    return buffer.read()


def test_restore_old_zip_without_new_join_tables(db_session):
    """Old zip missing the 7 new join tables should restore without errors."""
    old_zip = _build_old_style_zip(db_session)

    # Create fresh DB for restore
    engine2 = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine2)
    Session2 = sessionmaker(bind=engine2)
    session2 = Session2()

    restore_service = BackupService(session2)
    report = restore_service.restore_project_backup(old_zip)
    assert report.project_id is not None

    # The new join tables should simply have 0 records (no crash)
    for table in NEW_JOIN_TABLES:
        model = ENTITY_MODELS[table]
        count = session2.query(model).count()
        assert count == 0, f"old zip should restore {table} with 0 records, got {count}"

    session2.close()

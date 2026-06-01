"""Tests for character profile sections and dimensions (custom fields)."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402

import app.models.project  # noqa: E402, F401
import app.models.character  # noqa: E402, F401
import app.models.volume  # noqa: E402, F401
import app.models.chapter  # noqa: E402, F401

from app.models.character import Character  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.schemas.character import (  # noqa: E402
    VALID_DIMENSION_MAXES,
    CharacterCreate,
    CharacterProfileDimension,
    CharacterRead,
    CharacterUpdate,
    decode_profile_dimensions,
    decode_profile_sections,
    encode_profile_dimensions,
    encode_profile_sections,
    normalize_profile_dimensions,
    normalize_profile_sections,
)
from app.services.character_service import CharacterService  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project(session):
    pid = str(uuid4())
    now = datetime.now(timezone.utc)
    project = Project(id=pid, title="人物资料测试项目", created_at=now, updated_at=now)
    session.add(project)
    session.commit()
    return pid


# ---------------------------------------------------------------------------
# Normalize helpers
# ---------------------------------------------------------------------------


class TestNormalizeProfileSections:
    def test_empty_list(self):
        assert normalize_profile_sections([]) == []

    def test_valid_sections(self):
        raw = [
            {"id": "a", "title": "外貌", "content": "黑发", "collapsed": False},
            {"id": "b", "title": "性格", "content": "冷静", "collapsed": True},
        ]
        result = normalize_profile_sections(raw)
        assert len(result) == 2
        assert result[0]["title"] == "外貌"
        assert result[0]["order"] == 0
        assert result[1]["title"] == "性格"
        assert result[1]["order"] == 1
        assert result[1]["collapsed"] is True

    def test_empty_title_defaults(self):
        raw = [{"id": "x", "title": "", "content": "内容"}]
        result = normalize_profile_sections(raw)
        assert result[0]["title"] == "未命名资料"

    def test_truncates_long_title(self):
        raw = [{"id": "x", "title": "a" * 100, "content": ""}]
        result = normalize_profile_sections(raw)
        assert len(result[0]["title"]) == 48

    def test_max_sections_limit(self):
        raw = [{"id": f"s{i}", "title": f"Section {i}", "content": ""} for i in range(35)]
        result = normalize_profile_sections(raw)
        assert len(result) == 30

    def test_skips_non_dict_items(self):
        raw = ["invalid", 42, {"id": "ok", "title": "Valid", "content": "yes"}]
        result = normalize_profile_sections(raw)
        assert len(result) == 1
        assert result[0]["title"] == "Valid"


class TestNormalizeProfileDimensions:
    def test_empty_list(self):
        assert normalize_profile_dimensions([]) == []

    def test_valid_dimensions(self):
        raw = [
            {"id": "d1", "name": "行动力", "value": 80, "max": 100},
            {"id": "d2", "name": "智谋", "value": 60, "max": 100},
        ]
        result = normalize_profile_dimensions(raw)
        assert len(result) == 2
        assert result[0]["name"] == "行动力"
        assert result[0]["value"] == 80
        assert result[0]["order"] == 0

    def test_empty_name_defaults(self):
        raw = [{"id": "x", "name": "", "value": 50}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["name"] == "维度"

    def test_value_clamped(self):
        raw = [
            {"id": "a", "name": "Low", "value": -10},
            {"id": "b", "name": "High", "value": 200},
        ]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 0
        assert result[1]["value"] == 100

    def test_max_below_one_resets(self):
        raw = [{"id": "x", "name": "Dim", "value": 50, "max": 0}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["max"] == 100

    def test_max_dimensions_limit(self):
        raw = [{"id": f"d{i}", "name": f"Dim {i}", "value": 50} for i in range(15)]
        result = normalize_profile_dimensions(raw)
        assert len(result) == 12

    def test_five_scale_float_value(self):
        """5分制 with 0.5 step values should be preserved."""
        raw = [{"id": "d1", "name": "魅力", "value": 3.5, "max": 5}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 3.5
        assert result[0]["max"] == 5

    def test_ten_scale_value(self):
        """10分制 values should be preserved with float precision."""
        raw = [{"id": "d1", "name": "智力", "value": 7.3, "max": 10}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 7.3
        assert result[0]["max"] == 10

    def test_five_scale_clamped_above(self):
        """Value exceeding 5-scale max should clamp to 5."""
        raw = [{"id": "d1", "name": "力", "value": 8, "max": 5}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 5.0
        assert result[0]["max"] == 5

    def test_ten_scale_clamped_above(self):
        """Value exceeding 10-scale max should clamp to 10."""
        raw = [{"id": "d1", "name": "速", "value": 15.5, "max": 10}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 10.0
        assert result[0]["max"] == 10

    def test_invalid_max_defaults_to_100(self):
        """Max not in VALID_DIMENSION_MAXES should default to 100."""
        raw = [{"id": "d1", "name": "X", "value": 50, "max": 7}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["max"] == 100
        assert result[0]["value"] == 50.0

    def test_float_rounding_one_decimal(self):
        """Values should be rounded to 1 decimal to avoid float noise."""
        raw = [{"id": "d1", "name": "R", "value": 3.14159, "max": 5}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 3.1

    def test_valid_dimension_maxes_constant(self):
        """VALID_DIMENSION_MAXES should contain exactly 5, 10, 100."""
        assert VALID_DIMENSION_MAXES == {5, 10, 100}

    def test_value_type_is_float(self):
        """Normalized value should always be float, even when input is int."""
        raw = [{"id": "d1", "name": "力", "value": 3, "max": 100}]
        result = normalize_profile_dimensions(raw)
        assert isinstance(result[0]["value"], float)
        assert result[0]["value"] == 3.0

    def test_default_value_half_of_max(self):
        """When value is missing, default should be max/2."""
        raw = [{"id": "d1", "name": "力", "max": 10}]
        result = normalize_profile_dimensions(raw)
        assert result[0]["value"] == 5.0

        raw5 = [{"id": "d2", "name": "力", "max": 5}]
        result5 = normalize_profile_dimensions(raw5)
        assert result5[0]["value"] == 2.5


# ---------------------------------------------------------------------------
# Encode / decode helpers
# ---------------------------------------------------------------------------


class TestEncodeDecode:
    def test_encode_sections_roundtrip(self):
        sections = [{"id": "a", "title": "Test", "content": "Hello", "order": 0, "collapsed": False}]
        encoded = encode_profile_sections(sections)
        assert isinstance(encoded, str)
        decoded = decode_profile_sections(encoded)
        assert decoded[0]["title"] == "Test"

    def test_decode_sections_none(self):
        assert decode_profile_sections(None) == []

    def test_decode_sections_invalid_json(self):
        assert decode_profile_sections("not json") == []

    def test_decode_sections_list_passthrough(self):
        raw = [{"id": "a", "title": "Pass", "content": ""}]
        result = decode_profile_sections(raw)
        assert result[0]["title"] == "Pass"

    def test_encode_dimensions_roundtrip(self):
        dims = [{"id": "d1", "name": "行动力", "value": 75, "max": 100, "order": 0}]
        encoded = encode_profile_dimensions(dims)
        assert isinstance(encoded, str)
        decoded = decode_profile_dimensions(encoded)
        assert decoded[0]["name"] == "行动力"
        assert decoded[0]["value"] == 75

    def test_decode_dimensions_none(self):
        assert decode_profile_dimensions(None) == []

    def test_encode_string_passthrough(self):
        raw_str = '[{"id":"a","title":"T","content":"","order":0,"collapsed":false}]'
        assert encode_profile_sections(raw_str) == raw_str
        assert encode_profile_dimensions(raw_str) == raw_str


# ---------------------------------------------------------------------------
# Pydantic schema validation
# ---------------------------------------------------------------------------


class TestCharacterSchemaValidation:
    def test_create_with_profile_data(self):
        data = CharacterCreate(
            name="张三",
            profile_sections=[
                {"id": "s1", "title": "外貌", "content": "黑发黑眼"},
            ],
            profile_dimensions=[
                {"id": "d1", "name": "行动力", "value": 80},
                {"id": "d2", "name": "智谋", "value": 60},
            ],
        )
        assert len(data.profile_sections) == 1
        assert data.profile_sections[0].title == "外貌"
        assert len(data.profile_dimensions) == 2
        assert data.profile_dimensions[0].value == 80

    def test_create_with_float_dimension_values(self):
        """CharacterCreate should accept float values for dimensions."""
        data = CharacterCreate(
            name="浮点测试",
            profile_dimensions=[
                {"id": "d1", "name": "力", "value": 2.5, "max": 5},
                {"id": "d2", "name": "智", "value": 8.7, "max": 10},
            ],
        )
        assert data.profile_dimensions[0].value == 2.5
        assert data.profile_dimensions[1].value == 8.7

    def test_dimension_model_float_value(self):
        """CharacterProfileDimension model should store float value."""
        dim = CharacterProfileDimension(id="d1", name="力", value=3.5, max=5, order=0)
        assert isinstance(dim.value, float)
        assert dim.value == 3.5

    def test_create_defaults_to_empty(self):
        data = CharacterCreate(name="李四")
        assert data.profile_sections == []
        assert data.profile_dimensions == []

    def test_update_partial(self):
        data = CharacterUpdate(
            profile_sections=[{"id": "s1", "title": "New", "content": "data"}],
        )
        assert len(data.profile_sections) == 1

    def test_read_parses_json_string(self):
        """CharacterRead should parse DB JSON strings into arrays."""
        raw_data = {
            "id": "test-id",
            "project_id": "proj-id",
            "name": "Test",
            "role": "supporting",
            "importance": "normal",
            "status": "active",
            "faction": None,
            "summary": "",
            "biography": "",
            "appearance": "",
            "personality": "",
            "background": "",
            "ability": "",
            "motivation": "",
            "secret": "",
            "arc": "",
            "notes": "",
            "profile_sections": json.dumps([
                {"id": "s1", "title": "外貌", "content": "test", "order": 0, "collapsed": False}
            ]),
            "profile_dimensions": json.dumps([
                {"id": "d1", "name": "行动力", "value": 70, "max": 100, "order": 0}
            ]),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "deleted_at": None,
            "version": 1,
        }
        read = CharacterRead.model_validate(raw_data)
        assert isinstance(read.profile_sections, list)
        assert read.profile_sections[0].title == "外貌"
        assert isinstance(read.profile_dimensions, list)
        assert read.profile_dimensions[0].value == 70

    def test_read_handles_empty_json(self):
        raw_data = {
            "id": "test-id",
            "project_id": "proj-id",
            "name": "Test",
            "role": "supporting",
            "importance": "normal",
            "status": "active",
            "faction": None,
            "summary": "",
            "biography": "",
            "appearance": "",
            "personality": "",
            "background": "",
            "ability": "",
            "motivation": "",
            "secret": "",
            "arc": "",
            "notes": "",
            "profile_sections": "[]",
            "profile_dimensions": "[]",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "deleted_at": None,
            "version": 1,
        }
        read = CharacterRead.model_validate(raw_data)
        assert read.profile_sections == []
        assert read.profile_dimensions == []


# ---------------------------------------------------------------------------
# Service integration (create / update / search)
# ---------------------------------------------------------------------------


class TestCharacterServiceProfile:
    def test_create_with_profile_sections(self, db_session):
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        data = CharacterCreate(
            name="王五",
            profile_sections=[
                {"id": "s1", "title": "外貌", "content": "高大"},
                {"id": "s2", "title": "性格", "content": "温和"},
            ],
            profile_dimensions=[
                {"id": "d1", "name": "行动力", "value": 75},
            ],
        )
        character = service.create_character(project_id, data)

        # DB stores JSON string
        assert isinstance(character.profile_sections, str)
        parsed = json.loads(character.profile_sections)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "外貌"

        dim_parsed = json.loads(character.profile_dimensions)
        assert len(dim_parsed) == 1
        assert dim_parsed[0]["name"] == "行动力"

    def test_create_without_profile_defaults_empty(self, db_session):
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        data = CharacterCreate(name="赵六")
        character = service.create_character(project_id, data)

        assert character.profile_sections == "[]"
        assert character.profile_dimensions == "[]"

    def test_update_profile_sections(self, db_session):
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        character = service.create_character(
            project_id, CharacterCreate(name="更新测试")
        )

        update_data = CharacterUpdate(
            profile_sections=[
                {"id": "s1", "title": "新资料", "content": "新内容"},
            ]
        )
        updated = service.update_character(character.id, update_data)
        parsed = json.loads(updated.profile_sections)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "新资料"

    def test_update_profile_dimensions(self, db_session):
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        character = service.create_character(
            project_id, CharacterCreate(name="维度测试")
        )

        update_data = CharacterUpdate(
            profile_dimensions=[
                {"id": "d1", "name": "勇气", "value": 90},
                {"id": "d2", "name": "智慧", "value": 65},
            ]
        )
        updated = service.update_character(character.id, update_data)
        parsed = json.loads(updated.profile_dimensions)
        assert len(parsed) == 2
        assert parsed[0]["value"] == 90

    def test_keyword_search_includes_profile_sections(self, db_session):
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        service.create_character(
            project_id,
            CharacterCreate(
                name="搜索测试",
                profile_sections=[
                    {"id": "s1", "title": "特殊能力", "content": "操控火焰的独特能力"},
                ],
            ),
        )

        results = service.list_project_characters(
            project_id, keyword="操控火焰"
        )
        assert len(results) == 1
        assert results[0].name == "搜索测试"

    def test_value_clamping_in_create(self, db_session):
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        data = CharacterCreate(
            name="Clamp测试",
            profile_dimensions=[
                {"id": "d1", "name": "Over", "value": 999},
                {"id": "d2", "name": "Under", "value": -50},
            ],
        )
        character = service.create_character(project_id, data)
        parsed = json.loads(character.profile_dimensions)
        assert parsed[0]["value"] == 100
        assert parsed[1]["value"] == 0

    def test_float_dimension_values_in_create(self, db_session):
        """Service should store float values with different scale modes."""
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        data = CharacterCreate(
            name="多维测试",
            profile_dimensions=[
                {"id": "d1", "name": "武力", "value": 3.5, "max": 5},
                {"id": "d2", "name": "智谋", "value": 7.5, "max": 10},
                {"id": "d3", "name": "魅力", "value": 88.3, "max": 100},
            ],
        )
        character = service.create_character(project_id, data)
        parsed = json.loads(character.profile_dimensions)
        assert parsed[0]["value"] == 3.5
        assert parsed[0]["max"] == 5
        assert parsed[1]["value"] == 7.5
        assert parsed[1]["max"] == 10
        assert parsed[2]["value"] == 88.3
        assert parsed[2]["max"] == 100

    def test_legacy_payload_still_works(self, db_session):
        """Old clients not sending new fields should not break."""
        project_id = _make_project(db_session)
        service = CharacterService(db_session)

        data = CharacterCreate(
            name="旧客户端",
            summary="测试摘要",
            biography="测试传记",
            appearance="外貌描述",
        )
        character = service.create_character(project_id, data)
        assert character.name == "旧客户端"
        assert character.summary == "测试摘要"
        assert character.profile_sections == "[]"
        assert character.profile_dimensions == "[]"

# Tests for training service -- flag/dataset/template CRUD.

from pathlib import Path

import pytest

from pct.models.enums import AnnotationCategory, CurationStatus, FlagType
from pct.training.models import (
    DatasetCreate,
    DatasetUpdate,
    FlagCreate,
    FlagUpdate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
)
from pct.training.service import TrainingService


@pytest.fixture
def training_svc(tmp_path: Path) -> TrainingService:
    (tmp_path / ".pct").mkdir()
    return TrainingService(tmp_path)


class TestFlagCRUD:
    def test_create_flag(self, training_svc: TrainingService):
        flag = training_svc.create_flag(
            FlagCreate(
                session_ref="sess-1",
                message_index=3,
                flag_type=FlagType.positive,
            )
        )
        assert flag.id
        assert flag.session_ref == "sess-1"
        assert flag.message_range == [3]
        assert flag.flag_type == FlagType.positive
        assert flag.curation_status == CurationStatus.raw

    def test_create_flag_with_annotation(self, training_svc: TrainingService):
        flag = training_svc.create_flag(
            FlagCreate(
                session_ref="sess-1",
                message_index=0,
                flag_type=FlagType.negative,
                annotation_category=AnnotationCategory.accuracy,
                note="Wrong answer",
            )
        )
        assert flag.annotation_category == AnnotationCategory.accuracy
        assert flag.note == "Wrong answer"

    def test_list_flags_empty(self, training_svc: TrainingService):
        flags = training_svc.list_flags()
        assert flags == []

    def test_list_flags(self, training_svc: TrainingService):
        training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.positive)
        )
        training_svc.create_flag(
            FlagCreate(session_ref="s2", message_index=1, flag_type=FlagType.negative)
        )
        flags = training_svc.list_flags()
        assert len(flags) == 2

    def test_list_flags_filter_by_type(self, training_svc: TrainingService):
        training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.positive)
        )
        training_svc.create_flag(
            FlagCreate(session_ref="s2", message_index=1, flag_type=FlagType.negative)
        )
        pos = training_svc.list_flags(flag_type="positive")
        assert len(pos) == 1
        assert pos[0].flag_type == FlagType.positive

    def test_list_flags_filter_by_status(self, training_svc: TrainingService):
        flag = training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.positive)
        )
        training_svc.update_flag(flag.id, FlagUpdate(curation_status=CurationStatus.curated))
        training_svc.create_flag(
            FlagCreate(session_ref="s2", message_index=1, flag_type=FlagType.positive)
        )
        curated = training_svc.list_flags(status="curated")
        assert len(curated) == 1

    def test_get_flag(self, training_svc: TrainingService):
        created = training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.positive)
        )
        fetched = training_svc.get_flag(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_flag_not_found(self, training_svc: TrainingService):
        assert training_svc.get_flag("nonexistent") is None

    def test_update_flag(self, training_svc: TrainingService):
        flag = training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.positive)
        )
        updated = training_svc.update_flag(
            flag.id,
            FlagUpdate(
                annotation_category=AnnotationCategory.style,
                note="Better style needed",
                curation_status=CurationStatus.curated,
            ),
        )
        assert updated is not None
        assert updated.annotation_category == AnnotationCategory.style
        assert updated.note == "Better style needed"
        assert updated.curation_status == CurationStatus.curated

    def test_update_flag_not_found(self, training_svc: TrainingService):
        assert training_svc.update_flag("nope", FlagUpdate(note="x")) is None

    def test_update_flag_edited_response(self, training_svc: TrainingService):
        flag = training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.negative)
        )
        updated = training_svc.update_flag(flag.id, FlagUpdate(edited_response="Fixed response"))
        assert updated is not None
        assert updated.edited_response == "Fixed response"

    def test_delete_flag(self, training_svc: TrainingService):
        flag = training_svc.create_flag(
            FlagCreate(session_ref="s1", message_index=0, flag_type=FlagType.positive)
        )
        assert training_svc.delete_flag(flag.id) is True
        assert training_svc.get_flag(flag.id) is None

    def test_delete_flag_not_found(self, training_svc: TrainingService):
        assert training_svc.delete_flag("nope") is False

class TestDatasetCRUD:
    def test_create_dataset(self, training_svc: TrainingService):
        ds = training_svc.create_dataset(DatasetCreate(name="DS1", description="Test dataset"))
        assert ds.id
        assert ds.name == "DS1"
        assert ds.description == "Test dataset"
        assert ds.entries == []

    def test_list_datasets_empty(self, training_svc: TrainingService):
        assert training_svc.list_datasets() == []

    def test_list_datasets(self, training_svc: TrainingService):
        training_svc.create_dataset(DatasetCreate(name="DS1"))
        training_svc.create_dataset(DatasetCreate(name="DS2"))
        datasets = training_svc.list_datasets()
        assert len(datasets) == 2

    def test_get_dataset(self, training_svc: TrainingService):
        created = training_svc.create_dataset(DatasetCreate(name="DS1"))
        fetched = training_svc.get_dataset(created.id)
        assert fetched is not None
        assert fetched.name == "DS1"

    def test_get_dataset_not_found(self, training_svc: TrainingService):
        assert training_svc.get_dataset("nope") is None

    def test_update_dataset_name(self, training_svc: TrainingService):
        ds = training_svc.create_dataset(DatasetCreate(name="V1"))
        updated = training_svc.update_dataset(ds.id, DatasetUpdate(name="V2"))
        assert updated is not None
        assert updated.name == "V2"

    def test_update_dataset_entries(self, training_svc: TrainingService):
        ds = training_svc.create_dataset(DatasetCreate(name="DS1"))
        updated = training_svc.update_dataset(
            ds.id, DatasetUpdate(entry_ids=["flag-1", "flag-2"])
        )
        assert updated is not None
        assert updated.entries == ["flag-1", "flag-2"]

    def test_update_dataset_not_found(self, training_svc: TrainingService):
        assert training_svc.update_dataset("nope", DatasetUpdate(name="x")) is None

    def test_delete_dataset(self, training_svc: TrainingService):
        ds = training_svc.create_dataset(DatasetCreate(name="DS1"))
        assert training_svc.delete_dataset(ds.id) is True
        assert training_svc.get_dataset(ds.id) is None

    def test_delete_dataset_not_found(self, training_svc: TrainingService):
        assert training_svc.delete_dataset("nope") is False


class TestPromptTemplateCRUD:
    def test_create_template(self, training_svc: TrainingService):
        tmpl = training_svc.create_template(
            PromptTemplateCreate(name="System Prompt", content="You are a helpful assistant.")
        )
        assert tmpl.id
        assert tmpl.name == "System Prompt"
        assert tmpl.active_version == 1
        assert len(tmpl.versions) == 1
        assert tmpl.versions[0].content == "You are a helpful assistant."

    def test_list_templates_empty(self, training_svc: TrainingService):
        assert training_svc.list_templates() == []

    def test_list_templates(self, training_svc: TrainingService):
        training_svc.create_template(PromptTemplateCreate(name="T1", content="c1"))
        training_svc.create_template(PromptTemplateCreate(name="T2", content="c2"))
        templates = training_svc.list_templates()
        assert len(templates) == 2

    def test_get_template(self, training_svc: TrainingService):
        created = training_svc.create_template(
            PromptTemplateCreate(name="T1", content="v1 content")
        )
        fetched = training_svc.get_template(created.id)
        assert fetched is not None
        assert fetched.name == "T1"

    def test_get_template_not_found(self, training_svc: TrainingService):
        assert training_svc.get_template("nope") is None

    def test_update_template_creates_new_version(self, training_svc: TrainingService):
        tmpl = training_svc.create_template(
            PromptTemplateCreate(name="T1", content="v1 content")
        )
        updated = training_svc.update_template(
            tmpl.id, PromptTemplateUpdate(content="v2 content")
        )
        assert updated is not None
        assert updated.active_version == 2
        assert len(updated.versions) == 2
        assert updated.versions[0].content == "v1 content"
        assert updated.versions[1].content == "v2 content"

    def test_update_template_multiple_versions(self, training_svc: TrainingService):
        tmpl = training_svc.create_template(
            PromptTemplateCreate(name="T1", content="v1")
        )
        training_svc.update_template(tmpl.id, PromptTemplateUpdate(content="v2"))
        updated = training_svc.update_template(tmpl.id, PromptTemplateUpdate(content="v3"))
        assert updated is not None
        assert updated.active_version == 3
        assert len(updated.versions) == 3

    def test_update_template_not_found(self, training_svc: TrainingService):
        assert training_svc.update_template("nope", PromptTemplateUpdate(content="x")) is None

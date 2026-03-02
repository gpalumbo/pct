# Training service -- flag/dataset/template CRUD with YAML file storage.

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import yaml

from pct.models.training import (
    Dataset,
    PromptTemplate,
    PromptTemplateVersion,
    TrainingFlag,
)
from pct.storage._atomic import atomic_write
from pct.training.models import (
    DatasetCreate,
    DatasetUpdate,
    FlagCreate,
    FlagUpdate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid4().hex[:8]


class TrainingService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._training_dir = project_root / ".pct" / "training"
        self._flags_dir = self._training_dir / "flags"
        self._datasets_dir = self._training_dir / "datasets"
        self._snapshots_dir = self._training_dir / "snapshots"
        self._templates_dir = self._training_dir / "prompt_templates"

    # ---- Flags ----

    def create_flag(self, req: FlagCreate) -> TrainingFlag:
        flag_id = _new_id()
        snapshot_id = _new_id()
        now = _utcnow()
        flag = TrainingFlag(
            id=flag_id,
            session_ref=req.session_ref,
            message_range=[req.message_index],
            context_snapshot_id=snapshot_id,
            agent_id="",
            model_id="",
            flag_type=req.flag_type,
            annotation_category=req.annotation_category or "other",
            note=req.note or None,
            created_at=now,
        )
        self._save_flag(flag)
        return flag

    def list_flags(
        self,
        flag_type: str | None = None,
        status: str | None = None,
    ) -> list[TrainingFlag]:
        self._flags_dir.mkdir(parents=True, exist_ok=True)
        flags: list[TrainingFlag] = []
        for path in sorted(self._flags_dir.glob("*.yaml")):
            flag = self._load_flag_from_path(path)
            if flag is None:
                continue
            if flag_type is not None and flag.flag_type.value != flag_type:
                continue
            if status is not None and flag.curation_status.value != status:
                continue
            flags.append(flag)
        return flags

    def get_flag(self, flag_id: str) -> TrainingFlag | None:
        path = self._flags_dir / f"{flag_id}.yaml"
        if not path.exists():
            return None
        return self._load_flag_from_path(path)

    def update_flag(self, flag_id: str, req: FlagUpdate) -> TrainingFlag | None:
        flag = self.get_flag(flag_id)
        if flag is None:
            return None
        if req.annotation_category is not None:
            flag.annotation_category = req.annotation_category
        if req.note is not None:
            flag.note = req.note
        if req.curation_status is not None:
            flag.curation_status = req.curation_status
        if req.edited_response is not None:
            flag.edited_response = req.edited_response
        self._save_flag(flag)
        return flag

    def delete_flag(self, flag_id: str) -> bool:
        path = self._flags_dir / f"{flag_id}.yaml"
        if not path.exists():
            return False
        path.unlink()
        return True

    def _save_flag(self, flag: TrainingFlag) -> None:
        self._flags_dir.mkdir(parents=True, exist_ok=True)
        data = flag.model_dump(mode="json")
        atomic_write(self._flags_dir / f"{flag.id}.yaml", yaml.safe_dump(data, sort_keys=False))

    def _load_flag_from_path(self, path: Path) -> TrainingFlag | None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return TrainingFlag(**data)
        except Exception:
            return None
    # ---- Datasets ----

    def create_dataset(self, req: DatasetCreate) -> Dataset:
        ds_id = _new_id()
        now = _utcnow()
        ds = Dataset(
            id=ds_id,
            name=req.name,
            description=req.description or None,
            created_at=now,
            updated_at=now,
        )
        self._save_dataset(ds)
        return ds

    def list_datasets(self) -> list[Dataset]:
        self._datasets_dir.mkdir(parents=True, exist_ok=True)
        datasets: list[Dataset] = []
        for path in sorted(self._datasets_dir.glob("*.yaml")):
            ds = self._load_dataset_from_path(path)
            if ds is not None:
                datasets.append(ds)
        return datasets

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        path = self._datasets_dir / f"{dataset_id}.yaml"
        if not path.exists():
            return None
        return self._load_dataset_from_path(path)

    def update_dataset(self, dataset_id: str, req: DatasetUpdate) -> Dataset | None:
        ds = self.get_dataset(dataset_id)
        if ds is None:
            return None
        if req.name is not None:
            ds.name = req.name
        if req.description is not None:
            ds.description = req.description
        if req.entry_ids is not None:
            ds.entries = req.entry_ids
        ds.updated_at = _utcnow()
        self._save_dataset(ds)
        return ds

    def delete_dataset(self, dataset_id: str) -> bool:
        path = self._datasets_dir / f"{dataset_id}.yaml"
        if not path.exists():
            return False
        path.unlink()
        return True

    def _save_dataset(self, ds: Dataset) -> None:
        self._datasets_dir.mkdir(parents=True, exist_ok=True)
        data = ds.model_dump(mode="json")
        atomic_write(self._datasets_dir / f"{ds.id}.yaml", yaml.safe_dump(data, sort_keys=False))

    def _load_dataset_from_path(self, path: Path) -> Dataset | None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return Dataset(**data)
        except Exception:
            return None
    # ---- Prompt Templates ----

    def create_template(self, req: PromptTemplateCreate) -> PromptTemplate:
        tmpl_id = _new_id()
        now = _utcnow()
        version = PromptTemplateVersion(
            version=1,
            content=req.content,
            created_at=now,
        )
        tmpl = PromptTemplate(
            id=tmpl_id,
            name=req.name,
            versions=[version],
            active_version=1,
        )
        self._save_template(tmpl)
        return tmpl

    def list_templates(self) -> list[PromptTemplate]:
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        templates: list[PromptTemplate] = []
        for path in sorted(self._templates_dir.glob("*.yaml")):
            tmpl = self._load_template_from_path(path)
            if tmpl is not None:
                templates.append(tmpl)
        return templates

    def get_template(self, template_id: str) -> PromptTemplate | None:
        path = self._templates_dir / f"{template_id}.yaml"
        if not path.exists():
            return None
        return self._load_template_from_path(path)

    def update_template(self, template_id: str, req: PromptTemplateUpdate) -> PromptTemplate | None:
        tmpl = self.get_template(template_id)
        if tmpl is None:
            return None
        next_version = tmpl.active_version + 1
        now = _utcnow()
        new_ver = PromptTemplateVersion(
            version=next_version,
            content=req.content,
            created_at=now,
        )
        tmpl.versions.append(new_ver)
        tmpl.active_version = next_version
        self._save_template(tmpl)
        return tmpl

    def _save_template(self, tmpl: PromptTemplate) -> None:
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        data = tmpl.model_dump(mode="json")
        atomic_write(self._templates_dir / f"{tmpl.id}.yaml", yaml.safe_dump(data, sort_keys=False))

    def _load_template_from_path(self, path: Path) -> PromptTemplate | None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return PromptTemplate(**data)
        except Exception:
            return None

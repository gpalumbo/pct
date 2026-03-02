# Training router -- /api/training endpoints.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pct.auth.dependencies import get_current_user, get_settings
from pct.config import Settings
from pct.training.models import (
    DatasetCreate,
    DatasetUpdate,
    FlagCreate,
    FlagUpdate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
)
from pct.training.service import TrainingService

router = APIRouter(prefix="/api/training", tags=["training"])


def _training_service(settings: Settings = Depends(get_settings)) -> TrainingService:
    return TrainingService(settings.project_root)


# ---- Flags ----


@router.post("/flags")
async def create_flag(
    req: FlagCreate,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    flag = svc.create_flag(req)
    return flag.model_dump(mode="json")


@router.get("/flags")
async def list_flags(
    flag_type: str | None = None,
    status: str | None = None,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    flags = svc.list_flags(flag_type=flag_type, status=status)
    return [f.model_dump(mode="json") for f in flags]


@router.get("/flags/{flag_id}")
async def get_flag(
    flag_id: str,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    flag = svc.get_flag(flag_id)
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag.model_dump(mode="json")


@router.put("/flags/{flag_id}")
async def update_flag(
    flag_id: str,
    req: FlagUpdate,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    flag = svc.update_flag(flag_id, req)
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag.model_dump(mode="json")


@router.delete("/flags/{flag_id}")
async def delete_flag(
    flag_id: str,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    if not svc.delete_flag(flag_id):
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"deleted": True}

# ---- Datasets ----


@router.post("/datasets")
async def create_dataset(
    req: DatasetCreate,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    ds = svc.create_dataset(req)
    return ds.model_dump(mode="json")


@router.get("/datasets")
async def list_datasets(
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    datasets = svc.list_datasets()
    return [d.model_dump(mode="json") for d in datasets]


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    ds = svc.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds.model_dump(mode="json")


@router.put("/datasets/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    req: DatasetUpdate,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    ds = svc.update_dataset(dataset_id, req)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds.model_dump(mode="json")


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    if not svc.delete_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"deleted": True}


# ---- Prompt Templates ----


@router.post("/prompt-templates")
async def create_template(
    req: PromptTemplateCreate,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    tmpl = svc.create_template(req)
    return tmpl.model_dump(mode="json")


@router.get("/prompt-templates")
async def list_templates(
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    templates = svc.list_templates()
    return [t.model_dump(mode="json") for t in templates]


@router.get("/prompt-templates/{template_id}")
async def get_template(
    template_id: str,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    tmpl = svc.get_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl.model_dump(mode="json")


@router.put("/prompt-templates/{template_id}")
async def update_template(
    template_id: str,
    req: PromptTemplateUpdate,
    svc: TrainingService = Depends(_training_service),
    _user: str = Depends(get_current_user),
):
    tmpl = svc.update_template(template_id, req)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl.model_dump(mode="json")

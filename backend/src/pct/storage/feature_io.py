"""Feature I/O — feature_spec.md + metadata.yaml."""

from pathlib import Path

import yaml

from pct.models.core import Feature
from pct.storage._atomic import atomic_write
from pct.storage.directory_manager import create_feature_dir


def _feature_admin_dir(project_root: Path, feature_id: str) -> Path:
    return project_root / "pct-admin" / "active-features" / feature_id


def _backlog_dir(project_root: Path) -> Path:
    return project_root / "pct-admin" / "feature_backlog"


def load_feature(project_root: Path, feature_id: str) -> Feature | None:
    """Load feature from metadata.yaml in pct-admin."""
    meta_path = _feature_admin_dir(project_root, feature_id) / "metadata.yaml"
    if not meta_path.exists():
        return None
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    if data is None:
        return None
    data.setdefault("id", feature_id)
    return Feature(**data)


def save_feature_metadata(project_root: Path, feature: Feature) -> None:
    """Atomically write feature metadata.yaml."""
    admin_dir = _feature_admin_dir(project_root, feature.id)
    admin_dir.mkdir(parents=True, exist_ok=True)

    meta_path = admin_dir / "metadata.yaml"
    data = feature.model_dump(mode="json", exclude={"tasks"})
    content = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    atomic_write(meta_path, content)


def save_feature_spec(project_root: Path, feature_id: str, content: str) -> None:
    """Write feature_spec.md."""
    admin_dir = _feature_admin_dir(project_root, feature_id)
    admin_dir.mkdir(parents=True, exist_ok=True)
    spec_path = admin_dir / "feature_spec.md"
    spec_path.write_text(content, encoding="utf-8")


def load_feature_spec(project_root: Path, feature_id: str) -> str:
    """Read feature_spec.md."""
    spec_path = _feature_admin_dir(project_root, feature_id) / "feature_spec.md"
    if not spec_path.exists():
        return ""
    return spec_path.read_text(encoding="utf-8")


def list_features(project_root: Path) -> list[Feature]:
    """List all active features."""
    features_dir = project_root / "pct-admin" / "active-features"
    if not features_dir.exists():
        return []
    features = []
    for d in sorted(features_dir.iterdir()):
        if d.is_dir():
            f = load_feature(project_root, d.name)
            if f is not None:
                features.append(f)
    return features


def list_backlog(project_root: Path) -> list[str]:
    """List backlog spec filenames."""
    backlog_dir = _backlog_dir(project_root)
    if not backlog_dir.exists():
        return []
    return sorted(f.name for f in backlog_dir.glob("*.md"))


def activate_feature(project_root: Path, feature: Feature) -> None:
    """Move feature from backlog to active, create dirs."""
    create_feature_dir(project_root, feature.id)
    save_feature_metadata(project_root, feature)

    # Create feature document in work dir
    work_doc = project_root / "work" / feature.id / f"{feature.id}.md"
    if not work_doc.exists():
        work_doc.write_text(f"# {feature.title}\n\n", encoding="utf-8")

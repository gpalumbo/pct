"""Tests for feature I/O."""

from pathlib import Path

from pct.models.core import Feature
from pct.models.enums import FeatureStage
from pct.storage.feature_io import (
    activate_feature,
    list_features,
    load_feature,
    load_feature_spec,
    save_feature_metadata,
    save_feature_spec,
)


class TestFeatureIO:
    def test_save_and_load(self, tmp_project_root: Path):
        feature = Feature(id="f1-core", title="Core Server", stage=FeatureStage.planning)
        save_feature_metadata(tmp_project_root, feature)
        loaded = load_feature(tmp_project_root, "f1-core")
        assert loaded is not None
        assert loaded.id == "f1-core"
        assert loaded.title == "Core Server"
        assert loaded.stage == FeatureStage.planning

    def test_load_nonexistent(self, tmp_project_root: Path):
        assert load_feature(tmp_project_root, "nonexistent") is None

    def test_save_and_load_spec(self, tmp_project_root: Path):
        save_feature_spec(tmp_project_root, "f1", "# Feature Spec\n\nContent.")
        content = load_feature_spec(tmp_project_root, "f1")
        assert "Feature Spec" in content
        assert "Content." in content

    def test_load_spec_nonexistent(self, tmp_project_root: Path):
        assert load_feature_spec(tmp_project_root, "nope") == ""

    def test_list_features(self, tmp_project_root: Path):
        for i in range(3):
            f = Feature(id=f"f{i}", title=f"Feature {i}")
            save_feature_metadata(tmp_project_root, f)
        features = list_features(tmp_project_root)
        assert len(features) == 3

    def test_list_features_empty(self, tmp_path: Path):
        assert list_features(tmp_path) == []

    def test_activate_feature(self, tmp_project_root: Path):
        feature = Feature(id="f-new", title="New Feature")
        activate_feature(tmp_project_root, feature)

        # Check dirs created
        assert (tmp_project_root / "work" / "f-new").is_dir()
        assert (tmp_project_root / "pct-admin" / "active-features" / "f-new").is_dir()

        # Check metadata saved
        loaded = load_feature(tmp_project_root, "f-new")
        assert loaded is not None
        assert loaded.title == "New Feature"

        # Check work doc created
        work_doc = tmp_project_root / "work" / "f-new" / "f-new.md"
        assert work_doc.exists()

"""Board service — feature/task CRUD, workflow movement, lifecycle."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from pct.board.dag_validation import validate_dag
from pct.board.models import FeatureCreate, FeatureUpdate, TaskCreate, TaskMove, TaskUpdate
from pct.board.pert import PertData, build_pert_data
from pct.board.wikilinks import parse_wikilink
from pct.models.core import Feature, Project, Task
from pct.models.enums import ExecutionStatus, FeatureStage
from pct.storage.feature_io import activate_feature, list_features, load_feature, save_feature_metadata
from pct.storage.project_io import load_project_config
from pct.storage.task_io import delete_task, list_tasks, load_task, save_task


class BoardService:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def _load_project(self) -> Project:
        project = load_project_config(self.project_root)
        if project is None:
            raise ValueError("Project not initialized")
        return project

    def _stage_ids(self) -> list[str]:
        project = self._load_project()
        return [s.id for s in project.workflow_stages if s.enabled]

    def _done_stage_id(self) -> str:
        stages = self._stage_ids()
        return stages[-1] if stages else "done"

    def get_board_state(self) -> dict:
        """Get full board state."""
        project = self._load_project()
        features = list_features(self.project_root)
        feature_data = []
        for f in features:
            tasks = list_tasks(self.project_root, f.id)
            feature_data.append({
                **f.model_dump(mode="json"),
                "tasks": [t.model_dump(mode="json") for t in tasks],
            })
        return {
            "features": feature_data,
            "workflow_stages": [s.model_dump(mode="json") for s in project.workflow_stages],
        }

    # ── Feature CRUD ──

    def create_feature(self, req: FeatureCreate) -> Feature:
        stages = self._stage_ids()
        first_stage = stages[0] if stages else "refine-spec"

        feature = Feature(
            id=req.id,
            title=req.title,
            stage=FeatureStage.planning,
            spec_path=f"pct-admin/active-features/{req.id}/feature_spec.md",
        )
        activate_feature(self.project_root, feature)

        # Create Refine Feature task at first stage
        refine_task = Task(
            id="refine-feature",
            title=f"Refine Feature: {req.title}",
            feature_id=req.id,
            current_stage_id=first_stage,
        )
        save_task(self.project_root, refine_task, body=f"# Refine Feature: {req.title}\n\n{req.spec_content}")

        return feature

    def get_feature(self, feature_id: str) -> Feature | None:
        return load_feature(self.project_root, feature_id)

    def update_feature(self, feature_id: str, req: FeatureUpdate) -> Feature | None:
        feature = load_feature(self.project_root, feature_id)
        if feature is None:
            return None
        if req.title is not None:
            feature.title = req.title
        if req.stage is not None:
            feature.stage = req.stage
        feature.updated_at = datetime.now(UTC)
        save_feature_metadata(self.project_root, feature)
        return feature

    def delete_feature(self, feature_id: str) -> bool:
        feature = load_feature(self.project_root, feature_id)
        if feature is None:
            return False
        # Delete all task files
        tasks = list_tasks(self.project_root, feature_id)
        for t in tasks:
            delete_task(self.project_root, feature_id, t.id)
        # Remove feature admin dir
        admin_dir = self.project_root / "pct-admin" / "active-features" / feature_id
        if admin_dir.exists():
            shutil.rmtree(admin_dir)
        return True

    def suspend_feature(self, feature_id: str) -> Feature | None:
        return self.update_feature(feature_id, FeatureUpdate(stage=FeatureStage.suspended))

    def resume_feature(self, feature_id: str) -> Feature | None:
        return self.update_feature(feature_id, FeatureUpdate(stage=FeatureStage.active))

    # ── Task CRUD ──

    def create_task(self, feature_id: str, req: TaskCreate) -> Task:
        stages = self._stage_ids()
        first_stage = stages[0] if stages else "refine-spec"

        task = Task(
            id=req.id,
            title=req.title,
            feature_id=feature_id,
            current_stage_id=first_stage,
            artifact_type_id=req.artifact_type_id,
            blocked_by=req.blocked_by,
            cross_refs=req.cross_refs,
        )

        # Validate DAG if there are blocked_by refs
        if task.blocked_by:
            self._validate_dag_with_task(task)

        save_task(self.project_root, task, body=f"# {req.title}\n\n## Spec\n\n## Acceptance Criteria\n")
        return task

    def get_task(self, feature_id: str, task_id: str) -> Task | None:
        return load_task(self.project_root, feature_id, task_id)

    def update_task(self, feature_id: str, task_id: str, req: TaskUpdate) -> Task | None:
        task = load_task(self.project_root, feature_id, task_id)
        if task is None:
            return None
        if req.title is not None:
            task.title = req.title
        if req.artifact_type_id is not None:
            task.artifact_type_id = req.artifact_type_id
        if req.blocked_by is not None:
            task.blocked_by = req.blocked_by
        if req.cross_refs is not None:
            task.cross_refs = req.cross_refs

        if req.blocked_by is not None:
            self._validate_dag_with_task(task)

        task.updated_at = datetime.now(UTC)
        save_task(self.project_root, task)
        return task

    def delete_task_by_id(self, feature_id: str, task_id: str) -> bool:
        return delete_task(self.project_root, feature_id, task_id)

    # ── Task Movement ──

    def move_task(self, feature_id: str, task_id: str, req: TaskMove) -> Task | None:
        task = load_task(self.project_root, feature_id, task_id)
        if task is None:
            return None

        done_stage = self._done_stage_id()

        # Check if task is blocked (unless bypassing)
        if not req.bypass and task.blocked_by:
            is_blocked = self._check_blocked(task)
            if is_blocked:
                return None  # Blocked — cannot move without bypass

        if req.bypass and task.blocked_by:
            task.is_bypassed = True

        task.current_stage_id = req.target_stage_id
        task.execution_status = ExecutionStatus.idle
        task.updated_at = datetime.now(UTC)

        save_task(self.project_root, task)

        # Check if all tasks in feature are done → trigger integration test
        if req.target_stage_id == done_stage:
            self._check_feature_completion(feature_id)

        return task


    # ── PERT Chart ──

    def get_feature_pert(self, feature_id: str) -> PertData:
        """Load tasks for a feature and build PERT data."""
        feature = load_feature(self.project_root, feature_id)
        if feature is None:
            raise ValueError(f"Feature not found: {feature_id}")
        tasks = list_tasks(self.project_root, feature_id)
        done_stage = self._done_stage_id()
        return build_pert_data(tasks, feature_id=feature_id, done_stage=done_stage)

    def get_project_pert(self) -> PertData:
        """Load all active feature tasks and build PERT data."""
        features = list_features(self.project_root)
        all_tasks: list[Task] = []
        for f in features:
            if f.stage in (FeatureStage.active, FeatureStage.planning, FeatureStage.integration_test):
                tasks = list_tasks(self.project_root, f.id)
                all_tasks.extend(tasks)
        done_stage = self._done_stage_id()
        return build_pert_data(all_tasks, done_stage=done_stage)

    # ── Helpers ──

    def _check_blocked(self, task: Task) -> bool:
        """Check if any blocked_by dependency is not at Done stage."""
        done_stage = self._done_stage_id()
        for dep_link in task.blocked_by:
            feat_id, dep_task_id = parse_wikilink(dep_link)
            if dep_task_id:
                dep_task = load_task(self.project_root, feat_id, dep_task_id)
                if dep_task is None or dep_task.current_stage_id != done_stage:
                    return True
        return False

    def _check_feature_completion(self, feature_id: str) -> None:
        """If all tasks are at Done, transition feature to integration_test."""
        done_stage = self._done_stage_id()
        tasks = list_tasks(self.project_root, feature_id)
        if not tasks:
            return
        all_done = all(t.current_stage_id == done_stage for t in tasks)
        if all_done:
            feature = load_feature(self.project_root, feature_id)
            if feature and feature.stage == FeatureStage.active:
                feature.stage = FeatureStage.integration_test
                feature.updated_at = datetime.now(UTC)
                save_feature_metadata(self.project_root, feature)

    def _validate_dag_with_task(self, task: Task) -> None:
        """Validate DAG including the given task's blocked_by."""
        # Build full graph from all features
        all_tasks: dict[str, list[str]] = {}
        features = list_features(self.project_root)
        for f in features:
            tasks = list_tasks(self.project_root, f.id)
            for t in tasks:
                key = f"{t.feature_id}#{t.id}"
                all_tasks[key] = t.blocked_by

        # Override/add the task being validated
        key = f"{task.feature_id}#{task.id}"
        all_tasks[key] = task.blocked_by

        validate_dag(all_tasks)

"""Context builder: resolves cross-references, wikilinks, and RAG context for chat."""

from __future__ import annotations

import re

from loguru import logger


def expand_template(template: str, variables: dict[str, str]) -> str:
    """Expand {{variable}} placeholders. Missing variables left as-is."""

    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        return variables.get(key, match.group(0))

    return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, template)


def resolve_task_context(session_id: str) -> tuple[str, str | None, str | None]:
    """Resolve cross-reference context for a task chat session.

    Parses the session ID (``task-{featureId}-{taskId}``), loads the task,
    collects referenced artifacts from explicit ``cross_refs`` entries
    and ``[[wikilinks]]`` found in the task body and artifact content.

    Returns ``(cross_ref_context_text, artifact_type_prompt, stage_prompt)``
    """
    try:
        from pct.board import service as board_service
        from pct.board.wikilinks import extract_wikilinks, resolve_wikilinks
    except ImportError:
        return ("", None, None)

    # Parse session ID: "{featureId}--{taskId}"
    if "--" not in session_id:
        return ("", None, None)

    parts = session_id.split("--", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return ("", None, None)

    feature_id, task_id = parts

    try:
        task = board_service.get_task(feature_id, task_id)
    except Exception:
        return ("", None, None)
    if task is None:
        return ("", None, None)

    # Artifact type prompt
    artifact_type_prompt = None
    try:
        from pct.board.artifact_types import get_artifact_type_prompt

        artifact_type_prompt = get_artifact_type_prompt(task.artifact_type) or None
    except (ImportError, AttributeError):
        pass

    # Collect referenced task IDs (deduped) from multiple sources
    ref_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add_ref(fid: str, tid: str) -> None:
        key = (fid, tid)
        if key not in seen:
            ref_pairs.append(key)
            seen.add(key)

    # 1. Explicit cross_refs
    for ref in getattr(task, "cross_refs", []):
        if ":" in ref:
            fid, tid = ref.split(":", 1)
            _add_ref(fid, tid)

    # 2. Wikilinks from task body + artifact content
    texts_to_scan: list[str] = []
    if getattr(task, "body", None):
        texts_to_scan.append(task.body)

    artifact_content = ""
    try:
        artifact_data = board_service.read_artifact(feature_id, task_id)
        if artifact_data.get("exists") and artifact_data.get("content"):
            artifact_content = artifact_data["content"]
            texts_to_scan.append(artifact_content)
    except Exception:
        pass

    if texts_to_scan:
        all_links: list[str] = []
        for text in texts_to_scan:
            all_links.extend(extract_wikilinks(text))

        if all_links:
            try:
                features = board_service.list_features()
                resolved = resolve_wikilinks(all_links, features)
                for fid, tid in resolved:
                    _add_ref(fid, tid)
            except Exception:
                pass

    # Build context text from all referenced artifacts
    sections: list[str] = []
    for fid, tid in ref_pairs:
        try:
            ref_task = board_service.get_task(fid, tid)
            if ref_task is None:
                continue
            ref_artifact = board_service.read_artifact(fid, tid)
            content = ref_artifact.get("content", "")
            if not content:
                continue
            sections.append(
                f"--- Referenced: {ref_task.title} ({fid}/{tid}) ---\n{content}"
            )
        except Exception:
            continue

    cross_ref_text = ""
    if sections:
        cross_ref_text = (
            "## Cross-Reference Context\n"
            "The following are referenced world artifacts relevant to this task:\n\n"
            + "\n\n".join(sections)
        )

    # Expand stage prompt template
    stage_prompt = _expand_stage_prompt(
        task=task,
        feature_id=feature_id,
        artifact_content=artifact_content,
        cross_ref_text=cross_ref_text,
    )

    return (cross_ref_text, artifact_type_prompt, stage_prompt)


def _expand_stage_prompt(
    *,
    task,
    feature_id: str,
    artifact_content: str,
    cross_ref_text: str,
) -> str | None:
    """Look up the stage prompt_template for the task's status and expand variables."""
    try:
        from pct.settings import service as settings_service

        stages = settings_service.get_workflow_stages()
    except (ImportError, AttributeError):
        return None

    stage_cfg = None
    current_stage = getattr(task, "current_stage_id", getattr(task, "status", None))
    for s in stages:
        stage_id = getattr(s, "stage", getattr(s, "id", None))
        if stage_id == current_stage:
            stage_cfg = s
            break

    if stage_cfg is None or not getattr(stage_cfg, "prompt_template", None):
        return None

    # Resolve feature title
    feature_title = ""
    try:
        from pct.board import service as board_service

        feature = board_service.get_feature(feature_id)
        if feature:
            feature_title = feature.title
    except Exception:
        pass

    template = stage_cfg.prompt_template
    template = template.replace("{{artifact}}", artifact_content or "(no artifact yet)")
    template = template.replace("{{task_title}}", getattr(task, "title", "") or "")
    template = template.replace("{{feature_title}}", feature_title)
    template = template.replace("{{cross_refs}}", cross_ref_text or "(no cross-references)")

    # Expand user-defined template variables
    try:
        for tv in settings_service.get_template_variables():
            template = template.replace("{{" + tv.key + "}}", tv.value)
    except (ImportError, AttributeError):
        pass

    return template


def rag_search_context(project_id: str, query: str, max_results: int = 5) -> str:
    """Perform RAG semantic search over indexed artifacts.

    Returns formatted results or empty string if RAG is unavailable.
    """
    if not project_id or not query.strip():
        return ""

    try:
        from pct.rag.indexer import _get_db, _get_model
    except ImportError:
        return ""

    try:
        model = _get_model()
        db = _get_db(project_id)

        available = db.list_tables()
        if "artifacts" not in available:
            return ""

        vector = model.encode(query[:8192]).tolist()
        table = db.open_table("artifacts")
        results = table.search(vector).limit(max_results).to_list()

        if not results:
            return ""

        sections: list[str] = []
        for r in results:
            path = r.get("path", "unknown")
            text = r.get("text", "")
            snippet = text[:500] + "..." if len(text) > 500 else text
            sections.append(f"[{path}]\n{snippet}")

        return (
            "## World Knowledge (RAG)\n"
            "Potentially relevant artifacts from the project knowledge base:\n\n"
            + "\n\n".join(sections)
        )
    except Exception:
        logger.opt(exception=True).debug("RAG search failed")
        return ""

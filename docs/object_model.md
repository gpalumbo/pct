# PCT — Object Model v0.1 (Draft)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Conventions](#2-conventions)
3. [Enumerations](#3-enumerations)
4. [Core Entities](#4-core-entities)
   - [Project](#41-project)
   - [SmtpConfig](#42-smtpconfig)
   - [Feature](#43-feature)
   - [Task](#44-task)
   - [ErrorDetails](#45-errordetails)
5. [Agents & Models](#5-agents--models)
   - [Agent](#51-agent)
   - [ModelRegistryEntry](#52-modelregistryentry)
   - [LoRARegistryEntry](#53-loraregistryentry)
   - [LoRAVersion](#54-loraversion)
6. [Workflow & Configuration](#6-workflow--configuration)
   - [WorkflowStage](#61-workflowstage)
   - [ArtifactType](#62-artifacttype)
   - [TemplateVariable](#63-templatevariable)
   - [UserProfile](#64-userprofile)
7. [Chat & Context](#7-chat--context)
   - [TaskStageContext](#71-taskstagecontext)
   - [ChatMessage](#72-chatmessage)
   - [ContextSnapshot](#73-contextsnapshot)
8. [Training Pipeline (F7)](#8-training-pipeline-f7)
   - [TrainingFlag](#81-trainingflag)
   - [Dataset](#82-dataset)
   - [TrainingJob](#83-trainingjob)
   - [HyperParameters](#84-hyperparameters)
   - [TrainingProgress](#85-trainingprogress)
   - [EvaluationSession](#86-evaluationsession)
   - [EvalPrompt](#87-evalprompt)
   - [PromptTemplate](#88-prompttemplate)
   - [PromptTemplateVersion](#89-prompttemplateversion)
9. [Image Generation (F11)](#9-image-generation-f11)
   - [ImageSession](#91-imagesession)
   - [ImageRound](#92-imageround)
   - [GeneratedImage](#93-generatedimage)
10. [Notifications (F13)](#10-notifications-f13)
    - [NotificationEvent](#101-notificationevent)
11. [Relationships](#11-relationships)
12. [State Machines](#12-state-machines)
    - [Feature Lifecycle](#121-feature-lifecycle)
    - [Task Workflow Progression](#122-task-workflow-progression)
    - [Task Execution Status](#123-task-execution-status)
    - [Training Job Lifecycle](#124-training-job-lifecycle)
    - [HuggingFace Model Download](#125-huggingface-model-download)

---

## 1. Overview

This document defines the domain entities, enumerations, relationships, and state machines for PCT. It serves as the canonical reference for **what data exists and how it relates**. Implementation details (storage formats, API design, framework choices) belong in the technical specification.

---

## 2. Conventions

- **IDs** — kebab-case slugs with optional numeric prefixes for ordering (e.g., `f1-core-server`, `define-data-models`). Entity IDs are their slugs.
- **Timestamps** — ISO 8601 UTC
- **WikiLinks** — `[[feature_id]]` references a feature; `[[feature_id#task_id]]` references a task. Mirrors the `work/` directory structure.
- **Scope** — Model Registry and LoRA Registry are **global** (shared across projects). All other entities are **project-scoped**.

**Artifact directory structure** (defined by product spec Artifact Strategy):

```
work/
├── INDEX.md                              # Auto-generated master project index (includes Ideas List)
├── {feature_id}/
│   ├── {feature_id}.md                   # Feature document (writing) or spec (code)
│   ├── implementation_plan.md            # Code projects: tech spec / build plan
│   └── {task_id}/
│       ├── main.md                       # Primary text artifact
│       ├── images/                       # Generated images
│       │   └── session.json              # Image generation metadata
│       └── ...                           # Auxiliary files (drafts, mermaid, PDFs, etc.)
src/                                      # Code projects: shared source code
```

---

## 3. Enumerations

### FeatureStage

Lifecycle stage of a feature (swimlane).

| Value | Description |
|-------|-------------|
| `planning` | Feature created with a Refine Feature task; spec being refined |
| `active` | Tasks flowing through workflow; swimlane shows progress |
| `suspended` | Auto-execution paused; user can still interact manually |
| `integration_test` | All tasks done; feature-level verification running |
| `complete` | Passed integration testing; moved to completed archive |

### ExecutionStatus

Current execution state of a task within its workflow stage.

| Value | Description |
|-------|-------------|
| `idle` | Waiting for user action or auto-run trigger |
| `queued` | Ready for auto-run; waiting for a concurrency slot |
| `running` | Agent currently executing |
| `error` | Agent execution failed; requires user attention |

### AgentType

The kind of executor an agent represents.

| Value | Description |
|-------|-------------|
| `llm` | AI model with prompt template |
| `user` | Human performs the work |
| `tool` | Custom tool or script (future) |
| `image_gen` | Diffusion model for image generation |

### ProviderType

How a model is hosted or accessed. Lives on ModelRegistryEntry; agents inherit from their linked model.

| Value | Description |
|-------|-------------|
| `remote_api` | Cloud API endpoint (e.g., Claude, GPT) |
| `local` | Model weights on local disk |
| `huggingface` | HuggingFace Hub model (downloaded on demand) |
| `user` | Sentinel for User agents — no model backend |

A built-in "User" ModelRegistryEntry with `provider_type: user` exists so that User agents always have a valid model reference.

### DownloadStatus

Download state for HuggingFace models.

| Value | Description |
|-------|-------------|
| `pending` | Not yet downloaded |
| `downloading` | Download in progress |
| `ready` | Downloaded and available |
| `error` | Download failed |

### MessageRole

| Value | Description |
|-------|-------------|
| `user` | User message |
| `assistant` | Agent/model response |
| `system` | System-injected message |

### FlagType

Sentiment of a training data flag.

| Value | Description |
|-------|-------------|
| `positive` | Good response (thumbs up) |
| `negative` | Bad response (thumbs down) |

### AnnotationCategory

Quick category tag for flagged training data.

| Value |
|-------|
| `style` |
| `accuracy` |
| `completeness` |
| `format` |
| `instruction_following` |
| `other` |

### CurationStatus

Progress of a training example through the curation pipeline.

| Value | Description |
|-------|-------------|
| `raw` | Freshly flagged, unedited |
| `curated` | User has reviewed and edited |
| `in_dataset` | Added to at least one named dataset |

### TrainingMethod

LoRA fine-tuning approach.

| Value | Description |
|-------|-------------|
| `sft` | Supervised fine-tuning (positive examples only) |
| `kto` | Kahneman-Tversky Optimization (handles both positive and negative) |

### TrainingJobStatus

| Value | Description |
|-------|-------------|
| `pending` | Configured, not yet started |
| `running` | Training in progress |
| `completed` | Training finished successfully |
| `failed` | Training failed |
| `cancelled` | Cancelled by user |

### LoRASaveTarget

Where to persist a trained LoRA.

| Value | Description |
|-------|-------------|
| `project_local` | Saved to project directory only |
| `global` | Registered in global LoRA registry |

### ImpactSeverity

Severity level of an impact analysis finding.

| Value | Description |
|-------|-------------|
| `contradicted` | Spec directly conflicts with task output/spec |
| `dependency_conflict` | `blocked_by` targets deleted/moved task or creates indefinite wait |
| `possibly_affected` | Related changes that may need review |
| `unchanged` | Confirmed consistent |

### ImpactAction

User response to an impact analysis finding.

| Value | Description |
|-------|-------------|
| `restart` | Send task back to Refine Spec with updated context |
| `flag` | Visual indicator; task continues in current stage |
| `dismiss` | No action; finding acknowledged |

### NotificationState

Notification state for task cards. UI maps these to visual treatments (colors, icons, etc.).

| Value | Meaning | Priority |
|-------|---------|----------|
| `attention` | Needs immediate attention (error, failure, merge conflict) | Highest |
| `warning` | Consistency concern (impact/continuity finding) | Medium |
| `ready` | Ready for user interaction | Lowest |

### NotificationEventType

| Value | Description |
|-------|-------------|
| `task_waiting` | Task waiting for user action |
| `agent_failure` | Agent execution failed |
| `agent_assistance` | Agent explicitly requested human help |
| `merge_conflict` | Merge conflict detected |
| `consistency_finding` | Impact/continuity analysis found issue |
| `dependency_unblocked` | Task unblocked and waiting at user stage |
| `integration_test_complete` | Feature integration test finished |
| `training_job_complete` | LoRA training job finished |

### EvalVerdict

Outcome of a LoRA evaluation session.

| Value | Description |
|-------|-------------|
| `accept` | LoRA accepted for use |
| `reject` | LoRA rejected and deleted |
| `need_more_data` | Inconclusive; more training data needed |

---

## 4. Core Entities

### 4.1 Project

Top-level container. One PCT instance per project.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug identifier (e.g., `pct`) |
| `name` | string | Display name |
| `project_type` | string | Template type used at creation (read-only) |
| `directory` | string | Root directory path |
| `default_agent_id` | Agent ref | Fallback agent when no stage agent is configured |
| `planning_agent_id` | Agent ref | Agent for the Planning Window |
| `context_manager_agent_id` | Agent ref? | Optional agent for context compression (F4) |
| `context_manager_prompt` | string? | Default prompt for context summarization |
| `max_remote_agents` | integer | Max parallel remote API agents (default: 2) |
| `max_local_agents` | integer | Max parallel local GPU agents (default: 1) |
| `notification_email` | string? | Product-level email for system alerts |
| `smtp_config` | SmtpConfig? | SMTP settings for email delivery |
| `font_size` | integer | UI font size preference (10–20px, default: 14) |
| `features` | Feature[] | Ordered list (order = priority) |
| `workflow_stages` | WorkflowStage[] | Ordered workflow stage definitions |
| `agents` | Agent[] | Project-scoped agent definitions |
| `artifact_types` | ArtifactType[] | Project-scoped artifact type definitions |
| `users` | UserProfile[] | Registered user profiles |
| `template_variables` | TemplateVariable[] | Custom variables for stage prompt templates |
| `prompt_templates` | PromptTemplate[] | Versioned prompt template definitions |
| `planning_messages` | ChatMessage[] | Planning Window chat history |
| `planning_agent_selection` | Agent ref? | Sticky agent selection for planning chat |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

**Ideas** are maintained as text entries in `work/INDEX.md` (the Planning Window artifact). They are not domain objects — the user creates features from ideas manually or via chat.

### 4.2 SmtpConfig

Nested configuration for email delivery.

| Field | Type | Description |
|-------|------|-------------|
| `server` | string | SMTP server hostname |
| `port` | integer | SMTP port |
| `username` | string | Auth username |
| `password` | string | Auth password or app key |
| `tls` | boolean | Enable TLS |

### 4.3 Feature

A major deliverable represented as a Kanban swimlane.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug, unique within project (e.g., `f1-core-server`) |
| `title` | string | Display name |
| `stage` | FeatureStage | Current lifecycle stage |
| `spec_path` | string | Path to feature specification document |
| `worktree_path` | string? | Path to git worktree (set during execution, cleared on cleanup) |
| `branch` | string? | Feature branch name (e.g., `feature/f1-core-server`) |
| `tasks` | Task[] | Tasks belonging to this feature |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

**Directory:** `work/{id}/`

**Refine Feature task:** On creation, every feature auto-generates a "Refine Feature" task at the first workflow stage. The planning agent proposes task breakdowns and dependency graphs through this task. When the Refine Feature task completes, the feature transitions from `planning` to `active`.

### 4.4 Task

A single unit of work within a feature. Tasks flow through workflow stages.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug, unique within feature (e.g., `define-data-models`) |
| `title` | string | Display name |
| `feature_id` | Feature ref | Parent feature |
| `current_stage_id` | WorkflowStage ref | Current workflow stage |
| `artifact_type_id` | ArtifactType ref? | Artifact categorization |
| `blocked_by` | WikiLink[] | Hard-blocking deps: `[[feature_id#task_id]]` |
| `cross_refs` | WikiLink[] | Soft/informational refs: `[[feature_id#task_id]]` |
| `execution_status` | ExecutionStatus | Current execution state within the stage |
| `is_bypassed` | boolean | User bypassed unmet dependencies (default: false) |
| `consistency_flag` | ImpactSeverity? | Set by impact/continuity analysis; null when clear |
| `error_details` | ErrorDetails? | Populated when `execution_status` is `error` |
| `stage_contexts` | map\<stage_id, TaskStageContext\> | Per-stage chat history and metadata |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

**Directory:** `work/{feature_id}/{id}/`

**Computed properties:**
- `is_blocked` — true when any `blocked_by` entry references a task not yet at Done stage
- `notification_state` — `NotificationState?` derived from execution_status, consistency_flag, and assigned agent type: attention > warning > ready > `null` (no notification)

**Validation:**
- `blocked_by` graph must be acyclic (DAG enforced on save; cycles rejected with error naming the offending path)
- Both `blocked_by` and `cross_refs` support within-feature and cross-feature references
- Any agent can create new tasks during execution; new tasks always enter at the first workflow stage

### 4.5 ErrorDetails

Captured when an agent execution fails.

| Field | Type | Description |
|-------|------|-------------|
| `error_type` | string | Category (e.g., `api_error`, `timeout`, `oom`) |
| `message` | string | Error message |
| `partial_output` | string? | Any output produced before failure |
| `occurred_at` | timestamp | |

---

## 5. Agents & Models

### 5.1 Agent

A named, reusable executor configuration. Project-scoped. Provider information is inherited from the linked model.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug, unique within project |
| `name` | string | Display name |
| `agent_type` | AgentType | Kind of executor (llm, user, tool, image_gen) |
| `model_id` | ModelRegistryEntry ref | Base model (User agents link to the built-in "User" model) |
| `lora_id` | LoRARegistryEntry ref? | Optional LoRA adapter |
| `prompt_template` | string? | Agent prompt / system instructions |
| `temperature` | float? | Override model default |
| `context_length_override` | integer? | Override model default context length |
| `cli_command` | string? | Command for remote API provider |
| `linked_user_id` | UserProfile ref? | For User agents: linked registered user |
| `notify_on_waiting` | boolean | For User agents: email on task assignment (default: false) |

**Constraints:**
- `lora_id` must reference a LoRA compatible with `model_id` (matching `base_model_id`)
- `linked_user_id` and `notify_on_waiting` apply only when `agent_type` is `user`
- `notify_on_waiting` requires the linked user to have an email and SMTP to be configured
- Provider type is resolved via `model_id` → ModelRegistryEntry.provider_type

### 5.2 ModelRegistryEntry

A model available for use. **Global** — shared across all projects.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `provider_type` | ProviderType | How the model is sourced |
| `model_identifier` | string | Provider-specific ID (file path, API model name, HF repo) |
| `context_length` | integer | Max context window (0 = use model default) |
| `api_base_url` | string? | For remote API models |
| `file_path` | string? | For local/HuggingFace models |
| `download_status` | DownloadStatus? | For HuggingFace models only |

**Built-in entry:** A "User" model with `provider_type: user` exists by default. It has no model backend and serves as the model reference for User-type agents.

### 5.3 LoRARegistryEntry

A LoRA adapter available for use. **Global** — shared across all projects.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `base_model_id` | ModelRegistryEntry ref | Compatible base model |
| `description` | string | Purpose / training notes |
| `versions` | LoRAVersion[] | Version history |
| `active_version` | integer | Currently active version number |

### 5.4 LoRAVersion

A single version of a LoRA adapter. Supports rollback to previous versions.

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Sequential version number |
| `file_path` | string | Path to adapter weights |
| `training_job_id` | TrainingJob ref? | Job that produced this version |
| `created_at` | timestamp | |

---

## 6. Workflow & Configuration

### 6.1 WorkflowStage

A column on the Kanban board. Ordered within a project. Templates select a subset from the built-in catalog.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug identifier (e.g., `refine-spec`, `implement`) |
| `label` | string | Display name |
| `enabled` | boolean | Whether this stage is active for the project |
| `agent_id` | Agent ref? | Default executor for tasks at this stage |
| `prompt_template` | string? | Per-stage prompt injected into agent context |
| `auto_run` | boolean | Auto-execute agent when task enters this stage (default: false) |
| `sort_order` | integer | Position in the workflow |

**Built-in stage catalog** (templates select a subset):

| Stage ID | Label | Typical Use |
|----------|-------|-------------|
| `refine-spec` | Refine Spec | Clarify requirements, produce task spec |
| `implement` | Implement | Execute the work |
| `feature-test` | Feature Test | Run tests scoped to task/feature |
| `code-review` | Code Review | Another agent reviews the work |
| `user-approval` | User Approval | Human reviews and approves/rejects |
| `merge` | Merge | Merge task branch into feature branch |
| `full-test` | Full Test Suite | Run complete project tests post-merge |
| `refactoring-check` | Refactoring Check | Scan for refactoring opportunities |
| `push` | Push | Push to remote |
| `done` | Done | Terminal — task complete and archived |
| `concept` | Concept | Brainstorm core concept (Writing) |
| `outline` | Outline | Structure and outline (Writing) |
| `draft` | Draft | Write or expand draft (Writing) |
| `revise` | Revise | Review for quality and consistency (Writing) |
| `polish` | Polish | Final grammar, prose, consistency pass (Writing) |

### 6.2 ArtifactType

Categorization for task work products. Project-scoped.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug identifier |
| `label` | string | Display name |
| `template_hint` | string? | Instructional text injected into agent system prompt for tasks of this type |
| `color` | string? | Color for the task card indicator dot |

**Built-in artifact types** (Writing template):

| ID | Label |
|----|-------|
| `timeline` | Timeline & History |
| `location` | Location |
| `character` | Character |
| `faction` | Faction / Organization |
| `magic-system` | Magic & Religion |
| `technology` | Technology |
| `item` | Item / Artifact |
| `story-arc` | Story Arc |
| `chapter` | Chapter |
| `text` | Text (generic, used by Coding template) |

### 6.3 TemplateVariable

User-defined variable for stage prompt template substitution.

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Slug key (auto-slugified, lowercase alphanumeric) |
| `description` | string | What this variable represents |
| `value` | string | Substitution value |

**Built-in variables** (always available, read-only):

| Variable | Content |
|----------|---------|
| `{{artifact}}` | Full artifact content |
| `{{artifact_work_dir}}` | Task work directory path (`work/{feature_id}/{task_id}/`) |
| `{{artifact_file_path}}` | Feature document file path (`work/{feature_id}/{feature_id}.md`) |
| `{{task_title}}` | Task display name |
| `{{feature_title}}` | Feature display name |
| `{{blocked_by}}` | Upstream dependency artifact content |
| `{{cross_refs}}` | Cross-reference context from soft-linked tasks |

### 6.4 UserProfile

A registered user for notification routing. Project-scoped.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug, unique within project |
| `display_name` | string | Identifier shown in dropdowns and notifications |
| `email` | string? | Email for notifications (validated on save) |

---

## 7. Chat & Context

### 7.1 TaskStageContext

The chat session for a specific task at a specific workflow stage. Stored independently per (task, stage) pair.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | Task ref | |
| `stage_id` | WorkflowStage ref | |
| `messages` | ChatMessage[] | Conversation history at this stage |
| `last_agent_id` | Agent ref? | Sticky agent selection for this context |

**Stage transition rules:**
- **Advance** — context resets for the new stage; the artifact is the handoff mechanism
- **Send back** — previous stage's context is restored in full (non-destructive)
- **Carry-forward override** — optional flag on approval to include current stage's conversation in the next stage's context (rare)

### 7.2 ChatMessage

A single message in a chat session (planning or task-stage).

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique within session |
| `role` | MessageRole | user / assistant / system |
| `content` | string | Message text |
| `included` | boolean | Whether included in context sent to agent (default: true) |
| `created_at` | timestamp | |

### 7.3 ContextSnapshot

The full assembled context captured when a user flags a training example. Preserves exactly what the model saw at flag time.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `project_spec` | string | Project specification text at capture time |
| `feature_spec` | string | Feature specification text at capture time |
| `task_spec` | string | Task specification text at capture time |
| `rag_results` | string | RAG-injected context |
| `retry_history` | string | Prior attempts and feedback |
| `chat_history` | ChatMessage[] | Messages included in context |
| `captured_at` | timestamp | |

---

## 8. Training Pipeline (F7)

### 8.1 TrainingFlag

A user-flagged message pair from a chat interaction.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `session_ref` | string | Source: task_id + stage_id, or planning session |
| `message_range` | integer[] | Indices of the user turn + assistant response |
| `context_snapshot_id` | ContextSnapshot ref | What the model saw |
| `agent_id` | Agent ref | Agent that produced the response |
| `model_id` | ModelRegistryEntry ref | Model used |
| `flag_type` | FlagType | Positive or negative |
| `annotation_category` | AnnotationCategory | Quick category |
| `note` | string? | Free-text explanation |
| `curation_status` | CurationStatus | Pipeline progress |
| `edited_response` | string? | User's curated ideal response |
| `context_sections_included` | string[]? | Which context sections to include in training |
| `created_at` | timestamp | |

### 8.2 Dataset

A named collection of curated training examples.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name (e.g., "code-style-preferences") |
| `description` | string? | Purpose of this dataset |
| `entries` | TrainingFlag ref[] | Ordered list of included flags |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

**Computed properties:**
- `example_count`, `positive_count`, `negative_count`
- `avg_token_length` — average across entries

### 8.3 TrainingJob

A LoRA fine-tuning run.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Name for the output LoRA |
| `base_model_id` | ModelRegistryEntry ref | Target base model (local/HF only) |
| `training_method` | TrainingMethod | SFT or KTO |
| `dataset_ids` | Dataset ref[] | Source datasets |
| `target_lora_id` | LoRARegistryEntry ref? | If updating existing (null = create new) |
| `status` | TrainingJobStatus | Current state |
| `save_target` | LoRASaveTarget | Where to save output |
| `hyperparameters` | HyperParameters | Training configuration |
| `progress` | TrainingProgress? | Live metrics (when running/completed) |
| `error_message` | string? | If failed |
| `started_at` | timestamp? | |
| `completed_at` | timestamp? | |

**Constraint:** `base_model_id` must reference a model with `provider_type` of `local` or `huggingface` (remote API models cannot be LoRA-trained).

### 8.4 HyperParameters

Training configuration values.

| Field | Type | Default |
|-------|------|---------|
| `lora_rank` | integer | 16 |
| `lora_alpha` | integer | 32 |
| `learning_rate` | float | 2e-4 |
| `epochs` | integer | 3 |
| `batch_size` | integer | 4 |
| `max_sequence_length` | integer | (from model context) |

### 8.5 TrainingProgress

Live metrics for a running or completed training job.

| Field | Type | Description |
|-------|------|-------------|
| `current_epoch` | integer | |
| `total_epochs` | integer | |
| `loss` | float | Current loss value |
| `loss_history` | float[] | Loss values per step (for chart) |
| `elapsed_seconds` | integer | |
| `eta_seconds` | integer? | Estimated time remaining |

### 8.6 EvaluationSession

An A/B comparison between base model and base+LoRA.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `lora_id` | LoRARegistryEntry ref | LoRA being evaluated |
| `base_model_id` | ModelRegistryEntry ref | Base model |
| `blind_mode` | boolean | Whether model labels are hidden |
| `prompts` | EvalPrompt[] | Test prompts with responses |
| `verdict` | EvalVerdict? | Final outcome |
| `created_at` | timestamp | |

### 8.7 EvalPrompt

A single test prompt within an evaluation session.

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | The test input |
| `source_flag_id` | TrainingFlag ref? | Pulled from flagged example (or written fresh) |
| `base_response` | string | Base model response |
| `lora_response` | string | Base+LoRA model response |
| `base_rating` | integer? | User rating for base |
| `lora_rating` | integer? | User rating for LoRA |

### 8.8 PromptTemplate

Versioned agent instructions that evolve over time. Project-scoped.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `versions` | PromptTemplateVersion[] | Version history |
| `active_version` | integer | Currently active version number |

### 8.9 PromptTemplateVersion

A single version of a prompt template.

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Sequential version number |
| `content` | string | Template text |
| `notes` | string? | Change description |
| `created_at` | timestamp | |

---

## 9. Image Generation (F11)

### 9.1 ImageSession

Image generation state for a task. One per task.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | Task ref | Owning task |
| `rounds` | ImageRound[] | Generation rounds in order |
| `accepted_image_id` | GeneratedImage ref? | Selected/accepted final image |

### 9.2 ImageRound

A single round of image generation.

| Field | Type | Description |
|-------|------|-------------|
| `round_number` | integer | Sequential round index |
| `prompt` | string | Generation prompt |
| `negative_prompt` | string? | Exclusion prompt |
| `guidance_scale` | float | Prompt adherence (default: 7.5) |
| `divergence` | float? | img2img variation strength (0.1–0.9; only for rounds after the first) |
| `source_image_id` | GeneratedImage ref? | Source for img2img (null for text-to-image) |
| `images` | GeneratedImage[] | Generated images (typically 4) |

### 9.3 GeneratedImage

A single generated image.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `file_path` | string | Path to image file |
| `seed` | integer | Generation seed |
| `index` | integer | Position in the round (0–3) |
| `created_at` | timestamp | |

---

## 10. Notifications (F13)

### 10.1 NotificationEvent

A notification event surfaced to the user.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `event_type` | NotificationEventType | Kind of event |
| `task_id` | Task ref? | Related task (null for project-level events) |
| `feature_id` | Feature ref? | Related feature |
| `message` | string | Human-readable summary |
| `severity` | NotificationState | Visual priority |
| `acknowledged` | boolean | User has dismissed/addressed (default: false) |
| `email_sent` | boolean | Whether email was dispatched (default: false) |
| `email_target` | string? | Which email address received it |
| `created_at` | timestamp | |

**Email routing:**
- **Product notification email** (Project.notification_email) — agent failures, merge conflicts, integration tests, training jobs
- **Per-user email** (UserProfile.email) — task-waiting notifications when `notify_on_waiting` is enabled on the User agent

---

## 11. Relationships

### Entity Relationship Summary

```
Project
 ├── 1:N Feature (ordered by priority)
 ├── 1:N WorkflowStage (ordered)
 ├── 1:N Agent
 ├── 1:N ArtifactType
 ├── 1:N UserProfile
 ├── 1:N TemplateVariable
 ├── 1:N PromptTemplate
 ├── 1:N NotificationEvent
 ├── 0:1 SmtpConfig
 └── refs → Agent (default_agent, planning_agent, context_manager_agent)

Feature
 ├── 1:N Task
 └── belongs to → Project

Task
 ├── N:N Task (blocked_by — directed, acyclic)
 ├── N:N Task (cross_refs — directed, informational)
 ├── 1:N TaskStageContext (one per visited workflow stage)
 ├── 0:1 ImageSession
 ├── 0:1 ErrorDetails
 ├── refs → WorkflowStage (current_stage)
 ├── refs → ArtifactType
 └── belongs to → Feature

Agent
 ├── refs → ModelRegistryEntry (required — User agents use built-in "User" model)
 ├── refs → LoRARegistryEntry (optional, must match model)
 ├── refs → UserProfile (optional, for User agents)
 └── belongs to → Project

ModelRegistryEntry (GLOBAL)
 └── 1:N LoRARegistryEntry (compatible adapters)

LoRARegistryEntry (GLOBAL)
 ├── 1:N LoRAVersion
 └── refs → ModelRegistryEntry (base model)

TaskStageContext
 ├── 1:N ChatMessage
 └── refs → Agent (last selected)

TrainingFlag
 ├── refs → ContextSnapshot
 ├── refs → Agent
 └── refs → ModelRegistryEntry

Dataset
 └── N:N TrainingFlag (ordered entries)

TrainingJob
 ├── refs → ModelRegistryEntry (base model)
 ├── refs → LoRARegistryEntry (if updating)
 └── refs → Dataset[] (sources)

EvaluationSession
 ├── refs → LoRARegistryEntry
 ├── refs → ModelRegistryEntry
 └── 1:N EvalPrompt

ImageSession
 ├── 1:N ImageRound
 └── belongs to → Task

ImageRound
 └── 1:N GeneratedImage
```

### Key Constraints

1. **Acyclic `blocked_by` graph** — circular dependency detection enforced on save; the directed graph must be a DAG at all times
2. **Cross-feature references** — both `blocked_by` and `cross_refs` can reference tasks in any feature via WikiLinks
3. **LoRA–Model compatibility** — Agent's `lora_id` must reference a LoRA whose `base_model_id` matches the Agent's `model_id`
4. **LoRA training targets local only** — TrainingJob's `base_model_id` must have `provider_type` of `local` or `huggingface`
5. **Notification email requires SMTP** — email notifications silently skipped when SmtpConfig is absent
6. **User agent notifications require linked user with email** — `notify_on_waiting` only functions when linked UserProfile has a valid email and SMTP is configured
7. **Agent provider inherited** — Agent does not store its own provider type; resolved via `model_id` → ModelRegistryEntry.provider_type

---

## 12. State Machines

### 12.1 Feature Lifecycle

```
Planning ──→ Active ──→ Integration Test ──→ Complete
                │              │
                ↓              │
            Suspended ─────→ Active (resume)
```

| From | To | Trigger |
|------|----|---------|
| Planning | Active | Refine Feature task completes |
| Active | Suspended | User toggles suspend on swimlane |
| Active | Integration Test | All tasks reach Done stage |
| Suspended | Active | User toggles resume |
| Integration Test | Complete | Integration test passes |
| Integration Test | Active | Integration test fails (new tasks spawned at first workflow stage) |

**Notes:**
- Suspend can also be applied from Integration Test
- Project-wide suspend applies to all active swimlanes simultaneously
- Resume can be global or per-swimlane

### 12.2 Task Workflow Progression

Tasks advance through the project's ordered workflow stages.

```
[Stage 1] → [Stage 2] → ... → [Stage N-1] → [Done]
    ↑           ↑                    ↑
    └───────────┴── Send Back ───────┘
```

**Rules:**
- **Advance** — on approval, task moves to next enabled stage
- **Send back** — user can return task to any earlier stage; that stage's context is restored
- **Skip** — drag-and-drop to non-adjacent stage shows confirmation listing skipped stages
- **Bypass** — blocked tasks can be manually advanced with user confirmation; logged with badge
- **Auto-run** — when a task enters a stage with `auto_run` enabled and is not blocked, the agent fires automatically
- **Auto-unblock cascade** — when a task reaches Done, PCT re-evaluates all tasks listing it in `blocked_by`; newly unblocked tasks at auto-run stages fire automatically
- **Done** — terminal stage; task is complete and archived

### 12.3 Task Execution Status

```
      ┌──── (user retry) ─────┐
      ↓                        │
    Idle ──→ Queued ──→ Running ──→ Idle (at next stage on success)
                           │
                           └──→ Error
```

| From | To | Trigger |
|------|----|---------|
| Idle | Queued | Auto-run enabled and task enters stage (or unblocks) |
| Queued | Running | Concurrency slot available |
| Running | Idle | Agent completes successfully |
| Running | Error | Agent fails (API error, timeout, OOM, etc.) |
| Error | Idle | User retries or reassigns |

**Note:** Auto-run does not re-trigger on error. The user must manually retry.

### 12.4 Training Job Lifecycle

```
Pending ──→ Running ──→ Completed
               │
               ├──→ Failed
               └──→ Cancelled
```

### 12.5 HuggingFace Model Download

```
Pending ──→ Downloading ──→ Ready
                │
                └──→ Error ──→ (retry) → Downloading
```

Ok I want to build a project contruction tool (PCT) using local LLM models as agent builders.  It will have an initial pllanning chat window, using either local LLMs or a more powerful remote LLM. Once the plan is set, the PCT will ultimatly display todos via a Kanban board.  Different agents will be utilized based on task type and workflow stage of each to do.  Manual/User agent is always an option instead of always using an LLM agent.  There should also be swimlanes of activity, as well as the ability to suspend activity on a swimlane to allow for interrupts like code refactoring or re-definign and re-planning a feature.   Not all tasks will be coding, and not all projects app development. Custom tools for certain tasks will be added (possibly trained requiring a LORA).
Another major feature will be that rejected task completion will result in a negative prompt context and/or negative lora training depending on task/model.  The PCT will have a UI to collect negative _and positve_ task executions and help train or curate agent prompts.

My current thought is to build a server that manages the context and tool execution using llama cpp python and have a react front end that allows session management and interactions.  
Each task type/workflow stage should allow for an specific agent prompt text, a model and a LORA to be configured.  
The project and tasks should allow for continuity in base contexts to be shared across the whole project and multi task feature development.  
If llama is not sufficient to handle local LLMs as well as API usage we need some task abstraction to handle both.  We will need this anyway to handle user tasks.

I kind of want to use GIT and git worktree, allowing tasks to createa a worktree and branch and a stage in the kanban will be the merge.

Since I would wanto to store task results and grading as well as task history I am thinking local file store with a RAG on top .  Open to solutions here.


1. This will be single-user/local-first.  I don't want to lock out multi-user so lets keep an option to turn on Auth, however, it can be single project focused, spinning up a new instace for a new project.  Since new faetures may require a full specification and planning cycle we should plan for multiple tiers of spec and ensuring to-do items are tagged or organized so that an LLM working on a feature doesn't get confused between concurrently developed features.  We can dig deeper if you have more questions.

2. An example of other types of projects , creation of a DnD Campaign world and specific adventures within that world. My thought was individual adventures would be treated like features and user enterd campaign logs like additional context.

2.1 Another example would be creating a slide deck for a new business, or school reaseach project.
3. This is configurable by task or workflow stage.  As part of the kanban workflow, I see [refine spec, implement, feature test, code review(by another agent), user feature approval, merge,(Call to user on merge failures), full test suite, automated refactoring opportunity check (create new tasks), push]

4. See 3.

5. My thought is to utilize ClaudeCode via subscription (command line perhaps) although if we release this into the wild additional interfaces should be supported, but that is not a priority

6. I was thinking user helps curate and the training would be executed via PCT

7. Both.  I was thinking that if the user requested a change, we would rerun the previos context window and prompt but adding the code example as a user says thei is bad,     and gives additional feedback.  But for repeating issues we want to curate the agent templates.

8.  Good question.  PCT agents should work on worktrees etc tthat are part of the the project repo.  PCT curation  should be resuable, so should live elsewhere.  PCT project status could live in the project repo or a parallel repo.  lets refine this later

9. Both.  On the this is how similar things were done and what related features were, having the negative repsones here would be pareticularly helpful. We can surface existing functions that may be useful.  Also think outside of coding tasks, we would want to surface cahracters/NPCs/Locations/factions/descriptions that were created earlier.

10. This would suspend all work.  It means we are rvisting code refactor or feature definition that may invalidate the assumptions of currently running agents.  We would also need a feature to clear state and restart all inflight tasks.

## 7. Resolved Gaps

All gaps identified during initial review have been resolved:

1. ~~**Non-code workflow stages**~~ **[RESOLVED]** — PCT provides workflow templates per project type. Templates vary in which stages are active and what agents do at each stage, but **git is universal** — every project type uses git (branching, worktrees, merge). Non-code projects are expected to produce text-mergeable document formats (LaTeX, RTF, or Markdown). Parallel agent execution within a feature is only supported when the output artifacts are mergeable. Features producing non-mergeable artifacts (images, video, binary formats) must serialize task execution. This is configured as a per-feature setting.

2. ~~**Task dependencies**~~ **[RESOLVED]** — PCT supports explicit task dependencies within a feature. The planning agent proposes an initial dependency graph during task decomposition, and the user can review and edit it. Tasks with unmet dependencies remain blocked in their current column. No runtime auto-inference of dependencies — explicit is simpler and more predictable.

3. ~~**Cross-feature dependencies**~~ **[RESOLVED]** — Cross-feature dependencies are identified at planning time. The planning agent flags cross-feature dependencies when decomposing tasks. At runtime, these are modeled as task-level blocks across swimlanes (e.g., "Task X in Feature B is blocked by Task Y in Feature A"). Tasks with unmet cross-feature dependencies remain blocked. The Kanban UI visually indicates cross-swimlane blocks.

4. ~~**Merge conflict resolution UX**~~ **[RESOLVED]** — Merge conflicts are always resolved externally. PCT does not attempt agent-based conflict resolution or provide a built-in diff/merge UI. When a merge fails, PCT flags the conflict on the task card, notifies the user, and waits for the user to resolve using their own editor and merge tools (VS Code, vim, meld, etc.). The user signals PCT when resolution is complete.

5. ~~**Agent concurrency limits**~~ **[RESOLVED]** — PCT manages a concurrency pool with default limits: max 2 parallel remote API agents, max 1 local GPU agent. Defaults are overridable in the project configuration. A **Project Configuration page** (see F10) provides the UI for managing concurrency limits, workflow stage configuration, and other project-level settings.

6. ~~**Context window management**~~ **[RESOLVED]** — PCT manages context assembly automatically using a tiered strategy: (1) always include project spec, feature spec, and task spec; (2) summarize retry history beyond the latest 2 full attempts; (3) RAG results ranked by relevance, included up to a configurable token budget. A **context inspector** in the task detail panel shows the user exactly what was assembled. The user can **edit the assembled context at any time** — adding, removing, or modifying any section — and retry the agent with the modified context. This is critical for local models with restricted context windows where automatic assembly may include too much.

7. ~~**PCT's own state persistence**~~ **[RESOLVED — see tech_spec.md Section 1: Storage Architecture]** — Fully addressed in the tech spec. PCT uses a hybrid storage model: `.pct/` in the project repo for specs and task definitions, `~/.pct/projects/<project-id>/` for execution artifacts and RAG, and `~/.pct/curation/` for cross-project reusable data (prompt templates, LoRAs, training examples).

8. ~~**Worktree lifecycle for non-code tasks**~~ **[RESOLVED]** — Since git is universal (see Gap #1 resolution), worktrees are always used. Every task gets a branch and worktree regardless of project type. Non-code tasks produce text-mergeable documents (LaTeX, RTF, Markdown) in their worktree, and these flow through the same branch/merge/push pipeline as code tasks.

9. ~~**Multi-tier specification flow**~~ **[RESOLVED]** — Addressed by the Feature Lifecycle (see Core Concepts). The planning agent proposes specs at each level (project → feature → task), and the user can manually create or edit specs at any level. Spec creation and editing happens during the Planning and Suspended feature lifecycle stages. The flow is: planning agent drafts → user reviews/edits → approved spec becomes context for downstream work. The task detail panel (F3) and planning chat (F1) are the UI surfaces for spec editing.

10. ~~**What triggers the initial task breakdown?**~~ **[RESOLVED]** — The planning agent proposes the task breakdown during the feature's Planning lifecycle stage; the user approves before the feature becomes Active. Tasks can be added mid-flight to an active swimlane — by the user manually, or by agents (e.g., the refactoring-check agent spawns new tasks, or integration testing failures generate new tasks). New tasks always enter at the Refine Spec workflow stage.



<project-root>/
  .pct/
    link.json                         # ~/.pct/projects/<project-id>/
    pct.json                          # project config: project ID, workflow stages,
                                      #   agent defaults, auto-advance rules
    project_spec.md                   # project-level specification, includes feature priority
    active-features/                  # features with a defiend spec and swimlane
      001-configuration-feature/
        feature_spec.md               # feature-level specification 
        metadata.json                 # metadata in ap consumable form (depenedencies, swimlane info, worktree, branch, commits)
        tasks/
          001-define-data-models.md    # task definition + current status
          002-design-api-routes.md
          003-setup-scaffold.md
      002-other feature/
        feature_spec.md               # feature-level specification 
        feature_cfg.json              # metadata in ap consumable form (depenedencies, swimlane info)
        tasks/
          001-stuff to do.md    # task definition + current status
    feature_backlog/
      agent-execution-engine.md       # feature specs for backlogged features
      git-integration.md              #   (no tasks/ dir until activated)

~/.pct/
  projects/
    <project-id>/
      link.json                       # {"project_path": "~/projects/myapp"}
      execution/
        active-tasks/
          001-define-data-models/
            attempt-001/
              agent_log.jsonl         # raw LLM messages (streaming transcript)
              output.md               # agent's produced output
              feedback.md             # rejection feedback (if rejected)
              metadata.json           # timestamp, agent, model, duration, tokens, 
            attempt-002/
              ...
            attempt-003/
              ...
        completed-tasks/

        features/
           001-configuration-feature/
      chat_history/
        planning-001.jsonl            # initial project planning session
        planning-002.jsonl            # feature re-planning after swimlane suspend
      rag/
        tasks.lance/                  # LanceDB table: task execution embeddings
        specs.lance/                  # LanceDB table: spec/feature embeddings
      kanban_snapshots/               # periodic snapshots for timeline/history view
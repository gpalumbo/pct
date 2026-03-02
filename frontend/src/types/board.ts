/** Board types — mirrors backend models. */

import type {
  ExecutionStatus,
  FeatureStage,
  ImpactSeverity,
} from './enums';

export interface ErrorDetails {
  error_type: string;
  message: string;
  partial_output?: string | null;
  occurred_at: string;
}

export interface Task {
  id: string;
  title: string;
  feature_id: string;
  current_stage_id: string;
  artifact_type_id?: string | null;
  blocked_by: string[];
  cross_refs: string[];
  execution_status: ExecutionStatus;
  is_bypassed: boolean;
  consistency_flag?: ImpactSeverity | null;
  error_details?: ErrorDetails | null;
  created_at: string;
  updated_at: string;
}

export interface Feature {
  id: string;
  title: string;
  stage: FeatureStage;
  spec_path: string;
  worktree_path?: string | null;
  branch?: string | null;
  tasks: Task[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowStage {
  id: string;
  label: string;
  enabled: boolean;
  agent_id?: string | null;
  prompt_template?: string | null;
  auto_run: boolean;
  sort_order: number;
}

export interface BoardState {
  features: Feature[];
  workflow_stages: WorkflowStage[];
}

export interface FeatureCreate {
  id: string;
  title: string;
  spec_content?: string;
}

export interface TaskCreate {
  id: string;
  title: string;
  artifact_type_id?: string | null;
  blocked_by?: string[];
  cross_refs?: string[];
}

export interface TaskMove {
  target_stage_id: string;
  bypass?: boolean;
}

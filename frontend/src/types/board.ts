// Board domain types mirroring backend models

export type FeatureStage =
  | 'backlog'
  | 'planning'
  | 'active'
  | 'suspended'
  | 'integration-test'
  | 'complete';

export type SerializationMode = 'parallel' | 'serial';

export interface FeatureMetadata {
  lifecycle_stage: FeatureStage;
  serialization_mode: SerializationMode;
  worktree_path: string | null;
  branch: string | null;
  commits: string[];
  feature_dependencies: string[];
  created: string;
  updated: string;
}

export interface Task {
  id: string;
  title: string;
  feature: string;
  status: string;
  agent: string | null;
  branch: string | null;
  depends_on: string[];
  cross_depends_on: string[];
  tags: string[];
  priority: number;
  attempt: number;
  artifact_path: string;
  created: string;
  updated: string;
  body: string;
}

export interface Feature {
  id: string;
  title: string;
  specification: string;
  metadata: FeatureMetadata;
  tasks: Task[];
}

export interface BacklogFeature {
  id: string;
  title: string;
  specification: string;
}

export interface BoardResponse {
  features: Feature[];
  backlog: BacklogFeature[];
  enabled_stages: string[];
}

// Request types

export interface CreateFeatureRequest {
  id: string;
  title: string;
  specification?: string;
  metadata?: Partial<FeatureMetadata> | null;
}

export interface UpdateFeatureMetadataRequest {
  lifecycle_stage?: FeatureStage;
  serialization_mode?: SerializationMode;
  worktree_path?: string | null;
  branch?: string | null;
  commits?: string[];
  feature_dependencies?: string[];
}

export interface CreateTaskRequest {
  title: string;
  status?: string;
  agent?: string | null;
  depends_on?: string[];
  cross_depends_on?: string[];
  tags?: string[];
  priority?: number;
  artifact_path?: string;
  body?: string;
}

export interface UpdateTaskRequest {
  title?: string;
  status?: string;
  agent?: string | null;
  branch?: string | null;
  depends_on?: string[];
  cross_depends_on?: string[];
  tags?: string[];
  priority?: number;
  attempt?: number;
  artifact_path?: string;
  body?: string;
}

export interface MoveTaskRequest {
  new_status: string;
  confirm_skip?: boolean;
}

export interface ReassignTaskRequest {
  src_feature_id: string;
  task_id: string;
  dest_feature_id: string;
  new_status: string;
}

export type TaskStatus =
  | 'refine-spec'
  | 'implement'
  | 'feature-test'
  | 'code-review'
  | 'user-approval'
  | 'merge'
  | 'full-test'
  | 'refactor-check'
  | 'push'
  | 'done';

export const ALL_TASK_STATUSES: TaskStatus[] = [
  'refine-spec',
  'implement',
  'feature-test',
  'code-review',
  'user-approval',
  'merge',
  'full-test',
  'refactor-check',
  'push',
  'done',
];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  'refine-spec': 'Refine Spec',
  'implement': 'Implement',
  'feature-test': 'Feature Test',
  'code-review': 'Code Review',
  'user-approval': 'User Approval',
  'merge': 'Merge',
  'full-test': 'Full Test',
  'refactor-check': 'Refactor Check',
  'push': 'Push',
  'done': 'Done',
};

export type AgentType = 'llm' | 'user' | 'tool';
export type ProviderType = 'remote' | 'local' | 'user';

export interface ModelRegistryEntry {
  id: string;
  provider_type: ProviderType;
  model_id: string;
  context_length: number;
  model_path?: string | null;
  api_base?: string | null;
}

export interface LoRARegistryEntry {
  id: string;
  base_model: string;
  path: string;
  description?: string;
  created?: string | null;
}

export interface AgentConfig {
  id: string;
  agent_type: AgentType;
  provider_type: ProviderType;
  model: string;
  prompt_template?: string | null;
  lora?: string | null;
  cli_command?: string | null;
  context_length?: number | null;
  temperature?: number | null;
}

export interface WorkflowStageConfig {
  stage: TaskStatus;
  enabled: boolean;
  agent?: string | null;
}

export interface ConcurrencyConfig {
  remote_api_limit: number;
  local_gpu_limit: number;
}

export interface ContextConfig {
  token_budget: number;
  context_manager_model: string;
}

export interface ProjectConfig {
  project_id: string;
  project_name: string;
  project_type: string;
  agents: AgentConfig[];
  workflow_stages: WorkflowStageConfig[];
  planning_agent: string;
  default_agent: string;
  auto_advance: boolean;
  concurrency: ConcurrencyConfig;
  context: ContextConfig;
}

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

export interface ArtifactTypeConfig {
  id: string;
  label: string;
  template_hint: string;
}

export interface TemplateVariable {
  key: string;
  description: string;
  value: string;
}

export interface WorkflowStageConfig {
  stage: string;
  label: string;
  enabled: boolean;
  agent?: string | null;
  prompt_template?: string;
}

export interface ConcurrencyConfig {
  remote_api_limit: number;
  local_gpu_limit: number;
}

export interface ProjectConfig {
  project_id: string;
  project_name: string;
  project_type: string;
  project_directory: string;
  agents: AgentConfig[];
  workflow_stages: WorkflowStageConfig[];
  template_variables: TemplateVariable[];
  artifact_types: ArtifactTypeConfig[];
  planning_agent: string;
  default_agent: string;
  auto_advance: boolean;
  concurrency: ConcurrencyConfig;
}

export interface ProjectStatus {
  initialized: boolean;
  project_directory: string;
}

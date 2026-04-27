/** Config types — mirrors backend models. */

import type { AgentType, ProviderType, DownloadStatus } from './enums';

export interface SmtpConfig {
  server: string;
  port: number;
  username: string;
  password: string;
  tls: boolean;
}

export interface Agent {
  id: string;
  name: string;
  agent_type: AgentType;
  model_id: string;
  lora_id?: string | null;
  prompt_template?: string | null;
  temperature?: number | null;
  context_length_override?: number | null;
  cli_command?: string | null;
  linked_user_id?: string | null;
  notify_on_waiting: boolean;

  // Image-gen parameters (only when agent_type === 'image_gen')
  num_inference_steps?: number | null;
  guidance_scale?: number | null;
  negative_prompt?: string | null;
  num_images?: number | null;
  default_draft?: boolean | null;
  // Flux-specific
  max_sequence_length?: number | null;
  true_cfg_scale?: number | null;
}

export interface ModelRegistryEntry {
  id: string;
  name: string;
  provider_type: ProviderType;
  model_identifier: string;
  context_length: number;
  api_base_url?: string | null;
  file_path?: string | null;
  gguf_filename?: string | null;
  download_status?: DownloadStatus | null;
}

export interface HfGgufFile {
  filename: string;
  display_name: string;
  total_size: number;
  shard_count: number;
}

export interface LoRAVersion {
  version: number;
  file_path: string;
  training_job_id?: string | null;
  created_at: string;
}

export interface LoRARegistryEntry {
  id: string;
  name: string;
  base_model_id: string;
  description: string;
  versions: LoRAVersion[];
  active_version: number;
}

export interface ArtifactType {
  id: string;
  label: string;
  template_hint?: string | null;
  color?: string | null;
}

export interface TemplateVariable {
  key: string;
  description: string;
  value: string;
}

export interface UserProfile {
  id: string;
  display_name: string;
  email?: string | null;
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

export interface Project {
  initialized?: boolean;
  id: string;
  name: string;
  project_type: string;
  directory: string;
  default_agent_id: string;
  planning_agent_id: string;
  context_manager_agent_id?: string | null;
  context_manager_prompt?: string | null;
  max_remote_agents: number;
  max_local_agents: number;
  notification_email?: string | null;
  smtp_config?: SmtpConfig | null;
  font_size: number;
  features: unknown[];
  workflow_stages: WorkflowStage[];
  agents: Agent[];
  artifact_types: ArtifactType[];
  users: UserProfile[];
  template_variables: TemplateVariable[];
  prompt_templates: unknown[];
  planning_messages: unknown[];
  planning_agent_selection?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectStatus {
  initialized: boolean;
  project_id?: string | null;
  project_name?: string | null;
}

export interface FileEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

/** PCT enumerations — mirrors backend models/enums.py */

export type FeatureStage = 'planning' | 'active' | 'suspended' | 'integration_test' | 'complete';
export type ExecutionStatus = 'idle' | 'queued' | 'running' | 'error';
export type AgentType = 'llm' | 'user' | 'tool' | 'image_gen';
export type ProviderType = 'remote_api' | 'local' | 'huggingface' | 'user';
export type DownloadStatus = 'pending' | 'downloading' | 'ready' | 'error';
export type MessageRole = 'user' | 'assistant' | 'system';
export type FlagType = 'positive' | 'negative';
export type AnnotationCategory = 'style' | 'accuracy' | 'completeness' | 'format' | 'instruction_following' | 'other';
export type CurationStatus = 'raw' | 'curated' | 'in_dataset';
export type TrainingMethod = 'sft' | 'kto';
export type TrainingJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type LoRASaveTarget = 'project_local' | 'global';
export type ImpactSeverity = 'contradicted' | 'dependency_conflict' | 'possibly_affected' | 'unchanged';
export type ImpactAction = 'restart' | 'flag' | 'dismiss';
export type NotificationState = 'attention' | 'warning' | 'ready';
export type NotificationEventType =
  | 'task_waiting'
  | 'agent_failure'
  | 'agent_assistance'
  | 'merge_conflict'
  | 'consistency_finding'
  | 'dependency_unblocked'
  | 'integration_test_complete'
  | 'training_job_complete';
export type EvalVerdict = 'accept' | 'reject' | 'need_more_data';

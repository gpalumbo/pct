/** Training types — mirrors backend models. */

import type {
  AnnotationCategory,
  CurationStatus,
  FlagType,
} from './enums';

export interface TrainingFlag {
  id: string;
  session_ref: string;
  message_range: number[];
  context_snapshot_id: string;
  agent_id: string;
  model_id: string;
  flag_type: FlagType;
  annotation_category: AnnotationCategory;
  note: string | null;
  curation_status: CurationStatus;
  edited_response: string | null;
  context_sections_included: string[] | null;
  created_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  entries: string[];
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateVersion {
  version: number;
  content: string;
  notes: string | null;
  created_at: string;
}

export interface PromptTemplate {
  id: string;
  name: string;
  versions: PromptTemplateVersion[];
  active_version: number;
}

// Request types

export interface FlagCreate {
  session_ref: string;
  message_index: number;
  flag_type: FlagType;
  annotation_category?: AnnotationCategory;
  note?: string;
}

export interface FlagUpdate {
  annotation_category?: AnnotationCategory;
  note?: string;
  curation_status?: CurationStatus;
  edited_response?: string;
}

export interface DatasetCreate {
  name: string;
  description?: string;
}

export interface DatasetUpdate {
  name?: string;
  description?: string;
  entry_ids?: string[];
}

export interface PromptTemplateCreate {
  name: string;
  content: string;
}

export interface PromptTemplateUpdate {
  content: string;
}

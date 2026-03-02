/** PERT chart types -- mirrors backend board/pert.py models. */

export interface PertNode {
  id: string;
  task_id: string;
  feature_id: string;
  title: string;
  stage_id: string;
  execution_status: string;
  is_blocked: boolean;
  is_completed: boolean;
}

export interface PertEdge {
  source: string;
  target: string;
  edge_type: 'blocked_by' | 'cross_ref';
}

export interface CriticalPath {
  task_ids: string[];
  chain_length: number;
  stages_remaining: number;
}

export interface PertData {
  nodes: PertNode[];
  edges: PertEdge[];
  critical_path: CriticalPath | null;
  total_tasks: number;
  completed_count: number;
  blocked_count: number;
}

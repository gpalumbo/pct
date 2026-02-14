import { useEffect, useState } from 'react';
import { Button, Select, Switch, Table, message } from 'antd';
import { useWorkflowStages, useSaveWorkflowStages, useAgents } from '../../hooks/useConfigQueries';
import { ALL_TASK_STATUSES, TASK_STATUS_LABELS } from '../../types/config';
import type { WorkflowStageConfig } from '../../types/config';

export default function WorkflowTab() {
  const { data: savedStages = [] } = useWorkflowStages();
  const { data: agents = [] } = useAgents();
  const saveStages = useSaveWorkflowStages();

  const [stages, setStages] = useState<WorkflowStageConfig[]>([]);

  useEffect(() => {
    // Initialize from saved or create defaults for all statuses
    const map = new Map(savedStages.map((s) => [s.stage, s]));
    setStages(
      ALL_TASK_STATUSES.map((status) =>
        map.get(status) ?? { stage: status, enabled: true, agent: null }
      )
    );
  }, [savedStages]);

  const updateStage = (index: number, patch: Partial<WorkflowStageConfig>) => {
    setStages((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const handleSave = async () => {
    await saveStages.mutateAsync(stages);
    message.success('Workflow stages saved');
  };

  const columns = [
    {
      title: 'Stage',
      dataIndex: 'stage',
      key: 'stage',
      render: (val: WorkflowStageConfig['stage']) => TASK_STATUS_LABELS[val],
    },
    {
      title: 'Enabled',
      key: 'enabled',
      render: (_: unknown, _record: WorkflowStageConfig, index: number) => (
        <Switch checked={stages[index]?.enabled} onChange={(v) => updateStage(index, { enabled: v })} />
      ),
    },
    {
      title: 'Agent',
      key: 'agent',
      render: (_: unknown, _record: WorkflowStageConfig, index: number) => (
        <Select
          allowClear
          style={{ width: 200 }}
          value={stages[index]?.agent}
          onChange={(v) => updateStage(index, { agent: v ?? null })}
          options={agents.map((a) => ({ label: a.id, value: a.id }))}
          placeholder="Select agent"
        />
      ),
    },
  ];

  return (
    <>
      <Table
        dataSource={stages}
        columns={columns}
        rowKey="stage"
        pagination={false}
        size="small"
      />
      <Button
        type="primary"
        onClick={handleSave}
        loading={saveStages.isPending}
        style={{ marginTop: 16 }}
      >
        Save Changes
      </Button>
    </>
  );
}

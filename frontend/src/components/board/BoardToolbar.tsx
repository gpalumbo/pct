import { useState } from 'react';
import { Button, Select, Space, Switch, Typography } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useBoardStore } from '../../stores/boardStore';
import { useCreateFeature } from '../../hooks/useBoardQueries';
import type { Feature } from '../../types/board';
import CreateFeatureModal from './CreateFeatureModal';

const { Text } = Typography;

interface BoardToolbarProps {
  features: Feature[];
  onRefresh: () => void;
}

export default function BoardToolbar({ features, onRefresh }: BoardToolbarProps) {
  const filterFeatureIds = useBoardStore((s) => s.filterFeatureIds);
  const showSuspended = useBoardStore((s) => s.showSuspended);
  const showComplete = useBoardStore((s) => s.showComplete);
  const setFilterFeatureIds = useBoardStore((s) => s.setFilterFeatureIds);
  const setShowSuspended = useBoardStore((s) => s.setShowSuspended);
  const setShowComplete = useBoardStore((s) => s.setShowComplete);

  const [showCreateFeature, setShowCreateFeature] = useState(false);
  const createFeature = useCreateFeature();

  const featureOptions = features.map((f) => ({ label: f.title, value: f.id }));

  const handleCreateFeature = (id: string, title: string) => {
    createFeature.mutate(
      { id, title, specification: `# ${title}\n` },
      { onSuccess: () => setShowCreateFeature(false) },
    );
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 16px',
        borderBottom: '1px solid #e8e8e8',
        flexWrap: 'wrap',
      }}
    >
      <Select
        mode="multiple"
        allowClear
        placeholder="Filter features..."
        value={filterFeatureIds}
        onChange={setFilterFeatureIds}
        options={featureOptions}
        style={{ minWidth: 200 }}
        size="small"
      />
      <Space size="small">
        <Switch size="small" checked={showSuspended} onChange={setShowSuspended} />
        <Text style={{ fontSize: 12 }}>Suspended</Text>
      </Space>
      <Space size="small">
        <Switch size="small" checked={showComplete} onChange={setShowComplete} />
        <Text style={{ fontSize: 12 }}>Complete</Text>
      </Space>
      <Button size="small" icon={<PlusOutlined />} onClick={() => setShowCreateFeature(true)}>
        New Feature
      </Button>
      <Button size="small" icon={<ReloadOutlined />} onClick={onRefresh}>
        Refresh
      </Button>
      <CreateFeatureModal
        open={showCreateFeature}
        onCancel={() => setShowCreateFeature(false)}
        onSubmit={handleCreateFeature}
        loading={createFeature.isPending}
      />
    </div>
  );
}

import { useState } from 'react';
import { Button, Dropdown, Space, Tag, Typography } from 'antd';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  ExperimentOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import type { Feature } from '../../types/board';
import { runGapAnalysis, runContinuityCheck } from '../../api/boardApi';
import AnalysisModal from './AnalysisModal';

const { Text } = Typography;

const STAGE_COLORS: Record<string, string> = {
  planning: 'blue',
  active: 'green',
  suspended: 'orange',
  'integration-test': 'purple',
  complete: 'default',
  // Writing workflow stages
  concept: 'cyan',
  outline: 'blue',
  draft: 'geekblue',
  revise: 'orange',
  polish: 'gold',
};

interface SwimlaneHeaderProps {
  feature: Feature;
  collapsed: boolean;
  onToggle: () => void;
  onSuspend: () => void;
  onResume: () => void;
  onAddTask: () => void;
}

export default function SwimlaneHeader({
  feature,
  collapsed,
  onToggle,
  onSuspend,
  onResume,
  onAddTask,
}: SwimlaneHeaderProps) {
  const stage = feature.metadata.lifecycle_stage;
  const totalTasks = feature.tasks.length;
  const doneTasks = feature.tasks.filter((t) => t.status === 'done').length;
  const [analysisModal, setAnalysisModal] = useState<'gap' | 'continuity' | null>(null);

  const analysisMenuItems: MenuProps['items'] = [
    {
      key: 'gap',
      label: 'Gap Analysis',
      onClick: () => setAnalysisModal('gap'),
    },
    {
      key: 'continuity',
      label: 'Continuity Check',
      onClick: () => setAnalysisModal('continuity'),
    },
  ];

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '4px 8px',
          background: '#fafafa',
          borderBottom: '1px solid #f0f0f0',
          cursor: 'pointer',
          userSelect: 'none',
        }}
        onClick={onToggle}
      >
        {collapsed ? <CaretRightOutlined /> : <CaretDownOutlined />}
        <Text strong style={{ fontSize: 13 }}>
          {feature.title}
        </Text>
        <Tag color={STAGE_COLORS[stage] || 'default'} style={{ margin: 0 }}>
          {stage}
        </Tag>
        {totalTasks > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {doneTasks}/{totalTasks}
          </Text>
        )}
        <Space style={{ marginLeft: 'auto' }} onClick={(e) => e.stopPropagation()}>
          <Button
            size="small"
            type="text"
            icon={<PlusOutlined />}
            onClick={onAddTask}
          >
            Add Task
          </Button>
          <Dropdown menu={{ items: analysisMenuItems }} trigger={['click']}>
            <Button
              size="small"
              type="text"
              icon={<ExperimentOutlined />}
            >
              Analyze
            </Button>
          </Dropdown>
          {stage !== 'suspended' ? (
            <Button
              size="small"
              type="text"
              icon={<PauseCircleOutlined />}
              onClick={onSuspend}
            >
              Suspend
            </Button>
          ) : (
            <Button
              size="small"
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={onResume}
            >
              Resume
            </Button>
          )}
        </Space>
      </div>

      {/* Analysis modals */}
      <AnalysisModal
        open={analysisModal === 'gap'}
        title={`Gap Analysis: ${feature.title}`}
        featureId={feature.id}
        runAnalysis={runGapAnalysis}
        onClose={() => setAnalysisModal(null)}
      />
      <AnalysisModal
        open={analysisModal === 'continuity'}
        title={`Continuity Check: ${feature.title}`}
        featureId={feature.id}
        runAnalysis={runContinuityCheck}
        onClose={() => setAnalysisModal(null)}
      />
    </>
  );
}

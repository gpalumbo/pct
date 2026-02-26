import { useState } from 'react';
import { Modal, Collapse, Checkbox, Typography, Empty } from 'antd';
import type { Feature } from '../../types/board';

const { Text } = Typography;

interface CrossRefPickerProps {
  open: boolean;
  features: Feature[];
  currentFeatureId: string;
  currentTaskId: string;
  selected: string[]; // existing cross_depends_on entries ("featureId:taskId")
  onOk: (selected: string[]) => void;
  onCancel: () => void;
}

export default function CrossRefPicker({
  open,
  features,
  currentFeatureId,
  currentTaskId,
  selected,
  onOk,
  onCancel,
}: CrossRefPickerProps) {
  const [checked, setChecked] = useState<Set<string>>(new Set(selected));

  const handleToggle = (key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleOk = () => {
    onOk(Array.from(checked));
  };

  // Reset checked state when modal opens
  const handleAfterOpenChange = (visible: boolean) => {
    if (visible) {
      setChecked(new Set(selected));
    }
  };

  const items = features.map((feature) => ({
    key: feature.id,
    label: (
      <Text strong style={{ fontSize: 13 }}>
        {feature.title}
      </Text>
    ),
    children: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {feature.tasks
          .filter((t) => !(t.feature === currentFeatureId && t.id === currentTaskId))
          .map((task) => {
            const key = `${feature.id}:${task.id}`;
            return (
              <Checkbox key={key} checked={checked.has(key)} onChange={() => handleToggle(key)}>
                <Text style={{ fontSize: 12 }}>
                  {task.title}
                  <Text type="secondary" style={{ fontSize: 10, marginLeft: 4 }}>
                    ({task.id})
                  </Text>
                </Text>
              </Checkbox>
            );
          })}
        {feature.tasks.filter((t) => !(t.feature === currentFeatureId && t.id === currentTaskId))
          .length === 0 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            No tasks available
          </Text>
        )}
      </div>
    ),
  }));

  return (
    <Modal
      title="Add Cross-References"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      afterOpenChange={handleAfterOpenChange}
      width={480}
    >
      {features.length === 0 ? (
        <Empty description="No features available" />
      ) : (
        <Collapse
          items={items}
          defaultActiveKey={features.map((f) => f.id)}
          size="small"
          style={{ maxHeight: 400, overflow: 'auto' }}
        />
      )}
    </Modal>
  );
}

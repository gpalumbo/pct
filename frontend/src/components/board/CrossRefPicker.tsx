import { Select, Typography } from 'antd';
import { useBoardStore } from '../../stores/boardStore';
import type { Task } from '../../types/board';

const { Text } = Typography;

interface CrossRefPickerProps {
  currentTaskId: string;
  selectedRefs: string[];
  onChange: (refs: string[]) => void;
}

export default function CrossRefPicker({ currentTaskId, selectedRefs, onChange }: CrossRefPickerProps) {
  const features = useBoardStore((s) => s.features);

  const allTasks: Task[] = features.flatMap((f) => f.tasks).filter((t) => t.id !== currentTaskId);

  const options = allTasks.map((task) => {
    const feature = features.find((f) => f.id === task.feature_id);
    return {
      value: task.id,
      label: `${feature?.title ?? 'Unknown'} / ${task.title}`,
    };
  });

  return (
    <div>
      <Text strong style={{ display: 'block', marginBottom: 4 }}>
        Cross References
      </Text>
      <Select
        mode="multiple"
        value={selectedRefs}
        onChange={onChange}
        options={options}
        placeholder="Select related tasks..."
        style={{ width: '100%' }}
        filterOption={(input, option) =>
          (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
        }
      />
    </div>
  );
}

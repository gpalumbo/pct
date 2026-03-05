import { Modal, Select } from 'antd';
import { useBoardStore } from '../../stores/boardStore';

interface WikiLinkPickerProps {
  open: boolean;
  onSelect: (ref: string) => void;
  onCancel: () => void;
}

export default function WikiLinkPicker({ open, onSelect, onCancel }: WikiLinkPickerProps) {
  const features = useBoardStore((s) => s.features);

  const options = features.flatMap((f) =>
    f.tasks.map((t) => ({
      value: `${f.id}#${t.id}`,
      label: `${f.title} / ${t.title}`,
    })),
  );

  return (
    <Modal title="Insert WikiLink" open={open} onCancel={onCancel} footer={null} width={480}>
      <Select
        showSearch
        placeholder="Search for a task..."
        options={options}
        style={{ width: '100%' }}
        filterOption={(input, option) =>
          (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
        }
        onSelect={(value: string) => onSelect(value)}
      />
    </Modal>
  );
}

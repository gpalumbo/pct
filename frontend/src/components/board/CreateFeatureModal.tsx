import { useEffect, useState } from 'react';
import { Input, Modal } from 'antd';

interface CreateFeatureModalProps {
  open: boolean;
  onCancel: () => void;
  onSubmit: (id: string, title: string) => void;
  loading: boolean;
}

export default function CreateFeatureModal({
  open,
  onCancel,
  onSubmit,
  loading,
}: CreateFeatureModalProps) {
  const [featureId, setFeatureId] = useState('');
  const [title, setTitle] = useState('');

  useEffect(() => {
    if (!open) {
      setFeatureId('');
      setTitle('');
    }
  }, [open]);

  const handleOk = () => {
    const id = featureId.trim();
    const t = title.trim();
    if (id && t) {
      onSubmit(id, t);
    }
  };

  return (
    <Modal
      title="New Feature"
      open={open}
      onCancel={onCancel}
      onOk={handleOk}
      confirmLoading={loading}
      okButtonProps={{ disabled: !featureId.trim() || !title.trim() }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
        <Input
          placeholder="Feature ID (e.g. f3-auth-system)"
          value={featureId}
          onChange={(e) => setFeatureId(e.target.value)}
          autoFocus
        />
        <Input
          placeholder="Feature title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onPressEnter={handleOk}
        />
      </div>
    </Modal>
  );
}

import { useState, useEffect } from 'react';
import { Modal, Input, message } from 'antd';
import { boardApi } from '../../api/boardApi';

const { TextArea } = Input;

interface ArtifactEditorModalProps {
  open: boolean;
  content: string;
  featureId: string;
  taskId: string;
  onClose: () => void;
}

export default function ArtifactEditorModal({ open, content, featureId, taskId, onClose }: ArtifactEditorModalProps) {
  const [editContent, setEditContent] = useState(content);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setEditContent(content);
    }
  }, [open, content]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await boardApi.putArtifact(featureId, taskId, editContent);
      message.success('Artifact saved');
      onClose();
    } catch {
      message.error('Failed to save artifact');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Edit Artifact"
      onOk={handleSave}
      onCancel={onClose}
      confirmLoading={saving}
      okText="Save"
      width={720}
    >
      <TextArea
        value={editContent}
        onChange={(e) => setEditContent(e.target.value)}
        rows={20}
        style={{ fontFamily: 'monospace', fontSize: 13 }}
      />
    </Modal>
  );
}

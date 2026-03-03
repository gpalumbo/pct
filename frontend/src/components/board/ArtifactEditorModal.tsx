import { useState, useEffect, useCallback } from 'react';
import { Modal, App } from 'antd';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import { boardApi } from '../../api/boardApi';

interface ArtifactEditorModalProps {
  open: boolean;
  content: string;
  featureId: string;
  taskId: string;
  onClose: () => void;
}

export default function ArtifactEditorModal({ open, content, featureId, taskId, onClose }: ArtifactEditorModalProps) {
  const { message } = App.useApp();
  const [saving, setSaving] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Markdown,
    ],
    content: '',
    editorProps: {
      attributes: {
        style: 'min-height: 400px; padding: 12px; outline: none; font-size: 14px;',
      },
    },
  });

  useEffect(() => {
    if (open && editor) {
      editor.commands.setContent(content || '');
    }
  }, [open, content, editor]);

  const handleSave = useCallback(async () => {
    if (!editor) return;
    setSaving(true);
    try {
      const md = editor.storage.markdown.getMarkdown() as string;
      await boardApi.putArtifact(featureId, taskId, md);
      message.success('Artifact saved');
      onClose();
    } catch {
      message.error('Failed to save artifact');
    } finally {
      setSaving(false);
    }
  }, [editor, featureId, taskId, message, onClose]);

  return (
    <Modal
      open={open}
      title="Edit Artifact"
      onOk={handleSave}
      onCancel={onClose}
      confirmLoading={saving}
      okText="Save"
      width={800}
    >
      <div
        style={{
          border: '1px solid #d9d9d9',
          borderRadius: 6,
          maxHeight: '60vh',
          overflow: 'auto',
        }}
      >
        <EditorContent editor={editor} />
      </div>
    </Modal>
  );
}

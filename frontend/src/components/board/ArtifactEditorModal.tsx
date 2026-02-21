import { useEffect } from 'react';
import { Modal } from 'antd';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import './sidebar.css';

interface ArtifactEditorModalProps {
  open: boolean;
  content: string;
  onSave: (markdown: string) => void;
  onCancel: () => void;
}

export default function ArtifactEditorModal({ open, content, onSave, onCancel }: ArtifactEditorModalProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Markdown,
    ],
    content: '',
  });

  // Sync content into editor when modal opens
  useEffect(() => {
    if (editor && open) {
      editor.commands.setContent(content || '');
    }
  }, [editor, open, content]);

  const handleOk = () => {
    if (!editor) return;
    const md = editor.storage.markdown.getMarkdown() as string;
    onSave(md);
  };

  return (
    <Modal
      title="Edit Artifact"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      okText="Save"
      width={800}
      styles={{ body: { padding: 0 } }}
      destroyOnClose={false}
    >
      <div className="artifact-editor">
        {/* Toolbar */}
        {editor && (
          <div className="toolbar-row" style={{
            display: 'flex',
            gap: 2,
            padding: '6px 8px',
            flexWrap: 'wrap',
          }}>
            <ToolbarBtn
              label="B"
              active={editor.isActive('bold')}
              onClick={() => editor.chain().focus().toggleBold().run()}
              style={{ fontWeight: 'bold' }}
            />
            <ToolbarBtn
              label="I"
              active={editor.isActive('italic')}
              onClick={() => editor.chain().focus().toggleItalic().run()}
              style={{ fontStyle: 'italic' }}
            />
            <ToolbarBtn
              label="S"
              active={editor.isActive('strike')}
              onClick={() => editor.chain().focus().toggleStrike().run()}
              style={{ textDecoration: 'line-through' }}
            />
            <Separator />
            <ToolbarBtn
              label="H1"
              active={editor.isActive('heading', { level: 1 })}
              onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            />
            <ToolbarBtn
              label="H2"
              active={editor.isActive('heading', { level: 2 })}
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            />
            <ToolbarBtn
              label="H3"
              active={editor.isActive('heading', { level: 3 })}
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            />
            <Separator />
            <ToolbarBtn
              label="UL"
              active={editor.isActive('bulletList')}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
            />
            <ToolbarBtn
              label="OL"
              active={editor.isActive('orderedList')}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
            />
            <ToolbarBtn
              label="Code"
              active={editor.isActive('codeBlock')}
              onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            />
            <ToolbarBtn
              label="Quote"
              active={editor.isActive('blockquote')}
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
            />
            <Separator />
            <ToolbarBtn
              label="HR"
              active={false}
              onClick={() => editor.chain().focus().setHorizontalRule().run()}
            />
          </div>
        )}

        {/* Editor area */}
        <div style={{
          minHeight: 400,
          maxHeight: '60vh',
          overflowY: 'auto',
          padding: '12px 16px',
        }}>
          <EditorContent editor={editor} />
        </div>
      </div>

    </Modal>
  );
}

function ToolbarBtn({ label, active, onClick, style }: {
  label: string;
  active: boolean;
  onClick: () => void;
  style?: React.CSSProperties;
}) {
  return (
    <button
      type="button"
      className={`toolbar-btn${active ? ' active' : ''}`}
      onMouseDown={(e) => { e.preventDefault(); onClick(); }}
      style={style}
    >
      {label}
    </button>
  );
}

function Separator() {
  return <div className="toolbar-separator" />;
}

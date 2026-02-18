import { useEffect } from 'react';
import { Modal } from 'antd';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';

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
          <div style={{
            display: 'flex',
            gap: 2,
            padding: '6px 8px',
            borderBottom: '1px solid #f0f0f0',
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

      <style>{`
        .artifact-editor .tiptap {
          outline: none;
          font-size: 14px;
          line-height: 1.6;
        }
        .artifact-editor .tiptap h1 { font-size: 1.6em; font-weight: 600; margin: 0.6em 0 0.3em; }
        .artifact-editor .tiptap h2 { font-size: 1.3em; font-weight: 600; margin: 0.5em 0 0.3em; }
        .artifact-editor .tiptap h3 { font-size: 1.1em; font-weight: 600; margin: 0.4em 0 0.2em; }
        .artifact-editor .tiptap p { margin: 0.4em 0; }
        .artifact-editor .tiptap ul, .artifact-editor .tiptap ol { padding-left: 1.5em; }
        .artifact-editor .tiptap blockquote {
          border-left: 3px solid #d9d9d9;
          padding-left: 12px;
          color: #595959;
          margin: 0.5em 0;
        }
        .artifact-editor .tiptap pre {
          background: #f5f5f5;
          border-radius: 4px;
          padding: 12px;
          font-family: monospace;
          font-size: 13px;
          overflow-x: auto;
        }
        .artifact-editor .tiptap code {
          background: #f5f5f5;
          border-radius: 2px;
          padding: 1px 4px;
          font-family: monospace;
          font-size: 0.9em;
        }
        .artifact-editor .tiptap hr {
          border: none;
          border-top: 1px solid #d9d9d9;
          margin: 1em 0;
        }
      `}</style>
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
      onMouseDown={(e) => { e.preventDefault(); onClick(); }}
      style={{
        padding: '2px 8px',
        fontSize: 12,
        border: '1px solid',
        borderColor: active ? '#1890ff' : '#d9d9d9',
        borderRadius: 3,
        background: active ? '#e6f7ff' : '#fff',
        color: active ? '#1890ff' : '#333',
        cursor: 'pointer',
        lineHeight: '20px',
        ...style,
      }}
    >
      {label}
    </button>
  );
}

function Separator() {
  return <div style={{ width: 1, background: '#e8e8e8', margin: '0 4px', alignSelf: 'stretch' }} />;
}

import { useState, useEffect, type ReactNode } from 'react';
import { Modal, Tooltip } from 'antd';
import {
  BoldOutlined,
  ItalicOutlined,
  StrikethroughOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  CodeOutlined,
  LineOutlined,
  UndoOutlined,
  RedoOutlined,
  LinkOutlined,
  PictureOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import WikiLinkNode from '../../extensions/WikiLinkNode';
import ImagePickerModal from './ImagePickerModal';
import WikiLinkPicker from './WikiLinkPicker';
import { getImageUrl } from '../../api/imagegenApi';
import './sidebar.css';

interface ArtifactEditorModalProps {
  open: boolean;
  content: string;
  featureId: string;
  taskId: string;
  onSave: (markdown: string) => void;
  onCancel: () => void;
}

export default function ArtifactEditorModal({
  open,
  content,
  featureId,
  taskId: _taskId,
  onSave,
  onCancel,
}: ArtifactEditorModalProps) {
  const [imagePickerOpen, setImagePickerOpen] = useState(false);
  const [wikiLinkPickerOpen, setWikiLinkPickerOpen] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Markdown,
      Link.configure({ openOnClick: false, autolink: true }),
      Image.configure({
        inline: false,
        allowBase64: false,
        HTMLAttributes: { class: 'artifact-image' },
      }),
      WikiLinkNode,
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

  const handleLinkToggle = () => {
    if (!editor) return;
    if (editor.isActive('link')) {
      editor.chain().focus().unsetLink().run();
    } else {
      const url = window.prompt('URL');
      if (url) {
        editor.chain().focus().setLink({ href: url }).run();
      }
    }
  };

  return (
    <>
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
            <div
              className="toolbar-row"
              style={{
                display: 'flex',
                gap: 2,
                padding: '6px 8px',
                flexWrap: 'wrap',
              }}
            >
              <ToolbarBtn
                label={<BoldOutlined />}
                tooltip="Bold"
                active={editor.isActive('bold')}
                onClick={() => editor.chain().focus().toggleBold().run()}
              />
              <ToolbarBtn
                label={<ItalicOutlined />}
                tooltip="Italic"
                active={editor.isActive('italic')}
                onClick={() => editor.chain().focus().toggleItalic().run()}
              />
              <ToolbarBtn
                label={<StrikethroughOutlined />}
                tooltip="Strikethrough"
                active={editor.isActive('strike')}
                onClick={() => editor.chain().focus().toggleStrike().run()}
              />
              <ToolbarBtn
                label={<span style={{ fontSize: '0.85em', fontFamily: 'monospace' }}>&lt;/&gt;</span>}
                tooltip="Inline code"
                active={editor.isActive('code')}
                onClick={() => editor.chain().focus().toggleCode().run()}
              />
              <Separator />
              <ToolbarBtn
                label="H1"
                tooltip="Heading 1"
                active={editor.isActive('heading', { level: 1 })}
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
              />
              <ToolbarBtn
                label="H2"
                tooltip="Heading 2"
                active={editor.isActive('heading', { level: 2 })}
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              />
              <ToolbarBtn
                label="H3"
                tooltip="Heading 3"
                active={editor.isActive('heading', { level: 3 })}
                onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              />
              <Separator />
              <ToolbarBtn
                label={<UnorderedListOutlined />}
                tooltip="Bullet list"
                active={editor.isActive('bulletList')}
                onClick={() => editor.chain().focus().toggleBulletList().run()}
              />
              <ToolbarBtn
                label={<OrderedListOutlined />}
                tooltip="Numbered list"
                active={editor.isActive('orderedList')}
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
              />
              <ToolbarBtn
                label={<CodeOutlined />}
                tooltip="Code block"
                active={editor.isActive('codeBlock')}
                onClick={() => editor.chain().focus().toggleCodeBlock().run()}
              />
              <ToolbarBtn
                label={<span style={{ fontWeight: 600 }}>&ldquo;&rdquo;</span>}
                tooltip="Blockquote"
                active={editor.isActive('blockquote')}
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
              />
              <Separator />
              <ToolbarBtn
                label={<LineOutlined />}
                tooltip="Horizontal rule"
                active={false}
                onClick={() => editor.chain().focus().setHorizontalRule().run()}
              />
              <Separator />
              <ToolbarBtn
                label={<UndoOutlined />}
                tooltip="Undo"
                active={false}
                onClick={() => editor.chain().focus().undo().run()}
              />
              <ToolbarBtn
                label={<RedoOutlined />}
                tooltip="Redo"
                active={false}
                onClick={() => editor.chain().focus().redo().run()}
              />
              <Separator />
              <ToolbarBtn
                label={<LinkOutlined />}
                tooltip="Link"
                active={editor.isActive('link')}
                onClick={handleLinkToggle}
              />
              <ToolbarBtn
                label={<PictureOutlined />}
                tooltip="Insert image"
                active={false}
                onClick={() => setImagePickerOpen(true)}
              />
              <ToolbarBtn
                label={<TagOutlined />}
                tooltip="Insert WikiLink"
                active={false}
                onClick={() => setWikiLinkPickerOpen(true)}
              />
            </div>
          )}

          {/* Editor area */}
          <div
            style={{
              minHeight: 400,
              maxHeight: '60vh',
              overflowY: 'auto',
              padding: '12px 16px',
            }}
          >
            <EditorContent editor={editor} />
          </div>
        </div>
      </Modal>

      <ImagePickerModal
        open={imagePickerOpen}
        featureId={featureId}
        onSelect={(img) => {
          const url = getImageUrl(img.feature_id, img.task_id, img.id);
          editor?.chain().focus().setImage({ src: url, alt: img.filename }).run();
          setImagePickerOpen(false);
        }}
        onCancel={() => setImagePickerOpen(false)}
      />

      <WikiLinkPicker
        open={wikiLinkPickerOpen}
        onSelect={(ref) => {
          editor?.chain().focus().insertWikiLink(ref).run();
          setWikiLinkPickerOpen(false);
        }}
        onCancel={() => setWikiLinkPickerOpen(false)}
      />
    </>
  );
}

function ToolbarBtn({
  label,
  tooltip,
  active,
  onClick,
}: {
  label: ReactNode;
  tooltip: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Tooltip title={tooltip} mouseEnterDelay={0.4}>
      <button
        type="button"
        className={`toolbar-btn${active ? ' active' : ''}`}
        onMouseDown={(e) => {
          e.preventDefault();
          onClick();
        }}
      >
        {label}
      </button>
    </Tooltip>
  );
}

function Separator() {
  return <div className="toolbar-separator" />;
}

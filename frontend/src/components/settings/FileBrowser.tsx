import { useEffect, useState } from 'react';
import { Button, Input, List, Modal, Space, Typography, message } from 'antd';
import { FolderOutlined, FileOutlined, ArrowUpOutlined } from '@ant-design/icons';
import { browseFiles, type FileEntry } from '../../api/configApi';

const { Text } = Typography;

interface FileBrowserProps {
  open: boolean;
  onCancel: () => void;
  onSelect: (path: string) => void;
  title?: string;
}

export default function FileBrowser({ open, onCancel, onSelect, title = 'Browse Files' }: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState('');
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [pathInput, setPathInput] = useState('');

  const loadDir = async (path: string) => {
    setLoading(true);
    try {
      const data = await browseFiles(path);
      setEntries(data);
      setCurrentPath(path);
      setPathInput(path);
    } catch {
      message.error('Could not browse directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadDir('');
    }
  }, [open]);

  const goUp = () => {
    const parts = currentPath.replace(/\\/g, '/').split('/').filter(Boolean);
    if (parts.length <= 1) {
      // At root or one level deep — go to filesystem root
      const root = currentPath.match(/^[A-Za-z]:/) ? currentPath.slice(0, 3) : '/';
      loadDir(root);
    } else {
      parts.pop();
      loadDir(parts.join('/'));
    }
  };

  const handleNavigate = (entry: FileEntry) => {
    if (entry.is_dir) {
      loadDir(entry.path);
    } else {
      onSelect(entry.path);
    }
  };

  const handlePathSubmit = () => {
    if (pathInput) loadDir(pathInput);
  };

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={600}
    >
      <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
        <Input
          value={pathInput}
          onChange={(e) => setPathInput(e.target.value)}
          onPressEnter={handlePathSubmit}
          placeholder="Enter path..."
        />
        <Button onClick={handlePathSubmit}>Go</Button>
      </Space.Compact>

      <Button icon={<ArrowUpOutlined />} size="small" onClick={goUp} style={{ marginBottom: 8 }}>
        Up
      </Button>

      <List
        loading={loading}
        size="small"
        style={{ maxHeight: 400, overflow: 'auto' }}
        dataSource={entries}
        renderItem={(entry) => (
          <List.Item
            style={{ cursor: 'pointer', padding: '4px 8px' }}
            onClick={() => handleNavigate(entry)}
            actions={
              !entry.is_dir
                ? [<Button size="small" type="link" onClick={(e) => { e.stopPropagation(); onSelect(entry.path); }}>Select</Button>]
                : undefined
            }
          >
            <Space>
              {entry.is_dir ? <FolderOutlined style={{ color: '#faad14' }} /> : <FileOutlined />}
              <Text>{entry.name}</Text>
            </Space>
          </List.Item>
        )}
      />
    </Modal>
  );
}

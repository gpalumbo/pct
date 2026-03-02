import { useState } from 'react';
import { List, Breadcrumb, Typography, Spin } from 'antd';
import { FolderOutlined, FileOutlined } from '@ant-design/icons';
import { useBrowseFiles } from '../../hooks/useConfigQueries';
import type { FileEntry } from '../../types/config';

const { Text } = Typography;

interface FileBrowserProps {
  onSelect?: (entry: FileEntry) => void;
}

export default function FileBrowser({ onSelect }: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState<string | undefined>(undefined);
  const { data: entries, isLoading } = useBrowseFiles(currentPath ?? '/');

  const pathParts = currentPath ? currentPath.split('/').filter(Boolean) : [];

  const navigateTo = (entry: FileEntry) => {
    if (entry.is_dir) {
      setCurrentPath(entry.path);
    } else {
      onSelect?.(entry);
    }
  };

  const navigateToBreadcrumb = (index: number) => {
    if (index < 0) {
      setCurrentPath(undefined);
    } else {
      const path = '/' + pathParts.slice(0, index + 1).join('/');
      setCurrentPath(path);
    }
  };

  if (isLoading) return <Spin />;

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          {
            title: (
              <a onClick={() => navigateToBreadcrumb(-1)}>Root</a>
            ),
          },
          ...pathParts.map((part, i) => ({
            title: (
              <a onClick={() => navigateToBreadcrumb(i)}>{part}</a>
            ),
          })),
        ]}
      />
      <List
        size="small"
        dataSource={entries ?? []}
        locale={{ emptyText: 'Empty directory' }}
        renderItem={(entry: FileEntry) => (
          <List.Item
            style={{ cursor: 'pointer', padding: '4px 8px' }}
            onClick={() => navigateTo(entry)}
          >
            {entry.is_dir ? <FolderOutlined style={{ marginRight: 8 }} /> : <FileOutlined style={{ marginRight: 8 }} />}
            <Text>{entry.name}</Text>
            {!entry.is_dir && (
              <Text type="secondary" style={{ marginLeft: 'auto' }}>
                {(entry.size / 1024).toFixed(1)} KB
              </Text>
            )}
          </List.Item>
        )}
      />
    </div>
  );
}

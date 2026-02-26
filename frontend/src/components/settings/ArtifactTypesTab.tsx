import { useEffect, useState } from 'react';
import { Button, Input, Space, Tooltip, Typography, message } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useArtifactTypes, useSaveArtifactTypes } from '../../hooks/useConfigQueries';
import type { ArtifactTypeConfig } from '../../types/config';

const { Text } = Typography;
const { TextArea } = Input;

function slugify(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export default function ArtifactTypesTab() {
  const { data: savedTypes = [] } = useArtifactTypes();
  const saveTypes = useSaveArtifactTypes();

  const [types, setTypes] = useState<ArtifactTypeConfig[]>([]);

  useEffect(() => {
    setTypes(savedTypes);
  }, [savedTypes]);

  const updateType = (index: number, patch: Partial<ArtifactTypeConfig>) => {
    setTypes((prev) => prev.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  };

  const addType = () => {
    const label = 'New Type';
    let id = slugify(label);
    const existing = new Set(types.map((t) => t.id));
    let counter = 1;
    while (existing.has(id)) {
      id = slugify(label) + '-' + counter++;
    }
    setTypes((prev) => [...prev, { id, label, template_hint: '' }]);
  };

  const removeType = (index: number) => {
    setTypes((prev) => prev.filter((_, i) => i !== index));
  };

  const handleLabelChange = (index: number, newLabel: string) => {
    const t = types[index];
    const oldSlug = slugify(t.label);
    const isAutoId = t.id === oldSlug || t.id.startsWith('new-type');
    const patch: Partial<ArtifactTypeConfig> = { label: newLabel };
    if (isAutoId) {
      const newSlug = slugify(newLabel);
      const existing = new Set(types.filter((_, i) => i !== index).map((x) => x.id));
      if (newSlug && !existing.has(newSlug)) {
        patch.id = newSlug;
      }
    }
    updateType(index, patch);
  };

  const handleSave = async () => {
    await saveTypes.mutateAsync(types);
    message.success('Artifact types saved');
  };

  return (
    <div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 13 }}>
        Artifact types determine how the AI assistant approaches each task. The template hint is
        injected into the system prompt when working on a task of that type.
      </Text>

      {/* Header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '120px 160px 1fr 40px',
          gap: 8,
          alignItems: 'center',
          padding: '4px 8px',
          fontWeight: 600,
          fontSize: 13,
          color: '#888',
          borderBottom: '1px solid #303030',
        }}
      >
        <div>ID</div>
        <div>Label</div>
        <div>Template Hint</div>
        <div></div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {types.map((t, index) => (
          <div
            key={t.id + '-' + index}
            style={{
              display: 'grid',
              gridTemplateColumns: '120px 160px 1fr 40px',
              gap: 8,
              alignItems: 'center',
              padding: '6px 8px',
              borderBottom: '1px solid #222',
            }}
          >
            {/* ID (read-only, auto-derived from label) */}
            <Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>
              {t.id}
            </Text>

            {/* Label */}
            <Input
              size="small"
              value={t.label}
              maxLength={40}
              onChange={(e) => handleLabelChange(index, e.target.value)}
              placeholder="Display label"
            />

            {/* Template hint */}
            <TextArea
              size="small"
              autoSize={{ minRows: 1, maxRows: 4 }}
              value={t.template_hint}
              onChange={(e) => updateType(index, { template_hint: e.target.value })}
              placeholder="LLM prompt hint for this artifact type"
              style={{ fontSize: 12 }}
            />

            {/* Delete */}
            <Tooltip title="Remove type">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeType(index)}
              />
            </Tooltip>
          </div>
        ))}
      </div>

      <Space style={{ marginTop: 16 }}>
        <Button icon={<PlusOutlined />} onClick={addType}>
          Add Type
        </Button>
        <Button type="primary" onClick={handleSave} loading={saveTypes.isPending}>
          Save Changes
        </Button>
      </Space>
    </div>
  );
}

import { useState } from 'react';
import {
  Typography,
  Button,
  Space,
  Modal,
  Form,
  Input,
  List,
  Tag,
  Empty,
  App,
} from 'antd';
import {
  PlusOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import {
  useTemplates,
  useCreateTemplateMutation,
  useUpdateTemplateMutation,
} from '../../hooks/useTrainingQueries';
import type { PromptTemplate, PromptTemplateVersion } from '../../types/training';

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function PromptTemplatesTab() {
  const { message } = App.useApp();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [createForm] = Form.useForm();

  const { data: templates, isLoading } = useTemplates();
  const createTemplate = useCreateTemplateMutation();
  const updateTemplate = useUpdateTemplateMutation();

  const selectedTemplate = (templates ?? []).find((t) => t.id === selectedId) ?? null;

  const handleSelect = (tmpl: PromptTemplate) => {
    setSelectedId(tmpl.id);
    const activeVersion = tmpl.versions.find((v) => v.version === tmpl.active_version);
    setEditContent(activeVersion?.content ?? '');
  };

  const handleCreate = async () => {
    const values = createForm.getFieldsValue() as { name: string; content: string };
    try {
      const tmpl = await createTemplate.mutateAsync(values);
      message.success('Template created');
      setCreateOpen(false);
      createForm.resetFields();
      setSelectedId(tmpl.id);
      setEditContent(values.content);
    } catch {
      message.error('Failed to create template');
    }
  };

  const handleSaveVersion = async () => {
    if (!selectedTemplate) return;
    try {
      await updateTemplate.mutateAsync({
        id: selectedTemplate.id,
        data: { content: editContent },
      });
      message.success('New version saved');
    } catch {
      message.error('Failed to save version');
    }
  };

  const activeVersionContent = selectedTemplate
    ? selectedTemplate.versions.find((v) => v.version === selectedTemplate.active_version)
        ?.content ?? ''
    : '';

  const hasChanges = selectedTemplate !== null && editContent !== activeVersionContent;

  return (
    <div style={{ display: 'flex', gap: 24, minHeight: 400 }}>
      {/* Left: Template list */}
      <div style={{ width: 280, flexShrink: 0 }}>
        <Space style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={5} style={{ margin: 0 }}>
            Templates
          </Title>
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setCreateOpen(true)}
          >
            New
          </Button>
        </Space>

        {isLoading ? (
          <Text type="secondary">Loading...</Text>
        ) : (templates ?? []).length === 0 ? (
          <Empty
            description="No templates yet"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            size="small"
            bordered
            dataSource={templates ?? []}
            renderItem={(tmpl: PromptTemplate) => (
              <List.Item
                onClick={() => handleSelect(tmpl)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: tmpl.id === selectedId ? '#e6f7ff' : undefined,
                  padding: '8px 12px',
                }}
              >
                <div style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text strong>{tmpl.name}</Text>
                    <Tag color="blue">v{tmpl.active_version}</Tag>
                  </div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {tmpl.versions.length} version{tmpl.versions.length !== 1 ? 's' : ''}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        )}
      </div>

      {/* Right: Editor and version history */}
      <div style={{ flex: 1 }}>
        {selectedTemplate === null ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Empty
              description="Select a template to edit"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </div>
        ) : (
          <>
            <Space style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
              <Title level={5} style={{ margin: 0 }}>
                {selectedTemplate.name}
              </Title>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveVersion}
                disabled={!hasChanges}
                loading={updateTemplate.isPending}
              >
                Save New Version
              </Button>
            </Space>

            <TextArea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={16}
              style={{ fontFamily: 'monospace', fontSize: 13, marginBottom: 16 }}
            />

            <div>
              <Space style={{ marginBottom: 8 }}>
                <HistoryOutlined />
                <Text strong>Version History</Text>
              </Space>
              <List
                size="small"
                bordered
                dataSource={[...selectedTemplate.versions].reverse()}
                renderItem={(ver: PromptTemplateVersion) => (
                  <List.Item
                    style={{ cursor: 'pointer', padding: '6px 12px' }}
                    onClick={() => setEditContent(ver.content)}
                    actions={[
                      ver.version === selectedTemplate.active_version ? (
                        <Tag key="active" color="green" icon={<CheckCircleOutlined />}>
                          Active
                        </Tag>
                      ) : (
                        <Text key="load" type="secondary" style={{ fontSize: 11 }}>
                          Click to load
                        </Text>
                      ),
                    ]}
                  >
                    <List.Item.Meta
                      title={"Version " + String(ver.version)}
                      description={new Date(ver.created_at).toLocaleString()}
                    />
                  </List.Item>
                )}
              />
            </div>
          </>
        )}
      </div>

      {/* Create Modal */}
      <Modal
        title="Create Prompt Template"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          createForm.resetFields();
        }}
        confirmLoading={createTemplate.isPending}
        width={600}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Name is required' }]}
          >
            <Input placeholder="e.g. code-review-prompt" />
          </Form.Item>
          <Form.Item
            name="content"
            label="Content"
            rules={[{ required: true, message: 'Content is required' }]}
          >
            <TextArea
              rows={10}
              style={{ fontFamily: 'monospace', fontSize: 13 }}
              placeholder="Enter your prompt template content..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

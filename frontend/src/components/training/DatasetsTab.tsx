import { useState } from 'react';
import {
  Table,
  Typography,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Tag,
  Popconfirm,
  Descriptions,
  List,
  message,
} from 'antd';
import { PlusOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  useDatasets,
  useCreateDatasetMutation,
  useUpdateDatasetMutation,
  useDeleteDatasetMutation,
} from '../../hooks/useTrainingQueries';
import type { Dataset, DatasetCreate, DatasetUpdate } from '../../types/training';

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function DatasetsTab() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null);
  const [viewingDataset, setViewingDataset] = useState<Dataset | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const { data: datasets, isLoading } = useDatasets();
  const createDataset = useCreateDatasetMutation();
  const updateDataset = useUpdateDatasetMutation();
  const deleteDataset = useDeleteDatasetMutation();

  const handleCreate = async () => {
    const values = createForm.getFieldsValue() as DatasetCreate;
    try {
      await createDataset.mutateAsync(values);
      message.success('Dataset created');
      setCreateOpen(false);
      createForm.resetFields();
    } catch {
      message.error('Failed to create dataset');
    }
  };

  const openEditModal = (ds: Dataset) => {
    setEditingDataset(ds);
    editForm.setFieldsValue({
      name: ds.name,
      description: ds.description ?? '',
    });
  };

  const handleEdit = async () => {
    if (!editingDataset) return;
    const values = editForm.getFieldsValue() as { name: string; description: string };
    const data: DatasetUpdate = {};
    if (values.name !== editingDataset.name) data.name = values.name;
    if (values.description !== (editingDataset.description ?? ''))
      data.description = values.description;
    try {
      await updateDataset.mutateAsync({ id: editingDataset.id, data });
      message.success('Dataset updated');
      setEditingDataset(null);
    } catch {
      message.error('Failed to update dataset');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDataset.mutateAsync(id);
      message.success('Dataset deleted');
    } catch {
      message.error('Failed to delete dataset');
    }
  };

  const columns: ColumnsType<Dataset> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string | null) => desc ?? <Text type="secondary">--</Text>,
    },
    {
      title: 'Entries',
      dataIndex: 'entries',
      key: 'entries',
      width: 90,
      render: (entries: string[]) => <Tag>{entries.length}</Tag>,
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 110,
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 130,
      render: (_: unknown, record: Dataset) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => setViewingDataset(record)}
          />
          <Button
            type="text"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => openEditModal(record)}
          />
          <Popconfirm
            title="Delete this dataset?"
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            cancelText="Cancel"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={5} style={{ margin: 0 }}>
          Datasets
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateOpen(true)}>
          Create Dataset
        </Button>
      </Space>

      <Table
        dataSource={datasets ?? []}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        locale={{ emptyText: 'No datasets yet' }}
        pagination={false}
      />

      {/* Create Modal */}
      <Modal
        title="Create Dataset"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          createForm.resetFields();
        }}
        confirmLoading={createDataset.isPending}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Name is required' }]}
          >
            <Input placeholder="e.g. style-corrections-v1" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Brief description of this dataset..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="Edit Dataset"
        open={editingDataset !== null}
        onOk={handleEdit}
        onCancel={() => setEditingDataset(null)}
        confirmLoading={updateDataset.isPending}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Name is required' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* View Entries Modal */}
      <Modal
        title={viewingDataset ? `Dataset: ${viewingDataset.name}` : 'Dataset'}
        open={viewingDataset !== null}
        onCancel={() => setViewingDataset(null)}
        footer={null}
        width={600}
      >
        {viewingDataset && (
          <>
            <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="ID">
                <Text code>{viewingDataset.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Description">
                {viewingDataset.description ?? 'None'}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {new Date(viewingDataset.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Updated">
                {new Date(viewingDataset.updated_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>Entries ({viewingDataset.entries.length})</Title>
            {viewingDataset.entries.length === 0 ? (
              <Text type="secondary">No entries in this dataset.</Text>
            ) : (
              <List
                size="small"
                bordered
                dataSource={viewingDataset.entries}
                renderItem={(entryId: string) => (
                  <List.Item>
                    <Text code>{entryId}</Text>
                  </List.Item>
                )}
              />
            )}
          </>
        )}
      </Modal>
    </div>
  );
}

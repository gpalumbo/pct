import { useState } from 'react';
import {
  Table,
  Typography,
  Select,
  Space,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Popconfirm,
  message,
} from 'antd';
import {
  LikeOutlined,
  DislikeOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  useFlags,
  useUpdateFlagMutation,
  useDeleteFlagMutation,
} from '../../hooks/useTrainingQueries';
import type { TrainingFlag, FlagUpdate } from '../../types/training';
import type { AnnotationCategory, CurationStatus, FlagType } from '../../types/enums';

const { Title, Text } = Typography;
const { TextArea } = Input;

const ANNOTATION_CATEGORY_OPTIONS: AnnotationCategory[] = [
  'style',
  'accuracy',
  'completeness',
  'format',
  'instruction_following',
  'other',
];

const CURATION_STATUS_OPTIONS: CurationStatus[] = ['raw', 'curated', 'in_dataset'];

const FLAG_TYPE_OPTIONS: FlagType[] = ['positive', 'negative'];

const curationStatusColors: Record<CurationStatus, string> = {
  raw: 'default',
  curated: 'blue',
  in_dataset: 'green',
};

export default function TrainingDataTab() {
  const [filterFlagType, setFilterFlagType] = useState<string | undefined>(undefined);
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined);
  const [editingFlag, setEditingFlag] = useState<TrainingFlag | null>(null);
  const [form] = Form.useForm();

  const { data: flags, isLoading } = useFlags({
    flag_type: filterFlagType,
    status: filterStatus,
  });
  const updateFlag = useUpdateFlagMutation();
  const deleteFlag = useDeleteFlagMutation();

  const openEditModal = (flag: TrainingFlag) => {
    setEditingFlag(flag);
    form.setFieldsValue({
      annotation_category: flag.annotation_category,
      note: flag.note ?? '',
      curation_status: flag.curation_status,
      edited_response: flag.edited_response ?? '',
    });
  };

  const handleEditSave = async () => {
    if (!editingFlag) return;
    const values = form.getFieldsValue() as {
      annotation_category: AnnotationCategory;
      note: string;
      curation_status: CurationStatus;
      edited_response: string;
    };
    const data: FlagUpdate = {};
    if (values.annotation_category !== editingFlag.annotation_category) {
      data.annotation_category = values.annotation_category;
    }
    if (values.note !== (editingFlag.note ?? '')) {
      data.note = values.note;
    }
    if (values.curation_status !== editingFlag.curation_status) {
      data.curation_status = values.curation_status;
    }
    if (values.edited_response !== (editingFlag.edited_response ?? '')) {
      data.edited_response = values.edited_response || undefined;
    }
    try {
      await updateFlag.mutateAsync({ id: editingFlag.id, data });
      message.success('Flag updated');
      setEditingFlag(null);
    } catch {
      message.error('Failed to update flag');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteFlag.mutateAsync(id);
      message.success('Flag deleted');
    } catch {
      message.error('Failed to delete flag');
    }
  };

  const columns: ColumnsType<TrainingFlag> = [
    {
      title: 'Type',
      dataIndex: 'flag_type',
      key: 'flag_type',
      width: 70,
      render: (flagType: FlagType) =>
        flagType === 'positive' ? (
          <LikeOutlined style={{ color: '#52c41a', fontSize: 16 }} />
        ) : (
          <DislikeOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
        ),
    },
    {
      title: 'Session',
      dataIndex: 'session_ref',
      key: 'session_ref',
      ellipsis: true,
      width: 140,
      render: (ref: string) => <Text code style={{ fontSize: 11 }}>{ref}</Text>,
    },
    {
      title: 'Category',
      dataIndex: 'annotation_category',
      key: 'annotation_category',
      width: 150,
      render: (cat: AnnotationCategory) => <Tag>{cat}</Tag>,
    },
    {
      title: 'Note',
      dataIndex: 'note',
      key: 'note',
      ellipsis: true,
      render: (note: string | null) => note ?? <Text type="secondary">--</Text>,
    },
    {
      title: 'Status',
      dataIndex: 'curation_status',
      key: 'curation_status',
      width: 110,
      render: (status: CurationStatus) => (
        <Tag color={curationStatusColors[status]}>{status}</Tag>
      ),
    },
    {
      title: 'Date',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 100,
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: TrainingFlag) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          />
          <Popconfirm
            title="Delete this flag?"
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
      <Title level={5}>Training Data Flags</Title>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="Filter by type"
          allowClear
          style={{ width: 160 }}
          value={filterFlagType}
          onChange={setFilterFlagType}
          options={FLAG_TYPE_OPTIONS.map((t) => ({ label: t, value: t }))}
        />
        <Select
          placeholder="Filter by status"
          allowClear
          style={{ width: 160 }}
          value={filterStatus}
          onChange={setFilterStatus}
          options={CURATION_STATUS_OPTIONS.map((s) => ({ label: s, value: s }))}
        />
      </Space>

      <Table
        dataSource={flags ?? []}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        locale={{ emptyText: 'No flags found' }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="Edit Flag"
        open={editingFlag !== null}
        onOk={handleEditSave}
        onCancel={() => setEditingFlag(null)}
        confirmLoading={updateFlag.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="annotation_category" label="Category">
            <Select
              options={ANNOTATION_CATEGORY_OPTIONS.map((c) => ({ label: c, value: c }))}
            />
          </Form.Item>
          <Form.Item name="curation_status" label="Curation Status">
            <Select
              options={CURATION_STATUS_OPTIONS.map((s) => ({ label: s, value: s }))}
            />
          </Form.Item>
          <Form.Item name="note" label="Note">
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item name="edited_response" label="Edited Response">
            <TextArea rows={6} placeholder="Provide the corrected/ideal response..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

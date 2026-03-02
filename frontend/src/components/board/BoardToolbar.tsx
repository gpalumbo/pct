import { Input, Select, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

const { Option } = Select;

interface BoardToolbarProps {
  searchText: string;
  onSearchChange: (value: string) => void;
  stageFilter: string | null;
  onStageFilterChange: (value: string | null) => void;
  stageOptions: { value: string; label: string }[];
}

export default function BoardToolbar({
  searchText,
  onSearchChange,
  stageFilter,
  onStageFilterChange,
  stageOptions,
}: BoardToolbarProps) {
  return (
    <Space style={{ marginBottom: 12 }} wrap>
      <Input
        prefix={<SearchOutlined />}
        placeholder="Search features/tasks..."
        value={searchText}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{ width: 260 }}
        allowClear
      />
      <Select
        placeholder="Filter by stage"
        value={stageFilter}
        onChange={onStageFilterChange}
        allowClear
        style={{ width: 180 }}
      >
        {stageOptions.map((opt) => (
          <Option key={opt.value} value={opt.value}>
            {opt.label}
          </Option>
        ))}
      </Select>
    </Space>
  );
}

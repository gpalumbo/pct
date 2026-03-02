/** PERT chart filter controls. */

import { Select, Checkbox, Radio, Space } from "antd";
import type { Feature } from "../../types/board";

const STATUS_OPTIONS = [
  { label: "Completed", value: "completed" },
  { label: "In Progress", value: "in-progress" },
  { label: "Blocked", value: "blocked" },
  { label: "Eligible", value: "eligible" },
];

interface PertFiltersProps {
  features: Feature[];
  featureFilter: string[];
  onFeatureFilterChange: (ids: string[]) => void;
  statusFilter: string[];
  onStatusFilterChange: (statuses: string[]) => void;
  direction: "LR" | "TB";
  onDirectionChange: (dir: "LR" | "TB") => void;
}

export default function PertFilters({
  features,
  featureFilter,
  onFeatureFilterChange,
  statusFilter,
  onStatusFilterChange,
  direction,
  onDirectionChange,
}: PertFiltersProps) {
  const featureOptions = features.map((f) => ({ label: f.title, value: f.id }));

  return (
    <Space wrap size="middle" style={{ marginBottom: 12 }}>
      <Select
        mode="multiple"
        placeholder="Filter by feature"
        options={featureOptions}
        value={featureFilter}
        onChange={onFeatureFilterChange}
        style={{ minWidth: 220 }}
        allowClear
        maxTagCount="responsive"
      />
      <Checkbox.Group
        options={STATUS_OPTIONS}
        value={statusFilter}
        onChange={(vals) => onStatusFilterChange(vals as string[])}
      />
      <Radio.Group
        value={direction}
        onChange={(e) => onDirectionChange(e.target.value as "LR" | "TB")}
        optionType="button"
        buttonStyle="solid"
        size="small"
      >
        <Radio.Button value="LR">Left to Right</Radio.Button>
        <Radio.Button value="TB">Top to Bottom</Radio.Button>
      </Radio.Group>
    </Space>
  );
}

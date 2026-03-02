/** PERT chart page -- project-wide or feature-scoped dependency graph. */

import { useState } from "react";
import { Card, Statistic, Space, Typography, Spin, Alert } from "antd";
import {
  NodeIndexOutlined,
  CheckCircleOutlined,
  StopOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useSearchParams, useNavigate } from "react-router-dom";
import PertChart from "../components/board/PertChart";
import PertFilters from "../components/board/PertFilters";
import { useProjectPert, useFeaturePert, useBoardQuery } from "../hooks/useBoardQueries";

const { Title } = Typography;

export default function PertPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const featureParam = searchParams.get("feature");

  const [featureFilter, setFeatureFilter] = useState<string[]>(
    featureParam ? [featureParam] : [],
  );
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [direction, setDirection] = useState<"LR" | "TB">("LR");

  const { data: board } = useBoardQuery();
  const features = board?.features ?? [];

  // Use feature-scoped query if exactly one feature is selected, otherwise project-wide
  const singleFeatureId = featureFilter.length === 1 ? featureFilter[0] : null;
  const projectPert = useProjectPert();
  const featurePert = useFeaturePert(singleFeatureId);

  const pertQuery = singleFeatureId ? featurePert : projectPert;
  const { data: pertData, isLoading, error } = pertQuery;

  const handleNodeClick = (featureId: string, taskId: string) => {
    navigate("/board?feature=" + featureId + "&task=" + taskId);
  };

  return (
    <div style={{ padding: 16, height: "100vh", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>
          <ApartmentOutlined style={{ marginRight: 8 }} />
          PERT Chart
        </Title>
      </div>

      <PertFilters
        features={features}
        featureFilter={featureFilter}
        onFeatureFilterChange={setFeatureFilter}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        direction={direction}
        onDirectionChange={setDirection}
      />

      {isLoading && (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Spin size="large" />
        </div>
      )}

      {error && (
        <Alert
          type="error"
          message="Failed to load PERT data"
          description={String(error)}
          style={{ marginBottom: 12 }}
        />
      )}

      {pertData && (
        <>
          <div style={{ flex: 1, minHeight: 0 }}>
            <PertChart
              data={pertData}
              direction={direction}
              featureFilter={featureFilter}
              statusFilter={statusFilter}
              onNodeClick={handleNodeClick}
            />
          </div>

          <Card size="small" style={{ marginTop: 12, flexShrink: 0 }}>
            <Space size="large" wrap>
              <Statistic
                title="Total Tasks"
                value={pertData.total_tasks}
                prefix={<NodeIndexOutlined />}
              />
              <Statistic
                title="Completed"
                value={pertData.completed_count}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: "#389e0d" }}
              />
              <Statistic
                title="Blocked"
                value={pertData.blocked_count}
                prefix={<StopOutlined />}
                valueStyle={{ color: "#ff4d4f" }}
              />
              {pertData.critical_path && (
                <>
                  <Statistic
                    title="Critical Chain Length"
                    value={pertData.critical_path.chain_length}
                    valueStyle={{ color: "#fa541c" }}
                  />
                  <Statistic
                    title="Stages Remaining"
                    value={pertData.critical_path.stages_remaining}
                    valueStyle={{ color: "#fa541c" }}
                  />
                </>
              )}
            </Space>
          </Card>
        </>
      )}
    </div>
  );
}

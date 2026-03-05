/** PERT chart visualization using ReactFlow and dagre layout. */

import { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node as RFNode,
  type Edge as RFEdge,
  type NodeMouseHandler,
  MarkerType,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import type { PertData, PertNode } from "../../types/pert";

/* -- Stage color palette -- */

const STAGE_COLORS: Record<string, string> = {
  backlog: "#8c8c8c",
  spec: "#1677ff",
  design: "#722ed1",
  implement: "#13c2c2",
  code_review: "#faad14",
  test: "#52c41a",
  docs: "#eb2f96",
  done: "#389e0d",
};

function stageColor(stageId: string): string {
  return STAGE_COLORS[stageId] ?? "#595959";
}

/* -- Node dimensions for dagre -- */

const NODE_WIDTH = 200;
const NODE_HEIGHT = 60;

/* -- Dagre layout helper -- */

interface LayoutInput {
  nodes: PertNode[];
  edges: PertData["edges"];
  direction: "LR" | "TB";
  criticalTaskIds: Set<string>;
}

interface LayoutOutput {
  rfNodes: RFNode[];
  rfEdges: RFEdge[];
}

function layoutGraph({ nodes, edges, direction, criticalTaskIds }: LayoutInput): LayoutOutput {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: direction,
    nodesep: 50,
    ranksep: 80,
    marginx: 20,
    marginy: 20,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const isHorizontal = direction === "LR";

  const rfNodes: RFNode[] = nodes.map((node) => {
    const pos = g.node(node.id);
    const isCritical = criticalTaskIds.has(node.id);

    let background = stageColor(node.stage_id);
    let borderStyle = "2px solid";
    let borderColor = stageColor(node.stage_id);
    let opacity = 1;

    if (node.is_completed) {
      opacity = 0.55;
      background = stageColor(node.stage_id);
    } else if (node.is_blocked) {
      borderStyle = "2px dashed";
      borderColor = "#ff4d4f";
      background = "#fff1f0";
    } else if (node.execution_status === "running") {
      borderColor = "#1677ff";
      borderStyle = "3px solid";
      background = "#e6f4ff";
    } else if (node.execution_status === "queued") {
      background = "#fffbe6";
      borderColor = "#faad14";
    } else {
      background = "#f6ffed";
      borderColor = stageColor(node.stage_id);
    }

    if (isCritical && !node.is_completed) {
      borderColor = "#fa541c";
      borderStyle = "3px solid";
    }

    return {
      id: node.id,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      data: {
        label: node.title.length > 28 ? node.title.slice(0, 26) + "..." : node.title,
        featureId: node.feature_id,
        stageId: node.stage_id,
        isBlocked: node.is_blocked,
        isCompleted: node.is_completed,
        executionStatus: node.execution_status,
      },
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      style: {
        background,
        border: borderStyle + " " + borderColor,
        borderRadius: 8,
        padding: "6px 10px",
        fontSize: "var(--pct-fs-base)",
        fontWeight: 500,
        width: NODE_WIDTH,
        opacity,
        color: node.is_completed ? "var(--pct-color-text-secondary)" : "var(--pct-color-text)",
      },
    };
  });

  const rfEdges: RFEdge[] = edges.map((edge, i) => {
    const isCritical =
      edge.edge_type === "blocked_by" &&
      criticalTaskIds.has(edge.source) &&
      criticalTaskIds.has(edge.target);

    return {
      id: "e-" + i + "-" + edge.source + "-" + edge.target,
      source: edge.source,
      target: edge.target,
      type: "default",
      animated: edge.edge_type === "cross_ref",
      style: {
        stroke: isCritical ? "#fa541c" : edge.edge_type === "blocked_by" ? "#595959" : "#bfbfbf",
        strokeWidth: isCritical ? 3 : edge.edge_type === "blocked_by" ? 2 : 1,
        strokeDasharray: edge.edge_type === "cross_ref" ? "6 3" : undefined,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: isCritical ? "#fa541c" : edge.edge_type === "blocked_by" ? "#595959" : "#bfbfbf",
      },
      label: edge.edge_type === "cross_ref" ? "ref" : undefined,
      labelStyle: { fontSize: "var(--pct-fs-xs)", fill: "#8c8c8c" },
    };
  });

  return { rfNodes, rfEdges };
}

/* -- Component -- */

interface PertChartProps {
  data: PertData;
  direction: "LR" | "TB";
  featureFilter: string[];
  statusFilter: string[];
  onNodeClick?: (featureId: string, taskId: string) => void;
}

export default function PertChart({
  data,
  direction,
  featureFilter,
  statusFilter,
  onNodeClick,
}: PertChartProps) {
  const criticalTaskIds = useMemo(() => {
    return new Set(data.critical_path?.task_ids ?? []);
  }, [data.critical_path]);

  const filteredNodes = useMemo(() => {
    let nodes = data.nodes;

    if (featureFilter.length > 0) {
      nodes = nodes.filter((n) => featureFilter.includes(n.feature_id));
    }

    if (statusFilter.length > 0) {
      nodes = nodes.filter((n) => {
        if (statusFilter.includes("completed") && n.is_completed) return true;
        if (statusFilter.includes("blocked") && n.is_blocked && !n.is_completed) return true;
        if (
          statusFilter.includes("in-progress") &&
          !n.is_completed &&
          !n.is_blocked &&
          (n.execution_status === "running" || n.execution_status === "queued")
        )
          return true;
        if (
          statusFilter.includes("eligible") &&
          !n.is_completed &&
          !n.is_blocked &&
          n.execution_status !== "running" &&
          n.execution_status !== "queued"
        )
          return true;
        return false;
      });
    }

    return nodes;
  }, [data.nodes, featureFilter, statusFilter]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return data.edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
  }, [data.edges, filteredNodes]);

  const { rfNodes, rfEdges } = useMemo(
    () =>
      layoutGraph({
        nodes: filteredNodes,
        edges: filteredEdges,
        direction,
        criticalTaskIds,
      }),
    [filteredNodes, filteredEdges, direction, criticalTaskIds],
  );

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      const featureId = node.data.featureId as string;
      const parts = node.id.split("#");
      const taskId = parts.length > 1 ? parts[1] : node.id;
      onNodeClick?.(featureId, taskId);
    },
    [onNodeClick],
  );

  if (filteredNodes.length === 0) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--pct-color-text-muted)" }}>
        No tasks to display. Adjust filters or create tasks first.
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} />
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          pannable
          zoomable
          style={{ background: "var(--pct-color-bg-light)" }}
        />
      </ReactFlow>
    </div>
  );
}

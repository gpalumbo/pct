import { Tabs, Typography } from 'antd';
import {
  FlagOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import TrainingDataTab from '../components/training/TrainingDataTab';
import DatasetsTab from '../components/training/DatasetsTab';
import TrainingTab from '../components/training/TrainingTab';
import EvaluationTab from '../components/training/EvaluationTab';
import PromptTemplatesTab from '../components/training/PromptTemplatesTab';

const { Title } = Typography;

const tabItems = [
  {
    key: 'data',
    label: 'Training Data',
    icon: <FlagOutlined />,
    children: <TrainingDataTab />,
  },
  {
    key: 'datasets',
    label: 'Datasets',
    icon: <DatabaseOutlined />,
    children: <DatasetsTab />,
  },
  {
    key: 'training',
    label: 'Training',
    icon: <ExperimentOutlined />,
    children: <TrainingTab />,
  },
  {
    key: 'evaluation',
    label: 'Evaluation',
    icon: <LineChartOutlined />,
    children: <EvaluationTab />,
  },
  {
    key: 'templates',
    label: 'Prompt Templates',
    icon: <FileTextOutlined />,
    children: <PromptTemplatesTab />,
  },
];

export default function TrainingPage() {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 16 }}>
        Training & Feedback
      </Title>
      <Tabs
        tabPosition="left"
        items={tabItems}
        style={{ minHeight: 'calc(100vh - 120px)' }}
      />
    </div>
  );
}

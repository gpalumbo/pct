import { Typography, Empty } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

export default function EvaluationTab() {
  return (
    <div>
      <Title level={5}>A/B Evaluation</Title>
      <Empty
        image={<ExperimentOutlined style={{ fontSize: 48, color: 'var(--pct-color-text-disabled)' }} />}
        description={
          <>
            <Paragraph type="secondary">
              Evaluation sessions will appear here after training completes.
            </Paragraph>
            <Paragraph type="secondary" className="pct-text-base">
              You will be able to compare base model responses with LoRA-enhanced
              responses in a blind A/B test.
            </Paragraph>
          </>
        }
      />
    </div>
  );
}

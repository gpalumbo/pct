import { Modal, Typography } from 'antd';
import { useBoardStore } from '../../stores/boardStore';
import { useMoveTask } from '../../hooks/useBoardQueries';

const { Text } = Typography;

export default function StageSkipModal() {
  const pendingMove = useBoardStore((s) => s.pendingMove);
  const setPendingMove = useBoardStore((s) => s.setPendingMove);
  const moveTask = useMoveTask();

  const handleConfirm = () => {
    if (!pendingMove) return;
    moveTask.mutate(
      {
        featureId: pendingMove.featureId,
        taskId: pendingMove.taskId,
        data: { new_status: pendingMove.newStatus, confirm_skip: true },
      },
      { onSettled: () => setPendingMove(null) },
    );
  };

  return (
    <Modal
      title="Confirm Stage Skip"
      open={pendingMove !== null}
      onOk={handleConfirm}
      onCancel={() => setPendingMove(null)}
      okText="Confirm Skip"
      confirmLoading={moveTask.isPending}
    >
      {pendingMove && (
        <Text>
          Move this task to <Text strong>{pendingMove.newStatus}</Text>? This skips one
          or more intermediate stages.
        </Text>
      )}
    </Modal>
  );
}

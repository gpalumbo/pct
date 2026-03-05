import { Modal, Spin, Empty } from 'antd';
import { useFeatureImages } from '../../hooks/useImageGenQueries';
import type { FeatureImage } from '../../api/imagegenApi';
import { getImageUrl } from '../../api/imagegenApi';
import './sidebar.css';

interface ImagePickerModalProps {
  open: boolean;
  featureId: string;
  onSelect: (image: FeatureImage) => void;
  onCancel: () => void;
}

export default function ImagePickerModal({ open, featureId, onSelect, onCancel }: ImagePickerModalProps) {
  const { data: images, isLoading } = useFeatureImages(featureId);

  return (
    <Modal title="Insert Image" open={open} onCancel={onCancel} footer={null} width={600}>
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : !images?.length ? (
        <Empty description="No images found in this feature" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className="imagegen-grid" style={{ maxHeight: 400, overflowY: 'auto' }}>
          {images.map((img) => (
            <div
              key={`${img.task_id}-${img.id}`}
              className="imagegen-grid-item"
              onClick={() => onSelect(img)}
            >
              <img
                src={getImageUrl(img.feature_id, img.task_id, img.id)}
                alt={img.filename}
              />
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

import { useCallback } from 'react';
import { Button, Modal, Space, Typography } from 'antd';
import { LeftOutlined, RightOutlined, EditOutlined, CheckOutlined } from '@ant-design/icons';
import type { GeneratedImage } from '../../api/imagegenApi';

const { Text } = Typography;

interface ImageGalleryModalProps {
  open: boolean;
  images: GeneratedImage[];
  imageUrls: Record<string, string>;
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onClose: () => void;
  onRefine?: (image: GeneratedImage) => void;
  onAccept?: (image: GeneratedImage) => void;
}

export default function ImageGalleryModal({
  open,
  images,
  imageUrls,
  currentIndex,
  onIndexChange,
  onClose,
  onRefine,
  onAccept,
}: ImageGalleryModalProps) {
  const current = images[currentIndex];
  const url = current ? imageUrls[current.filename] : undefined;

  const handlePrev = useCallback(() => {
    if (currentIndex > 0) onIndexChange(currentIndex - 1);
  }, [currentIndex, onIndexChange]);

  const handleNext = useCallback(() => {
    if (currentIndex < images.length - 1) onIndexChange(currentIndex + 1);
  }, [currentIndex, images.length, onIndexChange]);

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width="80vw"
      styles={{ body: { height: '80vh', display: 'flex', flexDirection: 'column', padding: 0 } }}
      centered
      destroyOnClose
    >
      {current && (
        <>
          {/* Image display */}
          <div style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden',
            background: '#1a1a1a',
            minHeight: 0,
          }}>
            {/* Left nav */}
            {currentIndex > 0 && (
              <Button
                shape="circle"
                icon={<LeftOutlined />}
                onClick={handlePrev}
                style={{ position: 'absolute', left: 12, zIndex: 1, opacity: 0.8 }}
              />
            )}

            {url ? (
              <img
                src={url}
                alt={`Image ${current.index + 1}`}
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
              />
            ) : (
              <Text type="secondary">Loading...</Text>
            )}

            {/* Right nav */}
            {currentIndex < images.length - 1 && (
              <Button
                shape="circle"
                icon={<RightOutlined />}
                onClick={handleNext}
                style={{ position: 'absolute', right: 12, zIndex: 1, opacity: 0.8 }}
              />
            )}
          </div>

          {/* Bottom bar: info + actions */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px',
            borderTop: '1px solid #303030',
            background: '#1a1a1a',
            flexShrink: 0,
          }}>
            <Space>
              <Text style={{ color: '#aaa', fontSize: 12 }}>
                {currentIndex + 1} / {images.length}
              </Text>
              <Text style={{ color: '#aaa', fontSize: 12 }}>
                Seed: {current.seed} &middot; Round {current.round} &middot; #{current.index + 1}
              </Text>
            </Space>
            <Space>
              {onRefine && (
                <Button
                  icon={<EditOutlined />}
                  onClick={() => onRefine(current)}
                >
                  Refine
                </Button>
              )}
              {onAccept && (
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={() => onAccept(current)}
                >
                  Accept
                </Button>
              )}
            </Space>
          </div>
        </>
      )}
    </Modal>
  );
}

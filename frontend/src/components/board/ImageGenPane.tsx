import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Collapse, Input, Progress, Slider, Typography, message } from 'antd';
import { CheckOutlined } from '@ant-design/icons';
import {
  useImageGenSession,
  useJobStatus,
  useStartGeneration,
  useSelectImage,
} from '../../hooks/useImageGenQueries';
import { fetchImageBlob } from '../../api/imagegenApi';
import type { GeneratedImage, GenerationRound } from '../../api/imagegenApi';
import './sidebar.css';

const { Text } = Typography;

interface ImageGenPaneProps {
  featureId: string;
  taskId: string;
  taskTitle?: string;
  pendingPrompt?: string | null;
  onPromptConsumed?: () => void;
}

const divergenceMarks = {
  0.1: 'Close',
  0.5: 'Balanced',
  0.9: 'Diverge',
};

export default function ImageGenPane({
  featureId,
  taskId,
  pendingPrompt,
  onPromptConsumed,
}: ImageGenPaneProps) {
  const { data: session, refetch: refetchSession } = useImageGenSession(featureId, taskId);
  const startGen = useStartGeneration();
  const selectImg = useSelectImage(featureId, taskId);

  const [negativePrompt, setNegativePrompt] = useState('');
  const [divergence, setDivergence] = useState(0.5);
  const [guidanceScale, setGuidanceScale] = useState(7.5);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<{ round: number; filename: string } | null>(
    null,
  );
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({});

  const { data: job } = useJobStatus(activeJobId);

  const isGenerating = !!activeJobId && job?.status !== 'completed' && job?.status !== 'failed';
  const hasRounds = (session?.rounds.length ?? 0) > 0;

  // Find the latest round's selected image for img2img source
  const latestSelectedImage = useMemo(() => {
    if (!session?.rounds.length) return null;
    for (let i = session.rounds.length - 1; i >= 0; i--) {
      if (session.rounds[i].selected_image) {
        return session.rounds[i].selected_image;
      }
    }
    return null;
  }, [session]);

  // Load image blobs for the current round's images
  const currentImages = useMemo(() => {
    if (!job?.images.length && session?.rounds.length) {
      const lastRound = session.rounds[session.rounds.length - 1];
      return lastRound.images;
    }
    return job?.images ?? [];
  }, [job, session]);

  const loadImageBlob = useCallback(
    async (filename: string) => {
      if (imageUrls[filename]) return;
      try {
        const blob = await fetchImageBlob(featureId, taskId, filename);
        const url = URL.createObjectURL(blob);
        setImageUrls((prev) => ({ ...prev, [filename]: url }));
      } catch {
        // Image not yet available
      }
    },
    [featureId, taskId, imageUrls],
  );

  useEffect(() => {
    currentImages.forEach((img) => loadImageBlob(img.filename));
  }, [currentImages, loadImageBlob]);

  // When job completes, refresh session and clear active job
  useEffect(() => {
    if (job?.status === 'completed') {
      refetchSession();
      setActiveJobId(null);
    } else if (job?.status === 'failed') {
      message.error(job.error || 'Image generation failed');
      setActiveJobId(null);
    }
  }, [job?.status, job?.error, refetchSession]);

  // Trigger generation when an external prompt arrives via pendingPrompt
  useEffect(() => {
    if (!pendingPrompt) return;
    startGen.mutate(
      {
        feature_id: featureId,
        task_id: taskId,
        prompt: pendingPrompt.trim(),
        negative_prompt: negativePrompt.trim(),
        guidance_scale: guidanceScale,
        source_image: latestSelectedImage ?? undefined,
        divergence,
      },
      {
        onSuccess: (data) => {
          setActiveJobId(data.job_id);
          setSelectedImage(null);
        },
        onError: () => message.error('Failed to start generation'),
      },
    );
    onPromptConsumed?.();
  }, [pendingPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectImage = (img: GeneratedImage) => {
    setSelectedImage({ round: img.round, filename: img.filename });
    selectImg.mutate({ round: img.round, filename: img.filename });
  };

  const handleAccept = () => {
    if (!selectedImage) return;
    selectImg.mutate(
      { round: selectedImage.round, filename: selectedImage.filename },
      {
        onSuccess: () => message.success('Image accepted as artifact'),
        onError: () => message.error('Failed to mark image as selected'),
      },
    );
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: '8px 12px',
        gap: 8,
        overflow: 'auto',
      }}
    >
      <Collapse
        size="small"
        ghost
        items={[
          {
            key: 'neg',
            label: (
              <Text type="secondary" style={{ fontSize: 11 }}>
                Negative prompt
              </Text>
            ),
            children: (
              <Input.TextArea
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="Things to avoid..."
                autoSize={{ minRows: 1, maxRows: 3 }}
                style={{ fontSize: 12 }}
                disabled={isGenerating}
              />
            ),
          },
        ]}
      />

      {/* Parameters */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        {hasRounds && (
          <div style={{ flex: 1 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Divergence
            </Text>
            <Slider
              min={0.1}
              max={0.9}
              step={0.1}
              value={divergence}
              onChange={setDivergence}
              marks={divergenceMarks}
              disabled={isGenerating}
            />
          </div>
        )}
        <div style={{ width: 80 }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            Guidance
          </Text>
          <Input
            size="small"
            type="number"
            value={guidanceScale}
            onChange={(e) => setGuidanceScale(parseFloat(e.target.value) || 7.5)}
            disabled={isGenerating}
          />
        </div>
      </div>

      {/* Progress bar */}
      {isGenerating && job && (
        <Progress percent={Math.round(job.progress * 100)} size="small" status="active" />
      )}

      {/* Image grid — 2x2 */}
      {currentImages.length > 0 && (
        <div className="imagegen-grid">
          {currentImages.map((img) => {
            const url = imageUrls[img.filename];
            const isSelected = selectedImage?.filename === img.filename;
            return (
              <div
                key={img.filename}
                className={`imagegen-grid-item${isSelected ? ' selected' : ''}`}
                onClick={() => handleSelectImage(img)}
              >
                {url ? (
                  <img src={url} alt={`Generated ${img.index + 1}`} />
                ) : (
                  <div className="imagegen-placeholder">Loading...</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Accept button */}
      {selectedImage && !isGenerating && (
        <Button icon={<CheckOutlined />} onClick={handleAccept} block>
          Accept Selected Image
        </Button>
      )}

      {/* Round history */}
      {session && session.rounds.length > 1 && (
        <Collapse
          size="small"
          ghost
          items={session.rounds
            .slice(0, -1)
            .reverse()
            .map((round: GenerationRound) => ({
              key: round.round,
              label: (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  Round {round.round} — {round.prompt.slice(0, 40)}
                  {round.prompt.length > 40 ? '...' : ''}
                </Text>
              ),
              children: (
                <div className="imagegen-grid imagegen-grid-small">
                  {round.images.map((img) => {
                    const url = imageUrls[img.filename];
                    return (
                      <div
                        key={img.filename}
                        className={`imagegen-grid-item${round.selected_image === img.filename ? ' selected' : ''}`}
                      >
                        {url ? (
                          <img
                            src={url}
                            alt={`Round ${round.round} img ${img.index + 1}`}
                            onLoad={() => {}} // already loaded
                          />
                        ) : (
                          <div
                            className="imagegen-placeholder"
                            ref={() => loadImageBlob(img.filename)}
                          >
                            ...
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ),
            }))}
        />
      )}
    </div>
  );
}

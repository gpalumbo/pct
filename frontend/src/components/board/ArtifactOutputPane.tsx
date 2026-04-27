import { useEffect, useRef, useState } from 'react';
import { Button, Checkbox, Image, Input, Modal, Select, Slider, Spin, Typography, message } from 'antd';
import {
  EditOutlined,
  ReloadOutlined,
  SaveOutlined,
  UpOutlined,
  DownOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  RetweetOutlined,
  DeleteOutlined,
  ExpandOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { useArtifact, useSaveArtifact } from '../../hooks/useBoardQueries';
import { useGenerate, useJobStatus, useActiveJob, useTaskImages, useDeleteImage, useCancelJob, useResolutions, useImagegenModels } from '../../hooks/useImageGenQueries';
import { getImageUrl, imagegenApi } from '../../api/imagegenApi';
import type { RefineTarget } from '../chat/ChatInput';
import type { AgentType } from '../../types/enums';
import ArtifactEditorModal from './ArtifactEditorModal';
import './sidebar.css';

const { Text } = Typography;

/* ------------------------------------------------------------------ */
/*  Sub-component: Text Preview                                        */
/* ------------------------------------------------------------------ */

interface TextPreviewProps {
  featureId: string;
  taskId: string;
  activeAgentType?: AgentType | null;
}

function TextPreview({ featureId, taskId, activeAgentType }: TextPreviewProps) {
  const { data: artifact, isLoading, refetch } = useArtifact(featureId, taskId);
  const saveMutation = useSaveArtifact();
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (artifact) {
      setContent(artifact.content);
      setDirty(false);
    }
  }, [artifact]);

  // Auto-collapse when image_gen agent is active
  useEffect(() => {
    if (activeAgentType === 'image_gen') {
      setCollapsed(true);
    } else if (activeAgentType) {
      setCollapsed(false);
    }
  }, [activeAgentType]);

  const handleSave = () => {
    saveMutation.mutate(
      { featureId, taskId, content },
      {
        onSuccess: () => {
          setDirty(false);
          message.success('Artifact saved');
        },
        onError: () => message.error('Failed to save artifact'),
      },
    );
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 12 }}>
        <Spin size="small" />
      </div>
    );
  }

  return (
    <div className="artifact-output-text-section">
      {/* Toolbar */}
      <div className="artifact-output-section-header" onClick={() => setCollapsed(!collapsed)}>
        <Text
          type="secondary"
          className="pct-meta-text"
          style={{ fontWeight: 500, flex: 1, cursor: 'pointer' }}
        >
          {collapsed ? (
            <DownOutlined className="pct-text-2xs" style={{ marginRight: 4 }} />
          ) : (
            <UpOutlined className="pct-text-2xs" style={{ marginRight: 4 }} />
          )}
          Text Artifact
        </Text>
        <div onClick={(e) => e.stopPropagation()} style={{ display: 'flex', gap: 4 }}>
          <Button size="small" icon={<EditOutlined />} onClick={() => setEditorOpen(true)} />
          <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()} />
          <Button
            size="small"
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            disabled={!dirty}
            loading={saveMutation.isPending}
          >
            Save
          </Button>
        </div>
      </div>

      {!collapsed && (
        <div className="artifact-output-text-body">
          {content ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : (
            <Text type="secondary" className="pct-text-base">
              {artifact
                ? '(empty)'
                : 'Artifact file does not exist yet. Use "Copy to artifact" or the editor to create it.'}
            </Text>
          )}
        </div>
      )}

      <ArtifactEditorModal
        open={editorOpen}
        content={content}
        featureId={featureId}
        taskId={taskId}
        onSave={(md) => {
          setContent(md);
          setDirty(true);
          setEditorOpen(false);
        }}
        onCancel={() => setEditorOpen(false)}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Image Section                                       */
/* ------------------------------------------------------------------ */

interface ImageSectionProps {
  featureId: string;
  taskId: string;
  activeAgentType: AgentType | null;
  pendingImagePrompt: string | null;
  pendingSourceImageId?: string | null;
  onPromptConsumed: () => void;
  onRefine?: (target: RefineTarget) => void;
}

function ImageSection({
  featureId,
  taskId,
  activeAgentType,
  pendingImagePrompt,
  pendingSourceImageId,
  onPromptConsumed,
  onRefine,
}: ImageSectionProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [negativePrompt, setNegativePrompt] = useState('');
  const [guidanceScale, setGuidanceScale] = useState(7.5);
  const [numImages, setNumImages] = useState(4);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewCurrent, setPreviewCurrent] = useState(0);
  const [resolution, setResolution] = useState({ width: 1024, height: 1024 });
  const [selectedModelId, setSelectedModelId] = useState<string | undefined>(undefined);
  const [draft, setDraft] = useState(false);

  const generateMutation = useGenerate();
  const { data: models } = useImagegenModels();
  const selectedModel = models?.find((m) => m.id === selectedModelId) ?? models?.[0];
  const { data: resolutions } = useResolutions(
    selectedModel?.architecture || undefined,
    selectedModel?.native_resolution || undefined,
  );
  const { data: jobStatus } = useJobStatus(activeJobId);
  const { data: taskImages, refetch: refetchTaskImages } = useTaskImages(featureId, taskId);
  const deleteMutation = useDeleteImage();
  const cancelMutation = useCancelJob();

  // Recover active job on mount (reconnect after navigation)
  const { data: recoveredJob } = useActiveJob(featureId, taskId);
  useEffect(() => {
    if (recoveredJob && !activeJobId) {
      setActiveJobId(recoveredJob.job_id);
    }
  }, [recoveredJob, activeJobId]);

  // Track previous pendingImagePrompt to detect new arrivals
  const prevPromptRef = useRef<string | null>(null);

  // When a new pendingImagePrompt arrives, fire the generate API
  useEffect(() => {
    if (!pendingImagePrompt || pendingImagePrompt === prevPromptRef.current) return;
    prevPromptRef.current = pendingImagePrompt;

    generateMutation.mutate(
      {
        feature_id: featureId,
        task_id: taskId,
        prompt: pendingImagePrompt,
        negative_prompt: negativePrompt || undefined,
        guidance_scale: guidanceScale,
        num_images: numImages,
        source_image_id: pendingSourceImageId || undefined,
        width: resolution.width,
        height: resolution.height,
        model_id: selectedModel?.id,
        draft,
      },
      {
        onSuccess: (data) => {
          setActiveJobId(data.job_id);
          onPromptConsumed();
        },
        onError: () => {
          message.error('Failed to submit image generation');
          onPromptConsumed();
        },
      },
    );
  }, [pendingImagePrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  // Refresh historical images when job completes
  useEffect(() => {
    if (jobStatus?.status === 'completed') {
      refetchTaskImages();
    }
  }, [jobStatus?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const isJobRunning =
    activeJobId &&
    jobStatus &&
    (jobStatus.status === 'pending' ||
      jobStatus.status === 'loading' ||
      jobStatus.status === 'running');
  const isJobCompleted = jobStatus?.status === 'completed';
  const isJobFailed = jobStatus?.status === 'failed';

  // Progressive images from the running job
  const progressiveImages = isJobRunning && jobStatus.images ? jobStatus.images : [];

  const handleSelect = (imageId: string) => {
    setSelectedImageId(imageId);
    imagegenApi.selectImage(featureId, taskId, imageId);
  };

  const handleDelete = (imageId: string) => {
    Modal.confirm({
      title: 'Delete image?',
      content: 'This will permanently remove the image from disk.',
      okText: 'Delete',
      okType: 'danger',
      onOk: () => {
        deleteMutation.mutate(
          { featureId, taskId, imageId },
          {
            onSuccess: () => {
              if (selectedImageId === imageId) setSelectedImageId(null);
              message.success('Image deleted');
            },
          },
        );
      },
    });
  };

  const handleCancel = () => {
    if (activeJobId) {
      cancelMutation.mutate(activeJobId);
    }
  };

  const handleRefine = (imageId: string) => {
    onRefine?.({
      filename: imageId,
      imageUrl: getImageUrl(featureId, taskId, imageId),
    });
  };

  // Midpoint preview from SSE
  const preview = isJobRunning ? jobStatus.preview : undefined;

  // Merge: show progressive images while running, otherwise show historical
  const displayImages =
    progressiveImages.length > 0
      ? progressiveImages.map((img: { id?: string; image_id?: string }, idx: number) => ({
          id: img.id || img.image_id || `prog-${idx}`,
          isProgressive: true,
          isPreview: false,
        }))
      : (taskImages || []).map((img) => ({ id: img.id, isProgressive: false, isPreview: false }));

  // Append midpoint preview as a placeholder if we have one and job is running
  if (preview && isJobRunning) {
    displayImages.push({
      id: `${preview.preview_id}_preview`,
      isProgressive: true,
      isPreview: true,
    });
  }

  return (
    <div className="artifact-output-image-section">
      <div className="artifact-output-section-header" onClick={() => setCollapsed(!collapsed)}>
        <Text
          type="secondary"
          className="pct-meta-text"
          style={{ fontWeight: 500, flex: 1, cursor: 'pointer' }}
        >
          {collapsed ? (
            <DownOutlined className="pct-text-2xs" style={{ marginRight: 4 }} />
          ) : (
            <UpOutlined className="pct-text-2xs" style={{ marginRight: 4 }} />
          )}
          Images
          {taskImages && taskImages.length > 0 && (
            <span style={{ opacity: 0.6, marginLeft: 4 }}>({taskImages.length})</span>
          )}
        </Text>
        {isJobRunning && <LoadingOutlined style={{ fontSize: 12 }} />}
        {isJobCompleted && <CheckCircleOutlined style={{ fontSize: 12, color: '#52c41a' }} />}
        {isJobFailed && <CloseCircleOutlined style={{ fontSize: 12, color: '#ff4d4f' }} />}
      </div>

      {!collapsed && (
        <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Controls — only show when image_gen agent is active */}
          {activeAgentType === 'image_gen' && (
            <>
              {/* Model selector — only when multiple models available */}
              {models && models.length > 1 && (
                <div>
                  <Text type="secondary" className="pct-text-xs" style={{ display: 'block', marginBottom: 2 }}>
                    Model
                  </Text>
                  <Select
                    size="small"
                    style={{ width: '100%' }}
                    value={selectedModel?.id}
                    onChange={(val) => setSelectedModelId(val)}
                    options={models.map((m) => ({
                      label: `${m.name}${m.architecture ? ` (${m.architecture})` : ''}`,
                      value: m.id,
                    }))}
                  />
                </div>
              )}

              {/* Negative prompt */}
              <div>
                <Text type="secondary" className="pct-text-xs" style={{ display: 'block', marginBottom: 2 }}>
                  Negative prompt
                </Text>
                <Input.TextArea
                  size="small"
                  rows={2}
                  placeholder="Things to avoid..."
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                />
              </div>

              {/* Guidance scale + Image count */}
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" className="pct-text-xs">
                    Guidance: {guidanceScale}
                  </Text>
                  <Slider
                    min={1}
                    max={20}
                    step={0.5}
                    value={guidanceScale}
                    onChange={setGuidanceScale}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" className="pct-text-xs">
                    Images: {numImages}
                  </Text>
                  <Slider min={1} max={6} step={1} value={numImages} onChange={setNumImages} />
                </div>
              </div>

              {/* Draft mode */}
              <Checkbox checked={draft} onChange={(e) => setDraft(e.target.checked)}>
                <Text type="secondary" className="pct-text-xs">
                  Draft (half res, 10 steps)
                </Text>
              </Checkbox>

              {/* Resolution preset */}
              <div>
                <Text type="secondary" className="pct-text-xs" style={{ display: 'block', marginBottom: 2 }}>
                  Resolution
                </Text>
                <Select
                  size="small"
                  style={{ width: '100%' }}
                  value={`${resolution.width}x${resolution.height}`}
                  onChange={(val) => {
                    const [w, h] = val.split('x').map(Number);
                    setResolution({ width: w, height: h });
                  }}
                  options={(resolutions || []).map((r) => ({
                    label: `${r.label} (${r.width}\u00d7${r.height})`,
                    value: `${r.width}x${r.height}`,
                  }))}
                />
              </div>
            </>
          )}

          {/* Job status */}
          {generateMutation.isPending && (
            <Text type="secondary" className="pct-text-sm">
              <LoadingOutlined style={{ marginRight: 4 }} />
              Submitting...
            </Text>
          )}
          {isJobRunning && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text type="secondary" className="pct-text-sm" style={{ flex: 1 }}>
                <LoadingOutlined style={{ marginRight: 4 }} />
                {jobStatus.status === 'loading'
                  ? (jobStatus.status_message || 'Loading model...')
                  : `Generating... (${progressiveImages.length}/${numImages})`}
              </Text>
              <Button
                size="small"
                danger
                onClick={handleCancel}
                loading={cancelMutation.isPending}
              >
                Cancel
              </Button>
            </div>
          )}
          {isJobFailed && (
            <Text type="danger" className="pct-text-sm">
              {jobStatus?.error === 'Cancelled'
                ? 'Generation cancelled'
                : `Generation failed: ${jobStatus?.error || 'Unknown error'}`}
            </Text>
          )}

          {/* Image grid */}
          {displayImages.length > 0 && (
            <Image.PreviewGroup
              items={displayImages.filter(i => !i.isPreview).map(({ id: imgId }) => getImageUrl(featureId, taskId, imgId))}
              preview={{
                visible: previewOpen,
                current: previewCurrent,
                onVisibleChange: (v) => setPreviewOpen(v),
                onChange: (cur) => setPreviewCurrent(cur),
              }}
            >
              <div className="imagegen-grid">
                {displayImages.map(({ id: imageId, isPreview: isPreviewItem }, idx) => (
                  <div
                    key={imageId}
                    className={`imagegen-grid-item${selectedImageId === imageId ? ' selected' : ''}${isPreviewItem ? ' imagegen-grid-item--preview' : ''}`}
                    onClick={() => !isPreviewItem && handleSelect(imageId)}
                  >
                    <Image
                      src={getImageUrl(featureId, taskId, imageId)}
                      alt={imageId}
                      preview={{ visible: false, mask: false }}
                    />
                    {!isPreviewItem && selectedImageId === imageId && (
                      <CheckCircleOutlined className="imagegen-selected-badge" />
                    )}
                    {!isPreviewItem && <div className="imagegen-grid-overlay">
                      <Button
                        size="small"
                        icon={<ExpandOutlined />}
                        title="Full size"
                        onClick={(e) => {
                          e.stopPropagation();
                          setPreviewOpen(true);
                          setPreviewCurrent(idx);
                        }}
                      />
                      <Button
                        size="small"
                        icon={<RetweetOutlined />}
                        title="Refine"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRefine(imageId);
                        }}
                      />
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        title="Delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(imageId);
                        }}
                      />
                    </div>}
                  </div>
                ))}
              </div>
            </Image.PreviewGroup>
          )}

          {/* Idle state — only when no images exist and no job running */}
          {displayImages.length === 0 && !activeJobId && !generateMutation.isPending && (
            <Text type="secondary" className="pct-text-sm">
              {activeAgentType === 'image_gen'
                ? 'Send a prompt to generate images.'
                : 'No images generated yet.'}
            </Text>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main: ArtifactOutputPane                                           */
/* ------------------------------------------------------------------ */

interface ArtifactOutputPaneProps {
  featureId: string;
  taskId: string;
  activeAgentType: AgentType | null;
  pendingImagePrompt: string | null;
  pendingSourceImageId?: string | null;
  onPromptConsumed: () => void;
  onRefine?: (target: RefineTarget) => void;
}

export default function ArtifactOutputPane({
  featureId,
  taskId,
  activeAgentType,
  pendingImagePrompt,
  pendingSourceImageId,
  onPromptConsumed,
  onRefine,
}: ArtifactOutputPaneProps) {
  return (
    <div className="artifact-output-pane">
      <TextPreview featureId={featureId} taskId={taskId} activeAgentType={activeAgentType} />
      <ImageSection
        featureId={featureId}
        taskId={taskId}
        activeAgentType={activeAgentType}
        pendingImagePrompt={pendingImagePrompt}
        pendingSourceImageId={pendingSourceImageId}
        onPromptConsumed={onPromptConsumed}
        onRefine={onRefine}
      />
    </div>
  );
}

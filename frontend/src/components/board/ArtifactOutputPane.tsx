import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Collapse, Input, Progress, Slider, Spin, Tag, Typography, message } from 'antd';
import {
  CheckOutlined,
  EditOutlined,
  EyeOutlined,
  ReloadOutlined,
  SaveOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { useArtifact, useSaveArtifact, useUpdateTask } from '../../hooks/useBoardQueries';
import {
  useImageGenSession,
  useJobStatus,
  useStartGeneration,
  useSelectImage,
} from '../../hooks/useImageGenQueries';
import { fetchImageBlob } from '../../api/imagegenApi';
import type { GeneratedImage, GenerationRound } from '../../api/imagegenApi';
import type { AgentType } from '../../types/config';
import ArtifactEditorModal from './ArtifactEditorModal';
import ImageGalleryModal from './ImageGalleryModal';
import './sidebar.css';

const { Text } = Typography;

/* Shared wikilink strip — same logic as ArtifactPane */
function WikilinkStrip({ text }: { text: string }) {
  const links = useMemo(() => {
    const matches: string[] = [];
    const regex = /\[\[([^[\]]+)\]\]/g;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(text)) !== null) {
      if (!matches.includes(match[1])) matches.push(match[1]);
    }
    return matches;
  }, [text]);
  if (links.length === 0) return null;
  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', padding: '4px 0', flexShrink: 0 }}>
      {links.map((link) => (
        <Tag key={link} color="blue" style={{ fontSize: 10, margin: 0, cursor: 'default' }}>
          {link}
        </Tag>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Text Preview                                        */
/* ------------------------------------------------------------------ */

interface TextPreviewProps {
  featureId: string;
  taskId: string;
  taskTitle?: string;
}

function TextPreview({ featureId, taskId, taskTitle }: TextPreviewProps) {
  const { data: artifact, isLoading, refetch } = useArtifact(featureId, taskId);
  const saveMutation = useSaveArtifact();
  const updateTask = useUpdateTask();
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [path, setPath] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (artifact) {
      setContent(artifact.content);
      setPath(artifact.path);
      setDirty(false);
    }
  }, [artifact]);

  function artifactSlug(text: string, maxWords = 3): string {
    const words = text.toLowerCase().match(/[a-z0-9]+/g) || [];
    return (words.length > maxWords ? words.slice(0, maxWords) : words).join('_') || 'untitled';
  }

  const handlePathSave = () => {
    const trimmed = path.trim();
    if (trimmed === (artifact?.path || '')) return;
    updateTask.mutate(
      { featureId, taskId, data: { artifact_path: trimmed } },
      {
        onSuccess: () => {
          refetch();
          message.success('Artifact path updated');
        },
        onError: () => message.error('Failed to update artifact path'),
      },
    );
  };

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
          style={{ fontSize: 11, fontWeight: 500, flex: 1, cursor: 'pointer' }}
        >
          {collapsed ? (
            <DownOutlined style={{ fontSize: 9, marginRight: 4 }} />
          ) : (
            <UpOutlined style={{ fontSize: 9, marginRight: 4 }} />
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
        <>
          {/* Path bar */}
          <div style={{ padding: '4px 8px', flexShrink: 0 }}>
            <Input
              size="small"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              onBlur={handlePathSave}
              onPressEnter={handlePathSave}
              placeholder={`work/${artifactSlug(featureId)}/${taskTitle ? artifactSlug(taskTitle) : 'task'}/`}
              style={{ fontSize: 11, fontFamily: 'monospace' }}
            />
          </div>

          {/* Rendered markdown */}
          <div className="artifact-output-text-body">
            {content ? (
              <ReactMarkdown>{content}</ReactMarkdown>
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {artifact?.exists
                  ? '(empty)'
                  : 'Artifact file does not exist yet. Use "Copy to artifact" or the editor to create it.'}
              </Text>
            )}
          </div>

          <div style={{ padding: '0 8px' }}>
            <WikilinkStrip text={content} />
          </div>
        </>
      )}

      <ArtifactEditorModal
        open={editorOpen}
        content={content}
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
/*  Sub-component: Image Grid                                          */
/* ------------------------------------------------------------------ */

const divergenceMarks = { 0.1: 'Close', 0.5: 'Balanced', 0.9: 'Diverge' };

interface ImageGridProps {
  featureId: string;
  taskId: string;
  activeAgentType: AgentType | null;
  /** Pending imagegen prompt from ChatInput */
  pendingImagePrompt: string | null;
  onPromptConsumed: () => void;
  /** Source image override for refine flow */
  refineSourceImage?: string | null;
  /** Called when user clicks Refine on a thumbnail */
  onRefineImage?: (image: GeneratedImage) => void;
}

function ImageGrid({
  featureId,
  taskId,
  activeAgentType,
  pendingImagePrompt,
  onPromptConsumed,
  refineSourceImage,
  onRefineImage,
}: ImageGridProps) {
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
  const [collapsed, setCollapsed] = useState(false);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [galleryIndex, setGalleryIndex] = useState(0);

  const { data: job } = useJobStatus(activeJobId);
  const isGenerating = !!activeJobId && job?.status !== 'completed' && job?.status !== 'failed';
  const hasRounds = (session?.rounds.length ?? 0) > 0;
  const showParams = activeAgentType === 'imagegen';

  const latestSelectedImage = useMemo(() => {
    if (!session?.rounds.length) return null;
    for (let i = session.rounds.length - 1; i >= 0; i--) {
      if (session.rounds[i].selected_image) return session.rounds[i].selected_image;
    }
    return null;
  }, [session]);

  const currentImages = useMemo(() => {
    if (!job?.images.length && session?.rounds.length) {
      return session.rounds[session.rounds.length - 1].images;
    }
    return job?.images ?? [];
  }, [job, session]);

  // Collect all images across all rounds for the gallery
  const allImages = useMemo(() => {
    if (!session?.rounds.length) return currentImages;
    const imgs: GeneratedImage[] = [];
    for (const round of session.rounds) {
      imgs.push(...round.images);
    }
    return imgs;
  }, [session, currentImages]);

  const loadImageBlob = useCallback(
    async (filename: string) => {
      if (imageUrls[filename]) return;
      try {
        const blob = await fetchImageBlob(featureId, taskId, filename);
        const url = URL.createObjectURL(blob);
        setImageUrls((prev) => ({ ...prev, [filename]: url }));
      } catch {
        /* not yet available */
      }
    },
    [featureId, taskId, imageUrls],
  );

  useEffect(() => {
    currentImages.forEach((img) => loadImageBlob(img.filename));
  }, [currentImages, loadImageBlob]);

  useEffect(() => {
    if (job?.status === 'completed') {
      refetchSession();
      setActiveJobId(null);
    } else if (job?.status === 'failed') {
      message.error(job.error || 'Image generation failed');
      setActiveJobId(null);
    }
  }, [job?.status, job?.error, refetchSession]);

  // Trigger generation from pending prompt
  useEffect(() => {
    if (!pendingImagePrompt) return;
    const sourceImage = refineSourceImage ?? latestSelectedImage ?? undefined;
    startGen.mutate(
      {
        feature_id: featureId,
        task_id: taskId,
        prompt: pendingImagePrompt.trim(),
        negative_prompt: negativePrompt.trim(),
        guidance_scale: guidanceScale,
        source_image: sourceImage,
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
    onPromptConsumed();
  }, [pendingImagePrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectImage = (img: GeneratedImage) => {
    setSelectedImage({ round: img.round, filename: img.filename });
    selectImg.mutate({ round: img.round, filename: img.filename });
  };

  const handleAcceptImage = (img?: GeneratedImage) => {
    const target =
      img ??
      (selectedImage ? { round: selectedImage.round, filename: selectedImage.filename } : null);
    if (!target) return;
    selectImg.mutate(
      { round: target.round, filename: target.filename },
      {
        onSuccess: () => message.success('Image accepted as artifact'),
        onError: () => message.error('Failed to mark image as selected'),
      },
    );
  };

  const handleViewImage = (img: GeneratedImage) => {
    const idx = allImages.findIndex((i) => i.filename === img.filename);
    setGalleryIndex(idx >= 0 ? idx : 0);
    setGalleryOpen(true);
  };

  const handleGalleryRefine = (img: GeneratedImage) => {
    setGalleryOpen(false);
    onRefineImage?.(img);
  };

  const handleGalleryAccept = (img: GeneratedImage) => {
    setGalleryOpen(false);
    handleAcceptImage(img);
  };

  // Nothing to show if no images and not an imagegen agent
  const hasContent = currentImages.length > 0 || showParams || isGenerating;
  if (!hasContent && !hasRounds) return null;

  return (
    <div className="artifact-output-image-section">
      {/* Section header */}
      <div className="artifact-output-section-header" onClick={() => setCollapsed(!collapsed)}>
        <Text
          type="secondary"
          style={{ fontSize: 11, fontWeight: 500, flex: 1, cursor: 'pointer' }}
        >
          {collapsed ? (
            <DownOutlined style={{ fontSize: 9, marginRight: 4 }} />
          ) : (
            <UpOutlined style={{ fontSize: 9, marginRight: 4 }} />
          )}
          Images {currentImages.length > 0 && `(${currentImages.length})`}
        </Text>
      </div>

      {!collapsed && (
        <div
          style={{
            padding: '4px 8px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            overflow: 'auto',
          }}
        >
          {/* Generation params (visible when imagegen agent active) */}
          {showParams && (
            <>
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
            </>
          )}

          {/* Progress bar */}
          {isGenerating && job && (
            <Progress percent={Math.round(job.progress * 100)} size="small" status="active" />
          )}

          {/* Image grid with hover actions */}
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
                    {/* Hover overlay */}
                    <div className="imagegen-grid-overlay">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          onRefineImage?.(img);
                        }}
                      >
                        Refine
                      </Button>
                      <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewImage(img);
                        }}
                      >
                        View
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Accept button */}
          {selectedImage && !isGenerating && (
            <Button icon={<CheckOutlined />} onClick={() => handleAcceptImage()} block>
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
                              <img src={url} alt={`Round ${round.round} img ${img.index + 1}`} />
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
      )}

      {/* Gallery modal */}
      <ImageGalleryModal
        open={galleryOpen}
        images={allImages}
        imageUrls={imageUrls}
        currentIndex={galleryIndex}
        onIndexChange={setGalleryIndex}
        onClose={() => setGalleryOpen(false)}
        onRefine={onRefineImage ? handleGalleryRefine : undefined}
        onAccept={handleGalleryAccept}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main: ArtifactOutputPane                                           */
/* ------------------------------------------------------------------ */

interface ArtifactOutputPaneProps {
  featureId: string;
  taskId: string;
  taskTitle?: string;
  activeAgentType: AgentType | null;
  pendingImagePrompt: string | null;
  onPromptConsumed: () => void;
  refineSourceImage?: string | null;
  onRefineImage?: (image: GeneratedImage) => void;
}

export default function ArtifactOutputPane({
  featureId,
  taskId,
  taskTitle,
  activeAgentType,
  pendingImagePrompt,
  onPromptConsumed,
  refineSourceImage,
  onRefineImage,
}: ArtifactOutputPaneProps) {
  return (
    <div className="artifact-output-pane">
      <TextPreview featureId={featureId} taskId={taskId} taskTitle={taskTitle} />
      <ImageGrid
        featureId={featureId}
        taskId={taskId}
        activeAgentType={activeAgentType}
        pendingImagePrompt={pendingImagePrompt}
        onPromptConsumed={onPromptConsumed}
        refineSourceImage={refineSourceImage}
        onRefineImage={onRefineImage}
      />
    </div>
  );
}

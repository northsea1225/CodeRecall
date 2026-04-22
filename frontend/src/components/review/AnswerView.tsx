import { useEffect, useState } from "react";
import { Button, Card, Space, Tag, Tooltip, Typography } from "antd";
import { useTranslation } from "react-i18next";

import MarkdownRenderer from "../common/MarkdownRenderer";
import { useAiAnalysisStream } from "../../hooks/useAiAnalysisStream";
import { useUIStore } from "../../stores/uiStore";
import type { ReviewCapability, ReviewItem, ReviewResult, ReviewReveal } from "../../types/review";
import AiAnalysisPanel from "./AiAnalysisPanel";
import DiffViewer from "./DiffViewer";
import SelfRateGroup from "./SelfRateGroup";
import VariantDrawer from "./VariantDrawer";

interface AnswerViewProps {
  capability: ReviewCapability;
  currentItem: ReviewItem;
  revealedData: ReviewReveal | null;
  submitting?: boolean;
  userAttemptMarkdown?: string;
  onOpenRawMistake: () => void;
  onSubmitRate: (value: ReviewResult) => void;
}

export default function AnswerView({
  capability,
  currentItem,
  revealedData,
  submitting = false,
  userAttemptMarkdown,
  onOpenRawMistake,
  onSubmitRate,
}: AnswerViewProps) {
  const { t } = useTranslation();
  const uiTheme = useUIStore((state) => state.theme);
  const { state, content, error, startStream, stop, retry, reset } = useAiAnalysisStream();
  const [variantOpen, setVariantOpen] = useState(false);
  const aiEnabled = capability.ai_analysis_enabled;
  const monacoTheme = uiTheme === "dark" ? "coderecall-dark" : "coderecall-light";
  const tooltipTitle = aiEnabled
    ? capability.model
      ? t("reviewComponents.modelTooltip", { model: capability.model })
      : t("reviewComponents.aiEnabled")
    : t("reviewComponents.aiDisabledTooltip");
  const hasUserAttempt = (userAttemptMarkdown ?? "").trim().length > 0;
  const diffOriginalCode = hasUserAttempt ? userAttemptMarkdown! : revealedData?.wrong_answer_markdown ?? "";
  const diffDescription = hasUserAttempt
    ? t("reviewComponents.attemptDiffDesc")
    : t("reviewComponents.diffViewerDesc");

  useEffect(() => {
    reset();
  }, [currentItem.mistake_id, reset]);

  const handleAiAnalysis = () => {
    void startStream({
      mistakeId: currentItem.mistake_id,
      model: capability.model,
    });
  };

  return (
    <>
      <Card className="panel-card review-content-card">
        <div className="page-stack">
          <div className="review-meta">
            <Space wrap>
              <Tag>{currentItem.language}</Tag>
              <Tag color="geekblue">{t("reviewComponents.difficulty", { difficulty: currentItem.difficulty })}</Tag>
              <Tag color="cyan">{currentItem.category_name}</Tag>
              {currentItem.tag_names.map((tag) => (
                <Tag key={tag}>#{tag}</Tag>
              ))}
            </Space>
          </div>

          <div className="review-markdown review-markdown--stem">
            <MarkdownRenderer>{currentItem.stem_markdown}</MarkdownRenderer>
          </div>

          <Card
            title={t("reviewComponents.codeDiff")}
            className="review-answer-card"
            extra={
              <Button type="link" onClick={onOpenRawMistake}>
                {t("reviewComponents.viewRawMistake")}
              </Button>
            }
          >
            <DiffViewer
              originalCode={diffOriginalCode}
              modifiedCode={revealedData?.correct_answer_markdown ?? ""}
              description={diffDescription}
              language={currentItem.language}
              theme={monacoTheme}
            />
          </Card>

          <Card
            title={t("reviewComponents.errorReview")}
            className="review-answer-card"
            extra={
              <Space>
                <Button onClick={() => setVariantOpen(true)}>生成变体题</Button>
                <Tooltip title={tooltipTitle}>
                  <span>
                    <Button
                      type={aiEnabled ? "primary" : "default"}
                      disabled={!aiEnabled || state === "streaming"}
                      loading={state === "streaming"}
                      onClick={handleAiAnalysis}
                    >
                      {aiEnabled ? t("reviewComponents.aiDeepAnalysisActive") : t("reviewComponents.aiDeepAnalysis")}
                    </Button>
                  </span>
                </Tooltip>
              </Space>
            }
          >
            <div className="review-markdown">
              <MarkdownRenderer>{revealedData?.error_reason_markdown ?? ""}</MarkdownRenderer>
            </div>
            <AiAnalysisPanel
              enabled={aiEnabled}
              model={capability.model}
              status={state}
              content={content}
              error={error}
              onRetry={() => void retry()}
              onStop={stop}
            />
          </Card>
        </div>
      </Card>

      <Card className="panel-card review-actions-card">
        <div className="page-stack">
          <Typography.Text className="soft-note">{t("reviewComponents.rateShortcutHint")}</Typography.Text>
          <SelfRateGroup disabled={!currentItem} loading={submitting} onSelect={onSubmitRate} />
        </div>
      </Card>
      <VariantDrawer
        mistakeId={currentItem.mistake_id}
        open={variantOpen}
        onClose={() => setVariantOpen(false)}
      />
    </>
  );
}

import { Button, Card, Result, Space, Statistic } from "antd";
import { useTranslation } from "react-i18next";

import type { ReviewSummary } from "../../types/review";
import { computeReviewAccuracy } from "./shared";

interface CompletedViewProps {
  summary: ReviewSummary;
  onBack: () => void;
  onRestart: () => void;
}

export default function CompletedView({ summary, onBack, onRestart }: CompletedViewProps) {
  const { t } = useTranslation();
  const accuracy = computeReviewAccuracy(summary);
  const durationLabel =
    summary.duration_ms < 60_000
      ? t("reviewComponents.durationSeconds", {
          count: Math.max(Math.round(summary.duration_ms / 1000), 0),
        })
      : t("reviewComponents.durationMinutes", { count: Math.round(summary.duration_ms / 60_000) });

  return (
    <Card className="panel-card">
      <Result
        status="success"
        title={t("reviewComponents.completedTitle")}
        subTitle={t("reviewComponents.completedSubtitle", { count: summary.total_count, accuracy })}
        extra={
          <Space>
            <Button onClick={onBack}>{t("common.backToDashboard")}</Button>
            <Button type="primary" onClick={onRestart}>
              {t("reviewComponents.restart")}
            </Button>
          </Space>
        }
      />
      <div className="metric-grid">
        <Card className="panel-card">
          <Statistic title={t("reviewComponents.totalQuestions")} value={summary.total_count} />
        </Card>
        <Card className="panel-card">
          <Statistic title={t("reviewComponents.accuracy")} value={accuracy} suffix="%" />
        </Card>
        <Card className="panel-card">
          <Statistic title={t("reviewComponents.duration")} value={durationLabel} />
        </Card>
      </div>
    </Card>
  );
}

import { Card, Skeleton, Statistic, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { StatsOverview } from "../../types/stats";

interface OverviewCardsProps {
  overview: StatsOverview | null;
  loading?: boolean;
}

const formatPercent = (value: number): string => `${Math.round(value * 100)}%`;

const getMasteryClassName = (accuracy: number): string => {
  if (accuracy >= 0.8) {
    return "stats-kpi-value stats-kpi-value--success";
  }
  if (accuracy < 0.6) {
    return "stats-kpi-value stats-kpi-value--warning";
  }
  return "stats-kpi-value";
};

export default function OverviewCards({ overview, loading = false }: OverviewCardsProps) {
  const { t } = useTranslation();
  const accuracy = overview?.avg_accuracy_7d ?? 0;
  const cards = [
    {
      title: t("statsComponents.totalMistakes"),
      value: overview?.total_mistakes ?? 0,
      suffix: "",
      note: t("statsComponents.activeMasteredNote", {
        active: overview?.active_mistakes ?? 0,
        mastered: overview?.mastered_count ?? 0,
      }),
      className: "stats-kpi-value",
    },
    {
      title: t("statsComponents.totalReviews"),
      value: overview?.reviewed_7d ?? 0,
      suffix: "",
      note: t("statsComponents.reviewedTodayNote", { count: overview?.reviewed_today ?? 0 }),
      className: "stats-kpi-value",
    },
    {
      title: t("statsComponents.currentStreak"),
      value: overview?.streak_days ?? 0,
      suffix: t("statsComponents.daysSuffix"),
      note: t("statsComponents.streakNote"),
      className:
        (overview?.streak_days ?? 0) >= 7 ? "stats-kpi-value stats-kpi-value--success" : "stats-kpi-value",
    },
    {
      title: t("statsComponents.averageMastery"),
      value: formatPercent(accuracy),
      suffix: "",
      note: t("statsComponents.avgEaseFactorNote", { value: (overview?.avg_ease_factor ?? 0).toFixed(2) }),
      className: getMasteryClassName(accuracy),
    },
  ];

  return (
    <div className="stats-kpi-grid">
      {cards.map((card) => (
        <Card className="panel-card stats-kpi-card" key={card.title}>
          <Typography.Text className="stats-kpi-title">{card.title}</Typography.Text>
          {loading ? (
            <Skeleton.Button active block size="large" className="stats-kpi-skeleton" />
          ) : (
            <Statistic
              className={card.className}
              value={card.value}
              suffix={card.suffix}
              valueStyle={{ color: "inherit" }}
            />
          )}
          <Typography.Text className="soft-note">{card.note}</Typography.Text>
        </Card>
      ))}
    </div>
  );
}

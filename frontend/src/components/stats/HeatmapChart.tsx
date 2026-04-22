import { Card, Skeleton, Tooltip, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { StatsHeatmap } from "../../types/stats";

interface HeatmapChartProps {
  heatmap: StatsHeatmap | null;
  loading?: boolean;
}

const formatTooltipDate = (value: string, locale: string): string =>
  new Date(`${value}T00:00:00`).toLocaleDateString(locale, {
    month: "long",
    day: "numeric",
  });

export default function HeatmapChart({ heatmap, loading = false }: HeatmapChartProps) {
  const { t, i18n } = useTranslation();

  if (loading) {
    return (
      <Card className="panel-card stats-chart-card" title={t("statsComponents.reviewHeatmap")}>
        <Skeleton.Image active className="stats-heatmap-skeleton" />
      </Card>
    );
  }

  return (
    <Card className="panel-card stats-chart-card" title={t("statsComponents.reviewHeatmap")}>
      {heatmap && heatmap.cells.length > 0 ? (
        <div className="stats-heatmap-scroll" aria-label={t("statsComponents.reviewHeatmap")}>
          <div className="stats-heatmap-grid">
            {heatmap.cells.map((cell) => (
              <Tooltip
                key={cell.date}
                title={t("statsComponents.heatmapTooltip", {
                  date: formatTooltipDate(cell.date, i18n.language),
                  count: cell.count,
                })}
                overlayInnerStyle={{
                  background: "var(--color-bg-card)",
                  color: "var(--color-text-primary)",
                }}
              >
                <span
                  className={`stats-heatmap-cell stats-heatmap-cell--level-${cell.level}`}
                  aria-label={t("statsComponents.heatmapCellAria", { date: cell.date, count: cell.count })}
                />
              </Tooltip>
            ))}
          </div>
        </div>
      ) : (
        <Typography.Text className="soft-note">{t("statsComponents.noHeatmapData")}</Typography.Text>
      )}
    </Card>
  );
}

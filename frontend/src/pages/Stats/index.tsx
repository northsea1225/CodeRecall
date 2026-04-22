import { useEffect, useState } from "react";
import { Alert, Button, Card, Empty, Layout, Select, Space, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import HeatmapChart from "../../components/stats/HeatmapChart";
import OverviewCards from "../../components/stats/OverviewCards";
import TopWeakList from "../../components/stats/TopWeakList";
import TrendChart from "../../components/stats/TrendChart";
import RadarTagChart from "../../components/stats/RadarTagChart";
import { getStatsHeatmap, getStatsOverview, getStatsTagRadar, getStatsTopWeak, getStatsTrend } from "../../services/statsService";
import type { StatsHeatmap, StatsOverview, StatsTagRadar, StatsTopWeak, StatsTrend } from "../../types/stats";

const { Content } = Layout;

interface StatsState {
  overview: StatsOverview | null;
  trend: StatsTrend | null;
  heatmap: StatsHeatmap | null;
  topWeak: StatsTopWeak | null;
  tagRadar: StatsTagRadar | null;
}

const initialStatsState: StatsState = {
  overview: null,
  trend: null,
  heatmap: null,
  topWeak: null,
  tagRadar: null,
};

const getBrowserTzOffset = (): number => -new Date().getTimezoneOffset();

const getLoadedEmptyState = ({ overview }: StatsState): boolean =>
  Boolean(
    overview &&
      overview.total_mistakes === 0 &&
      overview.active_mistakes === 0 &&
      overview.mastered_count === 0 &&
      overview.reviewed_7d === 0 &&
      overview.reviewed_today === 0 &&
      overview.streak_days === 0 &&
      overview.avg_accuracy_7d === 0,
  );

export default function StatsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [rangeDays, setRangeDays] = useState(30);
  const [reloadToken, setReloadToken] = useState(0);
  const [tzOffsetMinutes] = useState(getBrowserTzOffset);
  const [stats, setStats] = useState<StatsState>(initialStatsState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const rangeOptions = [
    { label: t("stats.range7"), value: 7 },
    { label: t("stats.range30"), value: 30 },
    { label: t("stats.range90"), value: 90 },
  ];

  useEffect(() => {
    let active = true;

    const loadStats = async () => {
      setLoading(true);
      setError(null);

      const [overviewResult, trendResult, heatmapResult, topWeakResult, tagRadarResult] = await Promise.allSettled([
        getStatsOverview({ days: rangeDays, tz_offset_minutes: tzOffsetMinutes }),
        getStatsTrend({ days: rangeDays, bucket: "day", tz_offset_minutes: tzOffsetMinutes }),
        getStatsHeatmap({ days: 364, tz_offset_minutes: tzOffsetMinutes }),
        getStatsTopWeak({ days: rangeDays, limit: 5 }),
        getStatsTagRadar(),
      ]);

      if (!active) {
        return;
      }

      setStats({
        overview: overviewResult.status === "fulfilled" ? overviewResult.value : null,
        trend: trendResult.status === "fulfilled" ? trendResult.value : null,
        heatmap: heatmapResult.status === "fulfilled" ? heatmapResult.value : null,
        topWeak: topWeakResult.status === "fulfilled" ? topWeakResult.value : null,
        tagRadar: tagRadarResult.status === "fulfilled" ? tagRadarResult.value : null,
      });

      const failed = [overviewResult, trendResult, heatmapResult, topWeakResult, tagRadarResult].some(
        (result) => result.status === "rejected",
      );
      setError(failed ? t("stats.loadFailed") : null);
      setLoading(false);
    };

    void loadStats();

    return () => {
      active = false;
    };
  }, [rangeDays, reloadToken, tzOffsetMinutes]);

  const isEmpty = !loading && !error && getLoadedEmptyState(stats);

  return (
    <Layout className="page-stack" style={{ background: "transparent" }}>
      <div className="page-title-copy">
        <div className="page-title-row">
          <div>
            <Typography.Title level={2} style={{ margin: 0 }}>
              {t("stats.title")}
            </Typography.Title>
            <p className="page-subtitle">{t("stats.subtitle")}</p>
          </div>
          <Space wrap>
            <Select
              value={rangeDays}
              style={{ minWidth: 140 }}
              options={rangeOptions}
              onChange={(value: number) => setRangeDays(value)}
            />
            <Tag color="blue">tz_offset {tzOffsetMinutes}m</Tag>
            <Button onClick={() => setReloadToken((value) => value + 1)}>{t("stats.refresh")}</Button>
          </Space>
        </div>
      </div>

      {error ? (
        <Alert
          type="error"
          showIcon
          message={t("stats.loadFailed")}
          action={<Button onClick={() => setReloadToken((value) => value + 1)}>{t("common.retry")}</Button>}
        />
      ) : null}

      <Content className="page-stack">
        <OverviewCards overview={stats.overview} loading={loading && !stats.overview} />

        {isEmpty ? (
          <Card className="panel-card">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t("stats.emptyDesc")}
            >
              <Button type="primary" onClick={() => navigate("/mistakes/new")}>
                {t("stats.emptyButton")}
              </Button>
            </Empty>
          </Card>
        ) : (
          <>
            <div className="stats-chart-grid">
              <TrendChart trend={stats.trend} loading={loading && !stats.trend} />
              <HeatmapChart heatmap={stats.heatmap} loading={loading && !stats.heatmap} />
            </div>
            <RadarTagChart radar={stats.tagRadar} loading={loading && !stats.tagRadar} />
            <TopWeakList items={stats.topWeak?.items ?? []} loading={loading && !stats.topWeak} />
          </>
        )}
      </Content>
    </Layout>
  );
}

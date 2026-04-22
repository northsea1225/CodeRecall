import { useEffect, useState } from "react";
import { Button, Card, List, Result, Skeleton, Space, Statistic, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { listMistakes } from "../../services/mistakeService";
import { getDueCount } from "../../services/reviewService";
import { useReviewStore } from "../../stores/reviewStore";
import { listCategories, listTags } from "../../services/taxonomyService";
import { useUIStore } from "../../stores/uiStore";
import type { Category, Mistake, Tag as TaxonomyTag } from "../../types/mistake";

export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const language = useUIStore((state) => state.language);
  const startReviewSession = useReviewStore((state) => state.startSession);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentMistakes, setRecentMistakes] = useState<Mistake[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<TaxonomyTag[]>([]);
  const [totalMistakes, setTotalMistakes] = useState(0);
  const [dueCount, setDueCount] = useState(0);

  const formatDate = (value: string): string =>
    new Date(value).toLocaleString(language, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      setLoading(true);
      setError(null);

      try {
        const [mistakeResponse, categoryResponse, tagResponse, dueCountResponse] = await Promise.all([
          listMistakes({ page: 1, page_size: 5 }),
          listCategories(),
          listTags(),
          getDueCount(),
        ]);

        if (!active) {
          return;
        }

        setRecentMistakes(mistakeResponse.items);
        setTotalMistakes(mistakeResponse.total);
        setCategories(categoryResponse.items);
        setTags(tagResponse.items);
        setDueCount(dueCountResponse.due_count);
      } catch (bootstrapError) {
        if (!active) {
          return;
        }

        setError(bootstrapError instanceof Error ? bootstrapError.message : t("dashboard.loadFailed"));
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="page-stack">
        <div className="page-title-copy">
          <Typography.Title level={2} style={{ margin: 0 }}>
            {t("nav.dashboard")}
          </Typography.Title>
          <p className="page-subtitle">{t("dashboard.subtitleLoading")}</p>
        </div>
        <div className="metric-grid">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index} className="panel-card">
              <Skeleton active paragraph={false} />
            </Card>
          ))}
        </div>
        <Skeleton active paragraph={{ rows: 6 }} />
      </div>
    );
  }

  if (error) {
    return (
      <Result
        status="500"
        title={t("dashboard.syncFailed")}
        subTitle={error}
        extra={
          <Button type="primary" onClick={() => window.location.reload()}>
            {t("common.retry")}
          </Button>
        }
      />
    );
  }

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div className="page-title-copy">
          <Typography.Title level={2} style={{ margin: 0 }}>
            {t("nav.dashboard")}
          </Typography.Title>
          <p className="page-subtitle">{t("dashboard.subtitle")}</p>
        </div>
        <Space>
          <Button
            type="primary"
            ghost
            onClick={async () => {
              await startReviewSession({ strategy: dueCount > 0 ? "due_first" : "random" });
              navigate("/review");
            }}
          >
            {dueCount > 0
              ? t("dashboard.dueButton", { count: dueCount })
              : t("dashboard.noDueButton")}
          </Button>
          <Button onClick={() => navigate("/mistakes")}>{t("dashboard.browseMistakes")}</Button>
          <Button type="primary" onClick={() => navigate("/mistakes/new")}>
            {t("dashboard.addMistake")}
          </Button>
        </Space>
      </div>

      <div className="metric-grid">
        <Card className="panel-card">
          <Statistic title={t("dashboard.totalMistakes")} value={totalMistakes} />
        </Card>
        <Card className="panel-card">
          <Statistic title={t("dashboard.categories")} value={categories.length} />
        </Card>
        <Card className="panel-card">
          <Statistic title={t("dashboard.tags")} value={tags.length} />
        </Card>
      </div>

      {totalMistakes === 0 ? (
        <Card className="panel-card">
          <div className="placeholder-copy">
            <Typography.Title level={4}>{t("dashboard.emptyTitle")}</Typography.Title>
            <Typography.Paragraph className="soft-note">
              {t("dashboard.emptyDesc")}
            </Typography.Paragraph>
            <Button type="primary" onClick={() => navigate("/mistakes/new")}>
              {t("dashboard.addFirst")}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="panel-grid">
          <Card className="panel-card" title={t("dashboard.recentMistakes")}>
            <List
              dataSource={recentMistakes}
              renderItem={(mistake) => (
                <List.Item>
                  <List.Item.Meta
                    title={mistake.title}
                    description={
                      <Space wrap>
                        <Tag>{mistake.language}</Tag>
                        <span className="soft-note">{formatDate(mistake.updated_at)}</span>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
          <Card className="panel-card" title={t("dashboard.tagCloud")}>
            <Space size={[8, 12]} wrap>
              {tags.length > 0 ? (
                tags.map((tag) => (
                  <Tag key={tag.id} color="default">
                    #{tag.name}
                  </Tag>
                ))
              ) : (
                <Typography.Text className="soft-note">{t("dashboard.noTags")}</Typography.Text>
              )}
            </Space>
          </Card>
        </div>
      )}
    </div>
  );
}

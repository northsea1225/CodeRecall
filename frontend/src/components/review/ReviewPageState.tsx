import { Card, Result, Space, Typography } from "antd";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface ReviewPageStateProps {
  subtitle: string;
  status: "info" | "success" | "error";
  title: string;
  resultSubtitle: string;
  extra?: ReactNode;
  children?: ReactNode;
}

export default function ReviewPageState({
  subtitle,
  status,
  title,
  resultSubtitle,
  extra,
  children,
}: ReviewPageStateProps) {
  const { t } = useTranslation();
  return (
    <div className="page-stack">
      <div className="page-title-copy">
        <Typography.Title level={2} style={{ margin: 0 }}>
          {t("review.pageTitle")}
        </Typography.Title>
        <p className="page-subtitle">{subtitle}</p>
      </div>
      <Card className="panel-card panel-card--placeholder">
        {children ?? <Result status={status} title={title} subTitle={resultSubtitle} extra={extra ? <Space>{extra}</Space> : undefined} />}
      </Card>
    </div>
  );
}

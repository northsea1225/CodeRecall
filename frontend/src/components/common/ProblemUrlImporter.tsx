import { useState } from "react";
import { Alert, Button, Card, Input, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { previewProblemUrl, type ProblemUrlPreviewResponse } from "../../services/problemImportService";

interface ProblemUrlImporterProps {
  onFilled: (data: ProblemUrlPreviewResponse) => void;
  autoFocus?: boolean;
}

const SUPPORTED_URL_PATTERN = /^https?:\/\/(www\.)?(leetcode\.(com|cn)|codeforces\.com)\//i;

export default function ProblemUrlImporter({ onFilled, autoFocus }: ProblemUrlImporterProps) {
  const { t } = useTranslation();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  const handleFetch = async () => {
    const trimmed = url.trim();
    if (!SUPPORTED_URL_PATTERN.test(trimmed)) {
      setError(t("urlImport.unsupportedPlatform"));
      return;
    }
    setLoading(true);
    setError(null);
    setWarnings([]);
    try {
      const data = await previewProblemUrl(trimmed);
      if (data.warnings?.length) {
        setWarnings(data.warnings);
      }
      onFilled(data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: { message?: string } } } })
        ?.response?.data?.detail;
      setError(detail?.message ?? t("urlImport.fetchFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="panel-card">
      <Space direction="vertical" style={{ width: "100%" }}>
        <Typography.Text strong>{t("urlImport.title")}</Typography.Text>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            autoFocus={autoFocus}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={t("urlImport.placeholder")}
            disabled={loading}
            onPressEnter={() => void handleFetch()}
          />
          <Button type="primary" loading={loading} onClick={() => void handleFetch()} disabled={!url.trim()}>
            {t("urlImport.fetchButton")}
          </Button>
        </Space.Compact>
        {error && (
          <Alert type="warning" message={error} showIcon closable onClose={() => setError(null)} />
        )}
        {warnings.map((warning) => (
          <Alert
            key={warning}
            type="warning"
            message={warning}
            showIcon
            closable
            onClose={() => setWarnings((items) => items.filter((item) => item !== warning))}
          />
        ))}
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {t("urlImport.supportedPlatforms")}
        </Typography.Text>
      </Space>
    </Card>
  );
}

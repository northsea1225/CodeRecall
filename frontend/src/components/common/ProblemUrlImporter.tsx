import { useState } from "react";
import { Alert, Button, Card, Input, Space, Typography } from "antd";
import { previewProblemUrl, type ProblemUrlPreviewResponse } from "../../services/problemImportService";

interface ProblemUrlImporterProps {
  onFilled: (data: ProblemUrlPreviewResponse) => void;
  autoFocus?: boolean;
}

const SUPPORTED_URL_PATTERN = /^https?:\/\/(www\.)?(leetcode\.(com|cn)|codeforces\.com)\//i;

export default function ProblemUrlImporter({ onFilled, autoFocus }: ProblemUrlImporterProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  const handleFetch = async () => {
    const trimmed = url.trim();
    if (!SUPPORTED_URL_PATTERN.test(trimmed)) {
      setError("请输入支持的平台链接（LeetCode 或 Codeforces）");
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
      setError(detail?.message ?? "抓取失败，请手动填写题面");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="panel-card">
      <Space direction="vertical" style={{ width: "100%" }}>
        <Typography.Text strong>从 OJ 链接导入题面</Typography.Text>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            autoFocus={autoFocus}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="粘贴 LeetCode 或 Codeforces 题目链接自动提取"
            disabled={loading}
            onPressEnter={() => void handleFetch()}
          />
          <Button type="primary" loading={loading} onClick={() => void handleFetch()} disabled={!url.trim()}>
            抓取
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
          当前支持 LeetCode（中英文站）与 Codeforces。
        </Typography.Text>
      </Space>
    </Card>
  );
}

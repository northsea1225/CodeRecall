import { useState } from "react";
import { Alert, Button, Card, Input, Space, Typography } from "antd";
import { previewProblemUrl, type ProblemUrlPreviewResponse } from "../../services/problemImportService";

interface ProblemUrlImporterProps {
  onFilled: (data: ProblemUrlPreviewResponse) => void;
}

const LEETCODE_PATTERN = /^https?:\/\/(www\.)?(leetcode\.com|leetcode\.cn)\/problems\/[a-z0-9-]+/i;

export default function ProblemUrlImporter({ onFilled }: ProblemUrlImporterProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    const trimmed = url.trim();
    if (!LEETCODE_PATTERN.test(trimmed)) {
      setError("请输入有效的 LeetCode 题目链接（如 https://leetcode.cn/problems/two-sum/）");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await previewProblemUrl(trimmed);
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
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="粘贴 LeetCode 题目链接自动提取题面（如 https://leetcode.cn/problems/two-sum/）"
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
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          当前支持 LeetCode（中英文站）。Codeforces、洛谷等平台接入中，敬请期待。
        </Typography.Text>
      </Space>
    </Card>
  );
}

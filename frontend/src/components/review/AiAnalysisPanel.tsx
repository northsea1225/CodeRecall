import { useEffect, useRef } from "react";
import { Alert, Button, Empty, Space, Spin, Typography } from "antd";
import ReactMarkdown from "react-markdown";

import type { AiAnalysisStreamStatus } from "../../types/review";

interface AiAnalysisPanelProps {
  enabled: boolean;
  model?: string;
  status: AiAnalysisStreamStatus;
  content: string;
  error: string | null;
  onRetry: () => void;
  onStop: () => void;
}

export default function AiAnalysisPanel({
  enabled,
  model,
  status,
  content,
  error,
  onRetry,
  onStop,
}: AiAnalysisPanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [content]);
  if (!enabled) {
    return (
      <div className="ai-analysis-panel ai-analysis-panel--disabled">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="AI 分析未启用，仍可手动填写错因总结。"
        />
      </div>
    );
  }

  if (status === "idle") {
    return (
      <div className="ai-analysis-panel">
        <Typography.Text strong>AI 深度分析</Typography.Text>
        <Typography.Paragraph className="soft-note" style={{ marginBottom: 0 }}>
          当前模型：{model ?? "未声明"}。点击右上角按钮后，会实时流式返回复盘建议。
        </Typography.Paragraph>
      </div>
    );
  }

  if (status === "ready") {
    return (
      <div className="ai-analysis-panel">
        <Typography.Text strong>AI 深度分析</Typography.Text>
        <Typography.Paragraph className="soft-note" style={{ marginBottom: 0 }}>
          当前模型：{model ?? "未声明"}。点击右上角按钮后，会实时流式返回复盘建议。
        </Typography.Paragraph>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="ai-analysis-panel ai-analysis-panel--error">
        <Alert
          type="error"
          showIcon
          message="分析失败，点击重试"
          description={error ?? "暂时无法完成 AI 分析。"}
          action={
            <Button size="small" onClick={onRetry}>
              重试
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="ai-analysis-panel">
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        {status === "streaming" ? (
          <Space size="small">
            <Spin size="small" />
            <Typography.Text className="soft-note">思考中...</Typography.Text>
            <Button size="small" type="link" onClick={onStop}>
              停止
            </Button>
          </Space>
        ) : (
          <Typography.Text type="success">分析完成</Typography.Text>
        )}
        <div className="ai-analysis-panel__content" ref={scrollContainerRef}>
          <div className={status === "streaming" ? "ai-analysis-panel__cursor" : undefined}>
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>
      </Space>
    </div>
  );
}

import { Button, Card, Space, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";

import CodeEditor from "../common/CodeEditor";
import MarkdownRenderer from "../common/MarkdownRenderer";
import { useUIStore } from "../../stores/uiStore";
import type { ReviewItem } from "../../types/review";
import { toMonacoLanguage } from "../../utils/monacoLanguage";

interface StemViewProps {
  currentItem: ReviewItem;
  loading?: boolean;
  userAttemptMarkdown: string;
  onUserAttemptChange: (value: string) => void;
  onShowAnswer: () => void;
}

export default function StemView({
  currentItem,
  loading = false,
  userAttemptMarkdown,
  onUserAttemptChange,
  onShowAnswer,
}: StemViewProps) {
  const { t } = useTranslation();
  const uiTheme = useUIStore((state) => state.theme);
  const monacoTheme = uiTheme === "dark" ? "coderecall-dark" : "coderecall-light";
  const hasUserAttempt = userAttemptMarkdown.trim().length > 0;

  return (
    <Card className="panel-card review-content-card">
      <div className="page-stack">
        <div className="review-meta">
          <Space wrap>
            <Tag>{currentItem.language}</Tag>
            <Tag color="geekblue">{t("reviewComponents.difficulty", { difficulty: currentItem.difficulty })}</Tag>
            <Tag color="cyan">{currentItem.category_name}</Tag>
            {currentItem.tag_names.map((tag) => (
              <Tag key={tag}>#{tag}</Tag>
            ))}
          </Space>
        </div>

        <div className="review-markdown review-markdown--stem">
          <MarkdownRenderer>{currentItem.stem_markdown}</MarkdownRenderer>
        </div>

        <div className="review-actions">
          <Typography.Text strong>{t("reviewComponents.attemptEditorTitle")}</Typography.Text>
        </div>

        <CodeEditor
          value={userAttemptMarkdown}
          onChange={onUserAttemptChange}
          language={toMonacoLanguage(currentItem.language)}
          height={250}
          theme={monacoTheme}
        />

        <div className="review-actions">
          <Button
            type="primary"
            size="large"
            disabled={loading || !hasUserAttempt}
            loading={loading}
            onClick={onShowAnswer}
          >
            {t("reviewComponents.submitAttempt")}
          </Button>
          <Button type="default" size="large" disabled={loading} onClick={onShowAnswer}>
            {hasUserAttempt ? t("reviewComponents.giveUpAndShowAnswer") : t("reviewComponents.skipToAnswer")}
          </Button>
        </div>
      </div>
    </Card>
  );
}

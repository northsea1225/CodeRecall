import { useEffect, useRef, useState } from "react";
import { FullscreenExitOutlined, FullscreenOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Progress, Result, Segmented, Space, Spin, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AnswerView from "../../components/review/AnswerView";
import CompletedView from "../../components/review/CompletedView";
import ExitConfirmModal from "../../components/review/ExitConfirmModal";
import RawMistakeDrawer from "../../components/review/RawMistakeDrawer";
import ReviewPageState from "../../components/review/ReviewPageState";
import StemView from "../../components/review/StemView";
import { selfRateOptions } from "../../components/review/shared";
import { getStatsOverview } from "../../services/statsService";
import { useAuthStore } from "../../stores/authStore";
import { useReviewStore } from "../../stores/reviewStore";
import { uiStore } from "../../stores/uiStore";
import type { ReviewStrategy } from "../../types/review";

interface ReviewPageProps {
  immersive?: boolean;
}

export default function ReviewPage({ immersive = false }: ReviewPageProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [exitConfirmOpen, setExitConfirmOpen] = useState(false);
  const [rawMistakeOpen, setRawMistakeOpen] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<ReviewStrategy>("due_first");
  const prevCompleted = useRef(false);
  const sessionId = useReviewStore((state) => state.sessionId);
  const strategy = useReviewStore((state) => state.strategy);
  const progress = useReviewStore((state) => state.progress);
  const capability = useReviewStore((state) => state.capability);
  const currentItem = useReviewStore((state) => state.currentItem);
  const showingAnswer = useReviewStore((state) => state.showingAnswer);
  const revealedData = useReviewStore((state) => state.revealedData);
  const loading = useReviewStore((state) => state.loading);
  const submitting = useReviewStore((state) => state.submitting);
  const completed = useReviewStore((state) => state.completed);
  const summary = useReviewStore((state) => state.summary);
  const error = useReviewStore((state) => state.error);
  const userAttemptMarkdown = useReviewStore((state) => state.userAttemptMarkdown);
  const startSession = useReviewStore((state) => state.startSession);
  const loadNext = useReviewStore((state) => state.loadNext);
  const showAnswer = useReviewStore((state) => state.showAnswer);
  const submitRate = useReviewStore((state) => state.submitRate);
  const exitSession = useReviewStore((state) => state.exitSession);
  const setUserAttemptMarkdown = useReviewStore((state) => state.setUserAttemptMarkdown);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest(".monaco-editor")) {
        return;
      }
      const isTypingTarget =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;
      if (isTypingTarget) {
        return;
      }
      if (event.key === "Escape" && sessionId) {
        event.preventDefault();
        setExitConfirmOpen(true);
        return;
      }
      if (loading || submitting || !currentItem) {
        return;
      }
      if ((event.code === "Space" || event.code === "Enter") && !showingAnswer) {
        event.preventDefault();
        void showAnswer();
        return;
      }
      if (showingAnswer && event.key.toLowerCase() === "r") {
        event.preventDefault();
        setRawMistakeOpen(true);
        return;
      }
      if (!showingAnswer) {
        return;
      }
      const matchedRate = selfRateOptions.find((option) => option.key === event.key);
      if (!matchedRate) {
        return;
      }
      event.preventDefault();
      void submitRate(matchedRate.value);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentItem, loading, sessionId, showAnswer, showingAnswer, submitRate, submitting]);

  useEffect(() => {
    if (!prevCompleted.current && completed) {
      const tz = -new Date().getTimezoneOffset();
      void getStatsOverview({ tz_offset_minutes: tz })
        .then(({ streak_days }) => {
          const userId = useAuthStore.getState().userId ?? "guest";
          const localDate = new Date().toLocaleDateString("sv");
          const dedupKey = `cr-streak-toast:${userId}:${localDate}`;
          if (localStorage.getItem(dedupKey)) return;
          localStorage.setItem(dedupKey, "1");
          const showToast = uiStore.getState().showToast;
          if (streak_days >= 30) {
            showToast("success", t("review.streakMilestone30"));
          } else if (streak_days >= 7) {
            showToast("success", t("review.streakMilestone7"));
          } else {
            showToast("info", t("review.streakToast", { days: streak_days }));
          }
        })
        .catch((err) => console.error("Streak check failed", err));
    }
    prevCompleted.current = completed;
  }, [completed]);

  const percent = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
  const handleExit = () => {
    setExitConfirmOpen(false);
    setRawMistakeOpen(false);
    exitSession();
    navigate(immersive ? "/review" : "/dashboard");
  };
  const handleShowAnswer = () => void showAnswer();

  if (!sessionId && !loading) {
    return (
      <ReviewPageState
        subtitle={t("review.subtitleStart")}
        status="info"
        title={t("review.titleStart")}
        resultSubtitle={t("review.resultSubtitleStart")}
        extra={
          <>
            <Segmented
              options={[
                { label: t("review.strategyRandom"), value: "random" },
                { label: t("review.strategyDue"), value: "due_first" },
              ]}
              value={selectedStrategy}
              onChange={(value) => setSelectedStrategy(value as ReviewStrategy)}
            />
            {!immersive ? (
              <span className="review-immersive-entry">
                <Button icon={<FullscreenOutlined />} onClick={() => navigate("/review/immersive")}>
                  {t("review.enterImmersive")}
                </Button>
              </span>
            ) : (
              <Button className="review-immersive-exit" icon={<FullscreenExitOutlined />} onClick={() => navigate("/review")}>
                {t("review.exitImmersive")}
              </Button>
            )}
            <Button onClick={() => navigate("/mistakes")}>{t("review.backToList")}</Button>
            <Button type="primary" onClick={() => void startSession({ strategy: selectedStrategy })}>
              {t("review.startReview")}
            </Button>
          </>
        }
      />
    );
  }

  if (loading && !currentItem && !completed) {
    return (
      <ReviewPageState subtitle={t("review.titleLoading")} status="info" title={t("review.titleLoading")} resultSubtitle="">
        <Spin size="large" />
      </ReviewPageState>
    );
  }

  if (error && !currentItem && !completed) {
    return (
      <ReviewPageState
        subtitle={t("review.subtitleError")}
        status="error"
        title={t("review.titleError")}
        resultSubtitle={error}
        extra={
          <>
            <Button onClick={() => navigate("/dashboard")}>{t("common.backToDashboard")}</Button>
            <Button
              type="primary"
              onClick={() => void (sessionId ? loadNext() : startSession({ strategy: selectedStrategy }))}
            >
              {t("common.retry")}
            </Button>
          </>
        }
      />
    );
  }

  if (sessionId && progress.total === 0 && !completed) {
    return (
      <ReviewPageState
        subtitle={t("review.subtitleEmpty")}
        status="success"
        title={t("review.titleEmpty")}
        resultSubtitle={t("review.subtitleRest")}
        extra={
          <>
            <Button onClick={() => navigate("/dashboard")}>{t("common.backToDashboard")}</Button>
            <Button type="primary" onClick={() => navigate("/mistakes/new")}>
              {t("review.addMistake")}
            </Button>
          </>
        }
      />
    );
  }

  return (
    <div className="page-stack review-shell">
      <div className="page-title-row">
        <div className="page-title-copy">
          <Typography.Title level={2} style={{ margin: 0 }}>{t("review.titleActive")}</Typography.Title>
          <p className="page-subtitle">
            {completed
              ? t("review.subtitleCompleted")
              : t("review.subtitleProgress", { completed: progress.completed, total: progress.total })}
          </p>
        </div>
        {!completed ? (
          <Space>
            <Tag color="processing">{t("review.strategyTag", { strategy: strategy ?? "random" })}</Tag>
            <Button onClick={() => setExitConfirmOpen(true)}>{t("common.backToDashboard")}</Button>
          </Space>
        ) : null}
      </div>

      {!completed ? (
        <Card className="panel-card review-progress-card">
          <div className="review-progress-copy">
            <Typography.Text strong>{currentItem?.title ?? t("review.nextItem")}</Typography.Text>
            <Typography.Text className="soft-note">{t("review.recallNote")}</Typography.Text>
          </div>
          <Progress percent={percent} status="active" />
        </Card>
      ) : null}

      {error ? <Alert type="error" message={error} showIcon /> : null}

      {completed && summary ? (
        <CompletedView
          summary={summary}
          onBack={handleExit}
          onRestart={() => {
            const restartStrategy = strategy ?? selectedStrategy;
            exitSession();
            void startSession({ strategy: restartStrategy });
          }}
        />
      ) : showingAnswer && currentItem ? (
        <AnswerView
          capability={capability}
          currentItem={currentItem}
          revealedData={revealedData}
          submitting={submitting}
          userAttemptMarkdown={userAttemptMarkdown}
          onOpenRawMistake={() => setRawMistakeOpen(true)}
          onSubmitRate={(value) => void submitRate(value)}
        />
      ) : currentItem ? (
        <StemView
          currentItem={currentItem}
          loading={loading}
          userAttemptMarkdown={userAttemptMarkdown}
          onUserAttemptChange={setUserAttemptMarkdown}
          onShowAnswer={handleShowAnswer}
        />
      ) : (
        <Card className="panel-card review-content-card">
          <Empty description={t("review.preparingNext")} />
        </Card>
      )}

      <ExitConfirmModal open={exitConfirmOpen} onCancel={() => setExitConfirmOpen(false)} onConfirm={handleExit} />
      <RawMistakeDrawer
        open={rawMistakeOpen}
        mistakeId={currentItem?.mistake_id ?? null}
        currentItem={currentItem}
        revealedData={revealedData}
        onClose={() => setRawMistakeOpen(false)}
      />
    </div>
  );
}

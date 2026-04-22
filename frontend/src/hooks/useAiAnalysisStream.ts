import { useCallback, useEffect, useRef, useState } from "react";

import { apiBaseURL } from "../services/api";
import type { AiAnalysisStreamStatus } from "../types/review";

interface StreamRequest {
  mistakeId: number;
  model?: string;
}

interface StreamSnapshot {
  status: AiAnalysisStreamStatus;
  content: string;
  error: string | null;
}

const readySnapshot: StreamSnapshot = {
  status: "ready",
  content: "",
  error: null,
};

export function useAiAnalysisStream() {
  const sourceRef = useRef<EventSource | null>(null);
  const lastRequestRef = useRef<StreamRequest | null>(null);
  const [snapshot, setSnapshot] = useState<StreamSnapshot>(readySnapshot);

  const closeStream = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  useEffect(() => closeStream, [closeStream]);

  const startStream = useCallback(async (request: StreamRequest) => {
    closeStream();
    lastRequestRef.current = request;
    setSnapshot({
      status: "streaming",
      content: "",
      error: null,
    });

    const params = new URLSearchParams({
      mistake_id: String(request.mistakeId),
    });
    if (request.model) {
      params.set("model", request.model);
    }

    const source = new EventSource(`${apiBaseURL}/ai/analyze/stream?${params.toString()}`);
    sourceRef.current = source;

    source.onmessage = (event) => {
      if (event.data === "[DONE]") {
        closeStream();
        setSnapshot((current) => ({
          status: "completed",
          content: current.content,
          error: null,
        }));
        return;
      }

      try {
        const payload = JSON.parse(event.data) as { delta?: string };
        if (!payload.delta) {
          return;
        }

        setSnapshot((current) => ({
          status: "streaming",
          content: current.content + payload.delta,
          error: null,
        }));
      } catch {
        closeStream();
        setSnapshot({
          status: "error",
          content: "",
          error: "AI 流返回了无法解析的数据。",
        });
      }
    };

    source.onerror = (event) => {
      const messageEvent = event as MessageEvent<string>;
      closeStream();

      if (messageEvent.data) {
        try {
          const payload = JSON.parse(messageEvent.data) as { message?: string };
          setSnapshot((current) => ({
            status: "error",
            content: current.content,
            error: payload.message ?? "AI 分析失败。",
          }));
          return;
        } catch {
          // fall through to generic error message
        }
      }

      setSnapshot((current) => ({
        status: "error",
        content: current.content,
        error: current.content ? "AI 流已中断。" : "AI 分析失败，请稍后重试。",
      }));
    };
  }, [closeStream]);

  const stop = useCallback(() => {
    closeStream();
    setSnapshot((current) => ({
      status: current.content ? "completed" : "ready",
      content: current.content,
      error: current.error,
    }));
  }, [closeStream]);

  const retry = useCallback(async () => {
    if (!lastRequestRef.current) {
      setSnapshot(readySnapshot);
      return;
    }

    await startStream(lastRequestRef.current);
  }, [startStream]);

  const reset = useCallback(() => {
    closeStream();
    lastRequestRef.current = null;
    setSnapshot(readySnapshot);
  }, [closeStream]);

  return {
    state: snapshot.status,
    content: snapshot.content,
    error: snapshot.error,
    startStream,
    stop,
    retry,
    reset,
  };
}

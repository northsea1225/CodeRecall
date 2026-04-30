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
const TOKEN_KEY = "coderecall_token";

function getBearerToken(): string {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? ((JSON.parse(raw) as { token?: string }).token ?? "") : "";
  } catch {
    return "";
  }
}

export function useAiAnalysisStream() {
  const abortRef = useRef<AbortController | null>(null);
  const lastRequestRef = useRef<StreamRequest | null>(null);
  const [snapshot, setSnapshot] = useState<StreamSnapshot>(readySnapshot);

  const closeStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  useEffect(() => closeStream, [closeStream]);

  const startStream = useCallback(
    async (request: StreamRequest) => {
      closeStream();
      lastRequestRef.current = request;
      setSnapshot({ status: "streaming", content: "", error: null });

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const params = new URLSearchParams({ mistake_id: String(request.mistakeId) });
      if (request.model) params.set("model", request.model);

      let response: Response;
      try {
        response = await fetch(`${apiBaseURL}/ai/analyze/stream?${params.toString()}`, {
          headers: { Authorization: `Bearer ${getBearerToken()}` },
          signal: ctrl.signal,
        });
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setSnapshot({ status: "error", content: "", error: "AI 分析失败，请稍后重试。" });
        return;
      }

      if (!response.ok) {
        let msg = "AI 分析失败，请稍后重试。";
        try {
          const body = (await response.json()) as unknown;
          if (body && typeof body === "object") {
            const detail = (body as { detail?: unknown }).detail;
            const message = (body as { message?: unknown }).message;
            if (typeof detail === "string") {
              msg = detail;
            } else if (typeof message === "string") {
              msg = message;
            }
          }
        } catch {
          /* ignore */
        }
        setSnapshot({ status: "error", content: "", error: msg });
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        setSnapshot({ status: "error", content: "", error: "AI 流不可用。" });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split(/\r?\n\r?\n/);
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            let eventType = "message";
            const dataLines: string[] = [];
            for (const l of part.split(/\r?\n/)) {
              if (l.startsWith("event: ")) eventType = l.slice(7).trim();
              else if (l.startsWith("data: ")) dataLines.push(l.slice(6));
            }
            const dataLine = dataLines.join("\n");
            if (!dataLine) continue;

            if (eventType === "error") {
              let errMsg = "AI 分析失败。";
              try {
                const errPayload = JSON.parse(dataLine) as { message?: string };
                errMsg = errPayload.message ?? errMsg;
              } catch {
                /* use default */
              }
              setSnapshot((cur) => ({
                status: "error",
                content: cur.content,
                error: errMsg,
              }));
              return;
            }

            if (dataLine === "[DONE]") {
              setSnapshot((cur) => ({ status: "completed", content: cur.content, error: null }));
              return;
            }

            try {
              const payload = JSON.parse(dataLine) as { delta?: string };
              if (payload.delta) {
                setSnapshot((cur) => ({
                  status: "streaming",
                  content: cur.content + payload.delta,
                  error: null,
                }));
              }
            } catch {
              /* malformed event — skip */
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setSnapshot((cur) => ({
          status: "error",
          content: cur.content,
          error: cur.content ? "AI 流已中断。" : "AI 分析失败，请稍后重试。",
        }));
      }
    },
    [closeStream],
  );

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

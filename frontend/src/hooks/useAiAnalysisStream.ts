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

// Pure type guard for HTTP error response bodies. Accepts the
// `unknown` returned by `response.json()` and pulls out the first
// usable `detail` or `message` string, or returns `null` so the
// caller can fall back to a generic message.
export function parseErrorBody(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const obj = payload as Record<string, unknown>;
  const detail = obj.detail;
  if (typeof detail === "string") return detail;
  const message = obj.message;
  if (typeof message === "string") return message;
  return null;
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
          const body: unknown = await response.json();
          msg = parseErrorBody(body) ?? msg;
        } catch (parseErr) {
          if (import.meta.env.DEV) {
            console.warn("[useAiAnalysisStream] error body is not JSON:", parseErr);
          }
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
              } catch (parseErr) {
                if (import.meta.env.DEV) {
                  console.warn("[useAiAnalysisStream] error event payload is not JSON:", parseErr);
                }
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
              // Silent on purpose: SSE delta lines may be partial frames or
              // protocol noise (keep-alive comments, fragment boundaries).
              // dev-mode console.warn here would be too chatty for normal
              // streaming traffic.
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

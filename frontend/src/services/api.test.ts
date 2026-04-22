import { AxiosError } from "axios";
import { describe, expect, it } from "vitest";

import { extractApiErrorMessage } from "./api";

describe("extractApiErrorMessage", () => {
  it("prefers backend message from standard error payload", () => {
    const error = new AxiosError("Request failed", undefined, undefined, undefined, {
      data: {
        code: "mistake_not_found",
        message: "Mistake not found.",
        detail: { mistake_id: 42 },
      },
      status: 404,
      statusText: "Not Found",
      headers: {},
      config: {} as never,
    });

    expect(extractApiErrorMessage(error)).toBe("Mistake not found.");
  });

  it("falls back to axios message when payload is unknown", () => {
    const error = new AxiosError("Network Error");

    expect(extractApiErrorMessage(error)).toBe("Network Error");
  });
});

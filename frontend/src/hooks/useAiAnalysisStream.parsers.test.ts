import { describe, expect, it } from "vitest";

import { parseErrorBody } from "./useAiAnalysisStream";


describe("parseErrorBody", () => {
  it("returns null for non-object payloads", () => {
    expect(parseErrorBody(null)).toBeNull();
    expect(parseErrorBody(undefined)).toBeNull();
    expect(parseErrorBody("oops")).toBeNull();
    expect(parseErrorBody(42)).toBeNull();
  });

  it("returns null for objects without detail or message", () => {
    expect(parseErrorBody({})).toBeNull();
    expect(parseErrorBody({ code: "x" })).toBeNull();
  });

  it("prefers a string detail when present", () => {
    expect(parseErrorBody({ detail: "boom", message: "fallback" })).toBe("boom");
  });

  it("falls back to message when detail is missing or non-string", () => {
    expect(parseErrorBody({ message: "fallback" })).toBe("fallback");
    expect(parseErrorBody({ detail: { nested: 1 }, message: "fallback" })).toBe("fallback");
  });

  it("returns null when both detail and message are non-strings", () => {
    expect(parseErrorBody({ detail: { x: 1 }, message: 42 })).toBeNull();
  });
});

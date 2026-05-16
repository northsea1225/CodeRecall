import { describe, expect, it } from "vitest";
import payload from "./demoImportPayload.json";

describe("demoImportPayload.json", () => {
  it("matches the v1/v2 import envelope schema", () => {
    expect(payload).toHaveProperty("version", "v1");
    expect(payload).toHaveProperty("schema_version", "v2");
    expect(Array.isArray(payload.categories)).toBe(true);
    expect(Array.isArray(payload.tags)).toBe(true);
    expect(Array.isArray(payload.mistakes)).toBe(true);
  });

  it("ships at least 8 demo mistakes for first-time users", () => {
    expect(payload.mistakes.length).toBeGreaterThanOrEqual(8);
  });

  it("every mistake has the four core required fields non-empty", () => {
    for (const m of payload.mistakes) {
      expect(m.title, `${m.title}: title missing`).toBeTruthy();
      expect(
        m.stem_markdown,
        `${m.title}: stem_markdown missing`,
      ).toBeTruthy();
      expect(
        m.wrong_answer_markdown,
        `${m.title}: wrong_answer_markdown missing`,
      ).toBeTruthy();
      expect(
        m.correct_answer_markdown,
        `${m.title}: correct_answer_markdown missing`,
      ).toBeTruthy();
      expect(
        m.error_reason_markdown,
        `${m.title}: error_reason_markdown missing`,
      ).toBeTruthy();
    }
  });

  it("every mistake has a difficulty in [1, 5]", () => {
    for (const m of payload.mistakes) {
      expect(m.difficulty, `${m.title}: difficulty out of range`).toBeGreaterThanOrEqual(1);
      expect(m.difficulty, `${m.title}: difficulty out of range`).toBeLessThanOrEqual(5);
    }
  });

  it("every mistake's category_name references a declared category", () => {
    const declared = new Set(payload.categories.map((c) => c.name));
    for (const m of payload.mistakes) {
      expect(
        declared.has(m.category_name),
        `${m.title}: category_name "${m.category_name}" not declared`,
      ).toBe(true);
    }
  });

  it("every mistake's tag_names reference declared tags", () => {
    const declared = new Set(payload.tags.map((t) => t.name));
    for (const m of payload.mistakes) {
      for (const tagName of m.tag_names ?? []) {
        expect(
          declared.has(tagName),
          `${m.title}: tag "${tagName}" not declared`,
        ).toBe(true);
      }
    }
  });

  it("covers a spread of difficulty levels (not all the same)", () => {
    const levels = new Set(payload.mistakes.map((m) => m.difficulty));
    expect(levels.size, "demo data should span multiple difficulty levels").toBeGreaterThanOrEqual(2);
  });
});

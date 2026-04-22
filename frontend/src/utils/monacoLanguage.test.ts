import { describe, expect, it } from "vitest";

import { toMonacoLanguage } from "./monacoLanguage";

describe("toMonacoLanguage", () => {
  it("maps known aliases to Monaco language ids", () => {
    expect(toMonacoLanguage("js")).toBe("javascript");
    expect(toMonacoLanguage("typescript")).toBe("typescript");
    expect(toMonacoLanguage("py")).toBe("python");
    expect(toMonacoLanguage("cpp")).toBe("cpp");
    expect(toMonacoLanguage("java")).toBe("java");
    expect(toMonacoLanguage("go")).toBe("go");
    expect(toMonacoLanguage("rust")).toBe("rust");
    expect(toMonacoLanguage("sql")).toBe("sql");
  });

  it("falls back to plaintext for unknown or empty values", () => {
    expect(toMonacoLanguage("elixir")).toBe("plaintext");
    expect(toMonacoLanguage("")).toBe("plaintext");
    expect(toMonacoLanguage("   ")).toBe("plaintext");
  });
});

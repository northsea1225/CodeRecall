/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ["monaco-editor", "@monaco-editor/react"],
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
  },
  test: {
    // Playwright e2e specs live in ./e2e and must not be picked up by vitest;
    // their @playwright/test import is incompatible with the vitest runner.
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
  },
});

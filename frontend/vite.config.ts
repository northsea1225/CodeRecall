/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    // I-004 Phase 1: PWA shell scaffolding (manifest + icons + service worker
    // registration). Runtime API caching rules and route exclusions are added
    // in Phase 2/3 — keep this config minimal so a regression rolls back cheap.
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      includeAssets: [
        "logo.png",
        "icon-192.png",
        "icon-512.png",
        "icon-maskable-512.png",
      ],
      manifest: {
        name: "码错本 CodeRecall",
        short_name: "码错本",
        description: "面向 OI/ACM/LeetCode 选手的智能编程错题本",
        theme_color: "#6366F1",
        background_color: "#ffffff",
        display: "standalone",
        orientation: "portrait",
        scope: "/",
        start_url: "/",
        lang: "zh-CN",
        icons: [
          {
            src: "icon-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Precache only small static shell assets. Monaco language workers
        // (>3 MB each) are excluded so first paint stays fast and SW quota
        // does not balloon. API runtime caching is configured in Phase 2.
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        globIgnores: [
          "**/ts.worker-*.js",
          "**/editor.worker-*.js",
          "**/json.worker-*.js",
          "**/css.worker-*.js",
          "**/html.worker-*.js",
        ],
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
      },
    }),
  ],
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

import { useEffect } from "react";
import { App as AntdApp, ConfigProvider, Spin, theme as antdTheme } from "antd";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import { RouterProvider } from "react-router-dom";

import PWAUpdatePrompt from "./components/PWAUpdatePrompt";
import { router } from "./routes";
import { useUIStore } from "./stores/uiStore";

function ToastBridge() {
  const toast = useUIStore((state) => state.toast);
  const clearToast = useUIStore((state) => state.clearToast);
  const globalLoading = useUIStore((state) => state.globalLoading);
  const { message } = AntdApp.useApp();

  useEffect(() => {
    if (!toast) {
      return;
    }

    void message.open({
      key: toast.id,
      type: toast.type,
      content: toast.content,
    });
    clearToast();
  }, [clearToast, message, toast]);

  return <Spin fullscreen spinning={globalLoading} />;
}

export default function App() {
  const theme = useUIStore((state) => state.theme);
  const language = useUIStore((state) => state.language);
  const isDark = theme === "dark";
  const initializeTheme = useUIStore((state) => state.initializeTheme);
  const initializeLanguage = useUIStore((state) => state.initializeLanguage);

  useEffect(() => {
    initializeTheme();
    initializeLanguage();
  }, [initializeLanguage, initializeTheme]);

  return (
    <ConfigProvider
      locale={language === "zh-CN" ? zhCN : enUS}
      theme={{
        algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: "#6366F1",
          borderRadius: 8,
          fontFamily: "var(--font-ui)",
          colorBgLayout: isDark ? "#1A1A2E" : "#FFFFFF",
          colorBgContainer: isDark ? "#16213E" : "#F8FAFC",
          colorText: isDark ? "#E0E0E0" : "#0F172A",
          colorTextSecondary: isDark ? "#A0A0B0" : "#475569",
          colorBorder: isDark ? "#2A2A4A" : "#E2E8F0",
        },
        components: {
          Layout: {
            siderBg: "transparent",
            lightSiderBg: "transparent",
          },
        },
      }}
    >
      <AntdApp>
        <ToastBridge />
        <PWAUpdatePrompt />
        <RouterProvider router={router} />
      </AntdApp>
    </ConfigProvider>
  );
}

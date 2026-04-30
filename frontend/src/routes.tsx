import { lazy, Suspense, useMemo } from "react";
import { Button, Layout, Menu, Spin } from "antd";
import { useTranslation } from "react-i18next";
import { createBrowserRouter, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuthStore } from "./stores/authStore";
import { useUIStore } from "./stores/uiStore";
import { routerBridge } from "./utils/routerBridge";

const DashboardPage = lazy(() => import("./pages/Dashboard"));
const ImportExportPage = lazy(() => import("./pages/ImportExport"));
const LoginPage = lazy(() => import("./pages/Login"));
const MistakeEditorPage = lazy(() => import("./pages/MistakeEditor"));
const MistakeListPage = lazy(() => import("./pages/MistakeList"));
const RegisterPage = lazy(() => import("./pages/Register"));
const ImmersiveReviewPage = lazy(() => import("./pages/Review/ImmersiveReviewPage"));
const ReviewPage = lazy(() => import("./pages/Review"));
const StatsPage = lazy(() => import("./pages/Stats"));

const { Header, Sider, Content } = Layout;

const resolveSelectedKey = (pathname: string): string => {
  if (pathname.startsWith("/mistakes")) {
    return "/mistakes";
  }

  return pathname;
};

function PageFallback() {
  const { t } = useTranslation();

  return (
    <div className="page-stack" style={{ minHeight: 320, display: "grid", placeItems: "center" }}>
      <Spin size="large" tip={t("common.pageLoading")} />
    </div>
  );
}

const withSuspense = (element: React.ReactNode) => <Suspense fallback={<PageFallback />}>{element}</Suspense>;

function AppLayout() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useUIStore((state) => state.theme);
  const language = useUIStore((state) => state.language);
  const toggleTheme = useUIStore((state) => state.toggleTheme);
  const toggleLanguage = useUIStore((state) => state.toggleLanguage);
  const username = useAuthStore((state) => state.username);
  const logout = useAuthStore((state) => state.logout);
  const navigationItems = useMemo(
    () => [
      { key: "/dashboard", label: t("nav.dashboard") },
      { key: "/mistakes", label: t("nav.mistakes") },
      { key: "/review", label: t("nav.review") },
      { key: "/stats", label: t("nav.stats") },
      { key: "/import-export", label: t("nav.importExport") },
    ],
    [t],
  );

  return (
    <Layout className="app-shell">
      <Sider width={240} breakpoint="lg" collapsedWidth={0} className="app-sider">
        <div className="app-brand">
          <img src="/logo.png" alt="码错本" className="app-brand__mark" style={{ padding: 0, background: 'none' }} />
          <div>
            <strong>{t("app.title")}</strong>
            <div className="app-brand__sub">{t("app.subtitle")}</div>
          </div>
        </div>
        <Menu
          mode="inline"
          theme={theme === "dark" ? "dark" : "light"}
          selectedKeys={[resolveSelectedKey(location.pathname)]}
          items={navigationItems}
          onClick={({ key }) => navigate(key)}
        />
        <div className="sider-user-footer">
          <div className="sider-username">{username}</div>
          <Button
            type="text"
            size="small"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            {t("auth.logout")}
          </Button>
        </div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <div>
            <h1 className="app-header__title">{t("app.title")}</h1>
          </div>
          <div className="app-header__actions" data-language={language}>
            <Button
              aria-label="Toggle theme"
              className="theme-toggle"
              icon={<span aria-hidden="true">{theme === "dark" ? "🌙" : "🌞"}</span>}
              onClick={toggleTheme}
            >
              {theme === "dark" ? t("theme.dark") : t("theme.light")}
            </Button>
            <Button
              aria-label="Toggle language"
              className="lang-toggle"
              onClick={toggleLanguage}
            >
              {t("lang.toggle")}
            </Button>
          </div>
        </Header>
        <Content className="app-content">
          <div className="page-card">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

function AuthGuard() {
  const token = useAuthStore((state) => state.token);
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: withSuspense(<LoginPage />) },
  { path: "/register", element: withSuspense(<RegisterPage />) },
  {
    path: "/",
    element: <AuthGuard />,
    children: [
      { path: "review/immersive", element: withSuspense(<ImmersiveReviewPage />) },
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: "dashboard", element: withSuspense(<DashboardPage />) },
          { path: "mistakes", element: withSuspense(<MistakeListPage />) },
          { path: "mistakes/new", element: withSuspense(<MistakeEditorPage />) },
          { path: "mistakes/:id", element: withSuspense(<MistakeEditorPage />) },
          { path: "mistakes/:id/edit", element: withSuspense(<MistakeEditorPage />) },
          { path: "review", element: withSuspense(<ReviewPage />) },
          { path: "stats", element: withSuspense(<StatsPage />) },
          { path: "import-export", element: withSuspense(<ImportExportPage />) },
        ],
      },
    ],
  },
]);

routerBridge.register((to, opts) => {
  void router.navigate(to, opts);
});

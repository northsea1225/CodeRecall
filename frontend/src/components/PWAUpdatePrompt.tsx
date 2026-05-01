import { useEffect } from "react";
import { App as AntdApp, Button, Space } from "antd";
import { useTranslation } from "react-i18next";
import { useRegisterSW } from "virtual:pwa-register/react";

// I-004 Phase 2: surface SW updates as an actionable antd notification.
// Mounted inside <AntdApp> so it can use the message/notification context API
// without manually attaching a contextHolder.
const NOTIFICATION_KEY = "pwa-update-prompt";

export default function PWAUpdatePrompt() {
  const { t } = useTranslation();
  const { notification } = AntdApp.useApp();

  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisterError(error) {
      // SW registration failure must not break the app; log only.
      // eslint-disable-next-line no-console
      console.warn("[pwa] service worker register error:", error);
    },
  });

  useEffect(() => {
    if (!needRefresh) {
      return;
    }
    notification.info({
      key: NOTIFICATION_KEY,
      message: t("pwa.updateTitle"),
      description: t("pwa.updateDescription"),
      duration: 0,
      placement: "bottomRight",
      btn: (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setNeedRefresh(false);
              notification.destroy(NOTIFICATION_KEY);
            }}
          >
            {t("pwa.updateLater")}
          </Button>
          <Button
            type="primary"
            size="small"
            onClick={() => {
              void updateServiceWorker(true);
            }}
          >
            {t("pwa.updateNow")}
          </Button>
        </Space>
      ),
    });
  }, [needRefresh, notification, setNeedRefresh, t, updateServiceWorker]);

  return null;
}

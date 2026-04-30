import { useState } from "react";
import { App, Button, Card, Form, Input, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { login as loginRequest } from "../../services/authService";
import { extractApiErrorMessage } from "../../services/api";
import { useAuthStore } from "../../stores/authStore";

interface LoginForm {
  username: string;
  password: string;
}

export default function LoginPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: LoginForm) => {
    setSubmitting(true);
    try {
      const response = await loginRequest(values.username, values.password);
      login(response.access_token, response.username, response.user_id);
      void message.success(t("auth.loginSuccess"));
      navigate("/", { replace: true });
    } catch (error) {
      void message.error(extractApiErrorMessage(error) || t("auth.loginFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <Card style={{ width: "min(420px, 100%)" }}>
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          {t("auth.login")}
        </Typography.Title>
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item name="username" label={t("auth.username")} rules={[{ required: true }]}>
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label={t("auth.password")} rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={submitting}>
            {t("auth.login")}
          </Button>
        </Form>
        <div style={{ marginTop: 16, textAlign: "center" }}>
          <Link to="/register">{t("auth.register")}</Link>
        </div>
      </Card>
    </div>
  );
}

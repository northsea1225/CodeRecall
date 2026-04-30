import { useState } from "react";
import { App, Button, Card, Form, Input, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { register as registerRequest } from "../../services/authService";
import { extractApiErrorMessage } from "../../services/api";
import { useAuthStore } from "../../stores/authStore";

interface RegisterForm {
  username: string;
  password: string;
}

export default function RegisterPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: RegisterForm) => {
    setSubmitting(true);
    try {
      const response = await registerRequest(values.username, values.password);
      login(response.access_token, response.username, response.user_id);
      void message.success(t("auth.registerSuccess"));
      navigate("/mistakes", { replace: true });
    } catch (error) {
      void message.error(extractApiErrorMessage(error) || t("auth.usernameExists"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <Card style={{ width: "min(420px, 100%)" }}>
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          {t("auth.register")}
        </Typography.Title>
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="username"
            label={t("auth.username")}
            rules={[
              { required: true },
              { min: 3, message: t("auth.usernameTooShort") },
              { max: 100, message: t("auth.usernameTooLong") },
              { pattern: /^[A-Za-z0-9_]+$/, message: t("auth.usernameInvalidChars") },
            ]}
          >
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label={t("auth.password")}
            rules={[
              { required: true },
              { min: 8, message: t("auth.passwordTooShort") },
              { max: 72, message: t("auth.passwordTooLong") },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={submitting}>
            {t("auth.register")}
          </Button>
        </Form>
        <div style={{ marginTop: 16, textAlign: "center" }}>
          <Link to="/login">{t("auth.login")}</Link>
        </div>
      </Card>
    </div>
  );
}

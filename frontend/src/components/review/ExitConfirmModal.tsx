import { Modal, Typography } from "antd";
import { useTranslation } from "react-i18next";

interface ExitConfirmModalProps {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function ExitConfirmModal({ open, onCancel, onConfirm }: ExitConfirmModalProps) {
  const { t } = useTranslation();

  return (
    <Modal
      open={open}
      title={t("reviewComponents.exitTitle")}
      okText={t("reviewComponents.exitOk")}
      cancelText={t("reviewComponents.exitCancel")}
      maskClosable={false}
      onCancel={onCancel}
      onOk={onConfirm}
    >
      <Typography.Paragraph style={{ marginBottom: 8 }}>
        {t("reviewComponents.exitBody")}
      </Typography.Paragraph>
      <Typography.Text className="soft-note">{t("reviewComponents.exitNote")}</Typography.Text>
    </Modal>
  );
}

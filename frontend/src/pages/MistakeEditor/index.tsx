import { useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  Rate,
  Result,
  Row,
  Select,
  Space,
  Typography,
} from "antd";
import type { InputRef } from "antd";
import { PlusOutlined, RobotOutlined } from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import CodeEditor from "../../components/common/CodeEditor";
import { api } from "../../services/api";
import { createMistake, getMistake, updateMistake } from "../../services/mistakeService";
import { createCategory, listCategories, listTags } from "../../services/taxonomyService";
import { draftStore, useDraftStore } from "../../stores/draftStore";
import { useUIStore } from "../../stores/uiStore";
import type { Category, Tag } from "../../types/mistake";
import { stripMarkdownCodeFences } from "../../utils/markdownCodeFence";
import { createEmptyDraft, draftToCreatePayload, draftToUpdatePayload, mistakeToDraft } from "./form";
import type { MistakeDraft } from "./form";
import ProblemUrlImporter from "../../components/common/ProblemUrlImporter";
import type { ProblemUrlPreviewResponse } from "../../services/problemImportService";

const monacoLanguageMap: Record<string, string> = {
  javascript: "javascript",
  typescript: "typescript",
  python: "python",
  cpp: "cpp",
  java: "java",
  go: "go",
  rust: "rust",
  sql: "sql",
  plain: "plaintext",
  plaintext: "plaintext",
};

interface AnswerCodeEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  language: string;
  height: number | string;
  theme: string;
}

function AnswerCodeEditor({ value, onChange, language, height, theme }: AnswerCodeEditorProps) {
  return (
    <CodeEditor
      value={stripMarkdownCodeFences(value)}
      onChange={(nextValue) => onChange?.(stripMarkdownCodeFences(nextValue))}
      language={language}
      height={height}
      theme={theme}
    />
  );
}

export default function MistakeEditorPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const rawId = params.id;
  const mistakeId = rawId ? Number(rawId) : undefined;
  const isEditMode = typeof mistakeId === "number" && Number.isFinite(mistakeId);
  const draftKey = isEditMode ? String(mistakeId) : "new";
  const [form] = Form.useForm<MistakeDraft>();
  const draft = useDraftStore((state) => state.drafts[draftKey]);
  const replaceDraft = useDraftStore((state) => state.replaceDraft);
  const patchDraft = useDraftStore((state) => state.patchDraft);
  const clearDraft = useDraftStore((state) => state.clearDraft);
  const ensureDraft = useDraftStore((state) => state.ensureDraft);
  const showToast = useUIStore((state) => state.showToast);
  const setGlobalLoading = useUIStore((state) => state.setGlobalLoading);
  const uiTheme = useUIStore((state) => state.theme);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [addingCategory, setAddingCategory] = useState(false);
  const [generatingAnswer, setGeneratingAnswer] = useState(false);
  const newCategoryInputRef = useRef<InputRef>(null);
  const previousDraftKey = useRef<string | null>(null);
  const stableInitialValues = useMemo(() => draft ?? createEmptyDraft(), [draftKey]);

  const languageOptions = useMemo(() => [
    { label: t("editor.langPlain"), value: "plaintext" },
    { label: "Python", value: "python" },
    { label: "TypeScript", value: "typescript" },
    { label: "JavaScript", value: "javascript" },
    { label: "Java", value: "java" },
    { label: "C++", value: "cpp" },
    { label: "Go", value: "go" },
    { label: "Rust", value: "rust" },
    { label: "SQL", value: "sql" },
  ], [t]);

  useEffect(() => {
    if (draft && previousDraftKey.current !== draftKey) {
      form.setFieldsValue(draft);
      previousDraftKey.current = draftKey;
    }
  }, [draft, draftKey, form]);

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      setLoading(true);

      try {
        const [categoryResponse, tagResponse] = await Promise.all([listCategories(), listTags()]);

        if (!active) {
          return;
        }

        setCategories(categoryResponse.items);
        setTags(tagResponse.items);

        const currentDraft = draftStore.getState().drafts[draftKey];

        if (isEditMode && mistakeId) {
          if (!currentDraft) {
            const mistake = await getMistake(mistakeId);
            if (!active) {
              return;
            }
            replaceDraft(draftKey, mistakeToDraft(mistake));
          }
        } else if (!currentDraft) {
          replaceDraft(draftKey, ensureDraft(draftKey) ?? createEmptyDraft());
        }
      } catch (bootstrapError) {
        if (active) {
          showToast("error", bootstrapError instanceof Error ? bootstrapError.message : t("editor.editorLoadFailed"));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    if (rawId && !isEditMode) {
      setLoading(false);
      return;
    }

    void bootstrap();

    return () => {
      active = false;
    };
  }, [draftKey, ensureDraft, isEditMode, mistakeId, rawId, replaceDraft, showToast, t]);

  const tagOptions = useMemo(
    () =>
      tags.map((tag) => ({
        label: tag.name,
        value: tag.name,
      })),
    [tags],
  );

  const editorLanguage = monacoLanguageMap[Form.useWatch("language", form) ?? "plaintext"] ?? "plaintext";
  const monacoTheme = uiTheme === "dark" ? "coderecall-dark" : "coderecall-light";

  if (rawId && !isEditMode) {
    return <Result status="404" title={t("editor.invalidId")} />;
  }

  const handleUrlFilled = (data: ProblemUrlPreviewResponse) => {
    const patch: Partial<MistakeDraft> = {
      title: data.title,
      stem_markdown: data.stem_markdown,
      difficulty: data.difficulty,
      source: data.source_url,
      tags: data.tags,
    };
    patchDraft(draftKey, patch);
    form.setFieldsValue(patch);
    showToast("success", t("editor.urlAutoFillSuccess"));
  };

  const handleAddCategory = async (event?: React.MouseEvent | React.KeyboardEvent) => {
    event?.preventDefault?.();
    event?.stopPropagation?.();
    const name = newCategoryName.trim();
    if (!name) return;
    if (categories.some((c) => c.name === name)) {
      showToast("error", t("editor.categoryAddExists"));
      return;
    }
    setAddingCategory(true);
    try {
      const created = await createCategory({ name, description: "" });
      setCategories((prev) => [...prev, created]);
      form.setFieldValue("category_id", created.id);
      patchDraft(draftKey, { category_id: created.id });
      setNewCategoryName("");
      showToast("success", t("editor.categoryAddSuccess"));
      setTimeout(() => newCategoryInputRef.current?.focus(), 0);
    } catch (err) {
      const message = err instanceof Error ? err.message : t("editor.categoryAddFailed");
      showToast("error", message);
    } finally {
      setAddingCategory(false);
    }
  };

  const handleGenerateCorrectAnswer = async () => {
    const rawStem = form.getFieldValue("stem_markdown");
    const stem = typeof rawStem === "string" ? rawStem.trim() : "";
    const language = form.getFieldValue("language") as string | undefined;
    if (!stem) {
      showToast("error", t("editor.aiAnswerNeedStem"));
      return;
    }
    if (!language) {
      showToast("error", t("editor.aiAnswerNeedLanguage"));
      return;
    }
    setGeneratingAnswer(true);
    try {
      const response = await api.post<{ correct_answer_markdown: string }>(
        "/ai/generate-correct-answer",
        { stem_markdown: stem, language },
      );
      const markdown = response.data?.correct_answer_markdown ?? "";
      form.setFieldValue("correct_answer_markdown", markdown);
      patchDraft(draftKey, { correct_answer_markdown: markdown });
      showToast("success", t("editor.aiAnswerSuccess"));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("editor.aiAnswerFailed");
      showToast("error", message);
    } finally {
      setGeneratingAnswer(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setGlobalLoading(true);
      const payload = values as MistakeDraft;

      if (isEditMode && mistakeId) {
        await updateMistake(mistakeId, draftToUpdatePayload(payload));
        showToast("success", t("editor.updateSuccess"));
      } else {
        await createMistake(draftToCreatePayload(payload));
        showToast("success", t("editor.createSuccess"));
      }

      clearDraft(draftKey);
      navigate("/mistakes");
    } catch (saveError) {
      if (saveError instanceof Error && saveError.message === "Category is required.") {
        showToast("error", t("editor.categoryRequired"));
      } else if (!(saveError instanceof Error && saveError.name === "Error" && saveError.message === "")) {
        showToast("error", saveError instanceof Error ? saveError.message : t("editor.saveFailed"));
      }
    } finally {
      setGlobalLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div className="page-title-copy">
          <Typography.Title level={2} style={{ margin: 0 }}>
            {isEditMode ? t("editor.titleEdit") : t("editor.titleCreate")}
          </Typography.Title>
          <p className="page-subtitle">{t("editor.subtitle")}</p>
        </div>
        <Space>
          <Button onClick={() => navigate("/mistakes")}>{t("common.back")}</Button>
          <Button type="primary" onClick={() => void handleSave()}>
            {t("common.save")}
          </Button>
        </Space>
      </div>

      {!isEditMode && <ProblemUrlImporter onFilled={handleUrlFilled} />}
      <Card className="panel-card" loading={loading}>
        <Form<MistakeDraft>
          layout="vertical"
          form={form}
          initialValues={stableInitialValues}
          onValuesChange={(_, allValues) => patchDraft(draftKey, allValues as Partial<MistakeDraft>)}
        >
          <Form.Item name="title" label={t("editor.fieldTitle")} rules={[{ required: true }, { max: 200 }]}>
            <Input size="large" placeholder={t("editor.titlePlaceholder")} />
          </Form.Item>

          <Form.Item name="stem_markdown" label={t("editor.fieldStem")}>
            <Input.TextArea rows={5} placeholder={t("editor.stemPlaceholder")} />
          </Form.Item>

          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item name="category_id" label={t("editor.fieldCategory")} rules={[{ required: true }]}>
                <Select
                  placeholder={t("editor.categoryPlaceholder")}
                  options={categories.map((category) => ({
                    label: category.name,
                    value: category.id,
                  }))}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: "8px 0" }} />
                      <Space style={{ padding: "0 8px 4px", width: "100%" }}>
                        <Input
                          ref={newCategoryInputRef}
                          placeholder={t("editor.categoryAddPlaceholder")}
                          value={newCategoryName}
                          onChange={(e) => setNewCategoryName(e.target.value)}
                          onKeyDown={(e) => {
                            e.stopPropagation();
                            if (e.key === "Enter") {
                              void handleAddCategory(e);
                            }
                          }}
                        />
                        <Button
                          type="text"
                          icon={<PlusOutlined />}
                          loading={addingCategory}
                          onClick={(e) => void handleAddCategory(e)}
                        >
                          {t("editor.categoryAddButton")}
                        </Button>
                      </Space>
                    </>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="tags" label={t("editor.fieldTags")}>
                <Select
                  mode="tags"
                  tokenSeparators={[","]}
                  placeholder={t("editor.tagsPlaceholder")}
                  options={tagOptions}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={4}>
              <Form.Item name="language" label={t("editor.fieldLanguage")} rules={[{ required: true }]}>
                <Select options={languageOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={4}>
              <Form.Item name="difficulty" label={t("editor.fieldDifficulty")} rules={[{ required: true }]}>
                <Rate count={5} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="source" label={t("editor.fieldSource")}>
            <Input placeholder={t("editor.sourcePlaceholder")} />
          </Form.Item>

          <div className="editor-grid">
            <Form.Item
              name="wrong_answer_markdown"
              label={t("editor.fieldWrongAnswer")}
              rules={[{ required: true, message: t("editor.wrongAnswerRequired") }]}
            >
              <AnswerCodeEditor language={editorLanguage} height={400} theme={monacoTheme} />
            </Form.Item>
            <Form.Item
              name="correct_answer_markdown"
              label={
                <Space size="small" align="center">
                  <span>{t("editor.fieldCorrectAnswer")}</span>
                  <Button
                    size="small"
                    type="link"
                    icon={<RobotOutlined />}
                    loading={generatingAnswer}
                    onClick={() => void handleGenerateCorrectAnswer()}
                  >
                    {t("editor.generateCorrectAnswer")}
                  </Button>
                </Space>
              }
              rules={[{ required: true, message: t("editor.correctAnswerRequired") }]}
            >
              <AnswerCodeEditor language={editorLanguage} height={400} theme={monacoTheme} />
            </Form.Item>
          </div>

          <Form.Item name="error_reason_markdown" label={t("editor.fieldErrorReason")}>
            <Input.TextArea rows={6} placeholder={t("editor.errorReasonPlaceholder")} />
          </Form.Item>

          <Space>
            <Button onClick={() => navigate("/mistakes")}>{t("common.cancel")}</Button>
            <Button type="primary" onClick={() => void handleSave()}>
              {t("common.save")}
            </Button>
          </Space>
        </Form>
      </Card>
    </div>
  );
}

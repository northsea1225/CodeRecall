import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Empty,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { deleteMistake } from "../../services/mistakeService";
import { listCategories } from "../../services/taxonomyService";
import { useMistakeStore } from "../../stores/mistakeStore";
import { useUIStore } from "../../stores/uiStore";
import type { Category, Mistake } from "../../types/mistake";

const formatDate = (value: string, locale: string): string =>
  new Date(value).toLocaleString(locale, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

export default function MistakeListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const language = useUIStore((state) => state.language);
  const list = useMistakeStore((state) => state.list);
  const filters = useMistakeStore((state) => state.filters);
  const pagination = useMistakeStore((state) => state.pagination);
  const loading = useMistakeStore((state) => state.loading);
  const error = useMistakeStore((state) => state.error);
  const fetchList = useMistakeStore((state) => state.fetchList);
  const setFilter = useMistakeStore((state) => state.setFilter);
  const showToast = useUIStore((state) => state.showToast);
  const setGlobalLoading = useUIStore((state) => state.setGlobalLoading);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filterLoading, setFilterLoading] = useState(true);

  const languageOptions = useMemo(() => [
    { label: t("mistakes.allLanguages"), value: undefined },
    { label: "Python", value: "python" },
    { label: "JavaScript", value: "javascript" },
    { label: "TypeScript", value: "typescript" },
    { label: "Java", value: "java" },
    { label: "Go", value: "go" },
    { label: "Rust", value: "rust" },
    { label: "SQL", value: "sql" },
    { label: "C++", value: "cpp" },
  ], [t]);

  useEffect(() => {
    void fetchList();
  }, [fetchList, filters.page, filters.pageSize, filters.categoryId, filters.keyword, filters.language]);

  useEffect(() => {
    let active = true;

    const loadCategories = async () => {
      setFilterLoading(true);
      try {
        const response = await listCategories();
        if (active) {
          setCategories(response.items);
        }
      } catch (categoryError) {
        if (active) {
          showToast("error", categoryError instanceof Error ? categoryError.message : t("mistakes.loadCategoriesFailed"));
        }
      } finally {
        if (active) {
          setFilterLoading(false);
        }
      }
    };

    void loadCategories();

    return () => {
      active = false;
    };
  }, [showToast, t]);

  const columns: ColumnsType<Mistake> = useMemo(
    () => [
      {
        title: t("mistakes.colTitle"),
        dataIndex: "title",
        key: "title",
        render: (_, record) => (
          <div>
            <Typography.Text strong>{record.title}</Typography.Text>
            <div className="soft-note">{record.source || t("mistakes.unknownSource")}</div>
          </div>
        ),
      },
      {
        title: t("mistakes.colLanguage"),
        dataIndex: "language",
        key: "language",
        width: 120,
        render: (value: string) => <Tag>{value}</Tag>,
      },
      {
        title: t("mistakes.colDifficulty"),
        dataIndex: "difficulty",
        key: "difficulty",
        width: 120,
      },
      {
        title: t("mistakes.colCategory"),
        key: "category",
        width: 180,
        render: (_, record) => record.category.name,
      },
      {
        title: t("mistakes.colUpdated"),
        dataIndex: "updated_at",
        key: "updated_at",
        width: 180,
        render: (value: string) => formatDate(value, language),
      },
      {
        title: t("mistakes.colActions"),
        key: "actions",
        width: 180,
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => navigate(`/mistakes/${record.id}/edit`)}>
              {t("common.edit")}
            </Button>
            <Popconfirm title={t("mistakes.deleteConfirm")} onConfirm={() => void handleDelete(record.id)}>
              <Button size="small" danger>
                {t("common.delete")}
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [navigate, t, language],
  );

  const handleDelete = async (id: number) => {
    setGlobalLoading(true);
    try {
      await deleteMistake(id);
      showToast("success", t("mistakes.deleteSuccess"));
      if (list.length === 1 && filters.page > 1) {
        setFilter({ page: filters.page - 1 });
      } else {
        await fetchList();
      }
    } catch (deleteError) {
      showToast("error", deleteError instanceof Error ? deleteError.message : t("mistakes.deleteFailed"));
    } finally {
      setGlobalLoading(false);
    }
  };

  const handlePaginationChange = (nextPagination: TablePaginationConfig) => {
    setFilter({
      page: nextPagination.current ?? 1,
      pageSize: nextPagination.pageSize ?? filters.pageSize,
    });
  };

  const keyword = filters.keyword.trim();
  const hasSearchEmpty = !loading && list.length === 0 && keyword.length > 0;
  const hasFilterEmpty = !loading && list.length === 0 && !keyword && Boolean(filters.categoryId || filters.language);
  const emptyState = hasSearchEmpty
    ? {
        title: t("mistakes.emptySearchTitle"),
        description: t("mistakes.emptySearchDesc"),
        cta: t("mistakes.emptySearchAction"),
        action: () => setFilter({ keyword: "" }),
      }
    : hasFilterEmpty
      ? {
          title: t("mistakes.emptyFilterTitle"),
          description: t("mistakes.emptyFilterDesc"),
          cta: t("mistakes.emptyFilterAction"),
          action: () => setFilter({ categoryId: undefined, language: undefined }),
        }
      : null;

  const totalPages = Math.max(Math.ceil(pagination.total / pagination.page_size), 1);

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div className="page-title-copy">
          <Typography.Title level={2} style={{ margin: 0 }}>
            {t("mistakes.title")}
          </Typography.Title>
          <p className="page-subtitle">{t("mistakes.subtitle")}</p>
        </div>
        <Button type="primary" onClick={() => navigate("/mistakes/new")}>
          {t("mistakes.newButton")}
        </Button>
      </div>

      <Space wrap size="middle" className="mistake-toolbar">
        <Select
          loading={filterLoading}
          placeholder={t("mistakes.allCategories")}
          style={{ minWidth: 220 }}
          value={filters.categoryId}
          onChange={(value) => setFilter({ categoryId: value })}
          options={[
            { label: t("mistakes.allCategories"), value: undefined },
            ...categories.map((category) => ({
              label: category.name,
              value: category.id,
            })),
          ]}
        />
        <Select
          placeholder={t("mistakes.allLanguages")}
          style={{ minWidth: 180 }}
          value={filters.language}
          onChange={(value) => setFilter({ language: value })}
          options={languageOptions}
        />
        <Input
          allowClear
          placeholder={t("mistakes.searchPlaceholder")}
          style={{ minWidth: 260 }}
          value={filters.keyword}
          onChange={(event) => setFilter({ keyword: event.target.value })}
        />
        {(filters.keyword || filters.categoryId || filters.language) && (
          <Button onClick={() => setFilter({ keyword: "", categoryId: undefined, language: undefined })}>
            {t("mistakes.resetFilters")}
          </Button>
        )}
      </Space>

      {error ? <Alert type="error" message={error} showIcon /> : null}

      <Table<Mistake>
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={list}
        pagination={{
          current: Math.min(pagination.page, totalPages),
          pageSize: pagination.page_size,
          total: pagination.total,
          showSizeChanger: true,
        }}
        locale={{
          emptyText: emptyState ? (
            <Empty
              className="mistake-empty"
              description={
                <Space direction="vertical" size={4}>
                  <Typography.Text strong>{emptyState.title}</Typography.Text>
                  <Typography.Text className="soft-note">{emptyState.description}</Typography.Text>
                </Space>
              }
            >
              <Button onClick={emptyState.action}>{emptyState.cta}</Button>
            </Empty>
          ) : (
            <Empty description={loading ? t("mistakes.emptyLoading") : t("mistakes.emptyNoData")} />
          ),
        }}
        onChange={handlePaginationChange}
      />
    </div>
  );
}

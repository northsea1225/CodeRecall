from urllib import parse

from tests.test_api_contract_day3 import APIServerTestCase


class SearchFilterDay6Tests(APIServerTestCase):
    def _create_category(self, *, name: str) -> dict:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {
                "name": name,
                "description": f"{name} 分类",
            },
        )
        self.assertEqual(status, 201, category)
        return category

    def _create_mistake(
        self,
        *,
        category_id: int,
        title: str,
        stem_markdown: str,
        wrong_answer_markdown: str = "wrong",
        correct_answer_markdown: str = "correct",
        error_reason_markdown: str = "reason",
        language: str = "python",
    ) -> dict:
        status, mistake, _ = self.request(
            "POST",
            "/api/v1/mistakes",
            {
                "title": title,
                "stem_markdown": stem_markdown,
                "wrong_answer_markdown": wrong_answer_markdown,
                "correct_answer_markdown": correct_answer_markdown,
                "error_reason_markdown": error_reason_markdown,
                "language": language,
                "difficulty": 2,
                "source": "LeetCode",
                "status": "new",
                "category_id": category_id,
                "tags": [],
            },
        )
        self.assertEqual(status, 201, mistake)
        return mistake

    def test_keyword_and_category_filters_compose(self) -> None:
        python_category = self._create_category(name="Python")
        javascript_category = self._create_category(name="JavaScript")
        target = self._create_mistake(
            category_id=python_category["id"],
            title="Python 字典边界遗漏",
            stem_markdown="处理 python 字典时漏掉默认值。",
        )
        self._create_mistake(
            category_id=javascript_category["id"],
            title="Python 事件循环误判",
            stem_markdown="关键词相同但分类不同。",
            language="javascript",
        )
        self._create_mistake(
            category_id=python_category["id"],
            title="双指针错位",
            stem_markdown="分类相同但没有关键字。",
        )

        query = parse.urlencode(
            {
                "page": 1,
                "page_size": 10,
                "category_id": python_category["id"],
                "keyword": "python",
            }
        )
        status, payload, _ = self.request("GET", f"/api/v1/mistakes?{query}")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["total"], 1)
        self.assertEqual([item["id"] for item in payload["items"]], [target["id"]])

    def test_keyword_and_language_filters_compose(self) -> None:
        category = self._create_category(name="字符串")
        target = self._create_mistake(
            category_id=category["id"],
            title="窗口滑动条件错误",
            stem_markdown="python 版本窗口条件遗漏。",
            language="python",
        )
        self._create_mistake(
            category_id=category["id"],
            title="窗口滑动条件错误",
            stem_markdown="javascript 版本窗口条件遗漏。",
            language="javascript",
        )
        self._create_mistake(
            category_id=category["id"],
            title="数组越界",
            stem_markdown="python 版本但关键字不同。",
            language="python",
        )

        query = parse.urlencode(
            {
                "page": 1,
                "page_size": 10,
                "language": "python",
                "keyword": "窗口",
            }
        )
        status, payload, _ = self.request("GET", f"/api/v1/mistakes?{query}")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["total"], 1)
        self.assertEqual([item["id"] for item in payload["items"]], [target["id"]])

    def test_empty_keyword_matches_same_result_as_omitted_keyword(self) -> None:
        category = self._create_category(name="二分")
        first = self._create_mistake(
            category_id=category["id"],
            title="二分边界遗漏",
            stem_markdown="左边界更新错误。",
        )
        second = self._create_mistake(
            category_id=category["id"],
            title="二分死循环",
            stem_markdown="mid 偏移错误。",
        )

        status_without, payload_without, _ = self.request("GET", "/api/v1/mistakes?page=1&page_size=10")
        status_blank, payload_blank, _ = self.request("GET", "/api/v1/mistakes?page=1&page_size=10&keyword=")

        self.assertEqual(status_without, 200, payload_without)
        self.assertEqual(status_blank, 200, payload_blank)
        self.assertEqual(payload_without["total"], 2)
        self.assertEqual(payload_blank["total"], 2)
        self.assertEqual({item["id"] for item in payload_blank["items"]}, {first["id"], second["id"]})

    def test_multi_keyword_requires_all_terms_across_searchable_fields(self) -> None:
        category = self._create_category(name="位运算")
        target = self._create_mistake(
            category_id=category["id"],
            title="binary search 边界误判",
            stem_markdown="先定位收缩区间。",
            error_reason_markdown="overflow 风险没有处理。",
        )
        self._create_mistake(
            category_id=category["id"],
            title="binary search 模板混淆",
            stem_markdown="只有 binary 没有第二个词。",
            error_reason_markdown="区间闭合错误。",
        )
        self._create_mistake(
            category_id=category["id"],
            title="整数溢出",
            stem_markdown="只有 overflow 没有第一个词。",
            error_reason_markdown="边界值超限。",
        )

        query = parse.urlencode(
            {
                "page": 1,
                "page_size": 10,
                "keyword": "binary overflow",
            }
        )
        status, payload, _ = self.request("GET", f"/api/v1/mistakes?{query}")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["total"], 1)
        self.assertEqual([item["id"] for item in payload["items"]], [target["id"]])

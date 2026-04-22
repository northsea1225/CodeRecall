from tests.test_api_contract_day3 import APIServerTestCase


class ReviewCapabilityFeatureDisabledTests(APIServerTestCase):
    def extra_env(self) -> dict[str, str]:
        return {
            "ENABLE_AI_ANALYSIS": "false",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "gpt-5.4-mini",
        }

    def test_review_capability_reports_ai_disabled_when_feature_flag_is_off(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/review/capability")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload, {"ai_analysis_enabled": False})

    def test_ai_stream_returns_503_when_feature_flag_is_off(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/ai/analyze/stream?mistake_id=1")

        self.assertEqual(status, 503, payload)
        self.assertEqual(payload["code"], "ai_analysis_disabled")


class ReviewCapabilityMissingKeyTests(APIServerTestCase):
    def extra_env(self) -> dict[str, str]:
        return {
            "ENABLE_AI_ANALYSIS": "true",
            "LLM_API_KEY": "",
            "LLM_MODEL": "gpt-5.4-mini",
        }

    def test_review_capability_reports_ai_disabled_when_api_key_is_blank(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/review/capability")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload, {"ai_analysis_enabled": False})

    def test_ai_stream_returns_503_when_api_key_is_blank(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/ai/analyze/stream?mistake_id=1")

        self.assertEqual(status, 503, payload)
        self.assertEqual(payload["code"], "ai_analysis_disabled")


class ReviewCapabilityEnabledTests(APIServerTestCase):
    def extra_env(self) -> dict[str, str]:
        return {
            "ENABLE_AI_ANALYSIS": "true",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "gpt-5.4-mini",
        }

    def test_review_capability_reports_ai_enabled_when_flag_and_key_exist(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/review/capability")

        self.assertEqual(status, 200, payload)
        self.assertEqual(
            payload,
            {
                "ai_analysis_enabled": True,
                "model": "gpt-5.4-mini",
            },
        )

    def test_ai_stream_returns_404_for_missing_mistake_when_ai_is_enabled(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/ai/analyze/stream?mistake_id=999")

        self.assertEqual(status, 404, payload)
        self.assertEqual(payload["code"], "mistake_not_found")

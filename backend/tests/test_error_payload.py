import unittest

from pydantic import ValidationError

from app.api.errors import ApiErrorOut, error_payload


class ErrorPayloadShapeTests(unittest.TestCase):
    def test_none_detail_is_normalized_to_empty_dict(self) -> None:
        # Backward compat: callers and clients have historically seen
        # detail={} when no detail was supplied.
        payload = error_payload("foo", "bar")
        self.assertEqual(payload, {"code": "foo", "message": "bar", "detail": {}})

    def test_dict_detail_passes_through(self) -> None:
        payload = error_payload("foo", "bar", {"x": 1, "y": "z"})
        self.assertEqual(payload["detail"], {"x": 1, "y": "z"})

    def test_list_of_dict_detail_passes_through(self) -> None:
        payload = error_payload("foo", "bar", [{"loc": ["body", "x"], "msg": "bad"}])
        self.assertEqual(
            payload["detail"], [{"loc": ["body", "x"], "msg": "bad"}]
        )

    def test_envelope_keys_are_exhaustive(self) -> None:
        payload = error_payload("foo", "bar", {"x": 1})
        self.assertEqual(set(payload.keys()), {"code", "message", "detail"})


class ApiErrorOutValidationTests(unittest.TestCase):
    def test_string_detail_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ApiErrorOut(code="x", message="y", detail="not-a-dict-or-list")  # type: ignore[arg-type]

    def test_int_detail_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ApiErrorOut(code="x", message="y", detail=42)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

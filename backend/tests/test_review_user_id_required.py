"""Fuse tests: confirm review service entry points reject calls that omit user_id.

These cover the C-001 batch A invariant — every review service function must
take ``user_id`` as a keyword-only argument with no default. If a caller
forgets it, Python raises TypeError before the function body runs, which is
exactly the desired fail-fast behavior. We use ``MagicMock`` for the DB
because the parameter check happens during call binding, well before any DB
access.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models import ReviewResult
from app.services.review import get_summary, start_session, submit_result


def test_start_session_requires_user_id_keyword() -> None:
    db_stub = MagicMock()
    with pytest.raises(TypeError):
        start_session(db_stub, "due_first", 5)  # type: ignore[call-arg]


def test_submit_result_requires_user_id_keyword() -> None:
    db_stub = MagicMock()
    with pytest.raises(TypeError):
        submit_result(db_stub, 1, 1, ReviewResult.GOOD)  # type: ignore[call-arg]


def test_get_summary_requires_user_id_keyword() -> None:
    db_stub = MagicMock()
    with pytest.raises(TypeError):
        get_summary(db_stub, 1)  # type: ignore[call-arg]

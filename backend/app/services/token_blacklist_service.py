from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import TokenJtiBlacklist


def is_jti_blacklisted(db: Session, jti: str) -> bool:
    return db.get(TokenJtiBlacklist, jti) is not None


def revoke_jti(db: Session, *, jti: str, user_id: int, exp_at: datetime) -> None:
    if db.get(TokenJtiBlacklist, jti) is not None:
        return
    db.add(TokenJtiBlacklist(jti=jti, user_id=user_id, exp_at=exp_at))
    db.commit()


def cleanup_expired_blacklisted_jtis(
    db: Session,
    *,
    now: datetime | None = None,
    batch_size: int = 500,
) -> int:
    cutoff = now or datetime.now(timezone.utc)
    expired_jtis = list(
        db.scalars(
            select(TokenJtiBlacklist.jti)
            .where(TokenJtiBlacklist.exp_at < cutoff)
            .order_by(TokenJtiBlacklist.exp_at)
            .limit(batch_size)
        )
    )
    if not expired_jtis:
        return 0
    db.execute(delete(TokenJtiBlacklist).where(TokenJtiBlacklist.jti.in_(expired_jtis)))
    db.commit()
    return len(expired_jtis)


_last_cleanup_at: datetime | None = None


def maybe_cleanup_blacklist(db: Session, *, interval_seconds: int, batch_size: int = 500) -> int:
    global _last_cleanup_at
    now = datetime.now(timezone.utc)
    if _last_cleanup_at is not None and now - _last_cleanup_at < timedelta(seconds=interval_seconds):
        return 0
    _last_cleanup_at = now
    return cleanup_expired_blacklisted_jtis(db, now=now, batch_size=batch_size)

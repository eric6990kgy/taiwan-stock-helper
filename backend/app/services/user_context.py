"""V1 has no auth (architecture decision A8) — there is exactly one seeded
User row. This stands in for "the current user" everywhere a user_id is
needed, so routes/schemas never have to accept one from the client."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.exceptions import NotFoundError


def get_current_user_id(db: Session) -> int:
    user = db.execute(select(User)).scalars().first()
    if user is None:
        raise NotFoundError("No user exists yet. Run the database seed script first.")
    return user.id

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RoundRobinState


def make_db_picker(db: Session):
    """Round-robin whose counter lives in Postgres.

    SELECT ... FOR UPDATE serializes concurrent workers on the team row
    (SQLite ignores the lock, which is fine for tests).
    """

    def pick(team: str, reps: list[str]) -> str:
        state = db.scalar(
            select(RoundRobinState).where(RoundRobinState.team == team).with_for_update()
        )
        if state is None:
            state = RoundRobinState(team=team, counter=0)
            db.add(state)
            db.flush()
        rep = reps[state.counter % len(reps)]
        state.counter += 1
        return rep

    return pick

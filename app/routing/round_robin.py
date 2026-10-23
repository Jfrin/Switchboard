from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import RoundRobinState


def make_db_picker(db: Session):
    """Round-robin whose counter lives in Postgres.

    SELECT ... FOR UPDATE serializes concurrent workers on the team row
    (SQLite ignores the lock, which is fine for tests). The very first lead for a
    team has no row to lock, so two workers can both try to insert it; the loser
    hits the primary key, rolls back its savepoint and locks the winner's row.
    """

    def locked_state(team: str) -> RoundRobinState | None:
        return db.scalar(
            select(RoundRobinState).where(RoundRobinState.team == team).with_for_update()
        )

    def pick(team: str, reps: list[str]) -> str:
        state = locked_state(team)
        if state is None:
            try:
                with db.begin_nested():
                    state = RoundRobinState(team=team, counter=0)
                    db.add(state)
            except IntegrityError:
                state = locked_state(team)
                if state is None:
                    raise
        rep = reps[state.counter % len(reps)]
        state.counter += 1
        return rep

    return pick

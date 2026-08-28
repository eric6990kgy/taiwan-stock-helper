"""Portfolio calculation engine.

Deliberately independent of FastAPI, SQLAlchemy, HTTP, and the database:
every function here takes plain dataclasses/Decimals in and returns plain
dataclasses/Decimals out. This is what keeps it unit-testable without a DB
and reusable later by a rule/signal engine or a Claude-based analysis
service (V4+) without going through the REST API.
"""

from app.analytics.types import Position, TransactionInput, ValuedPosition
from app.analytics.exceptions import InsufficientSharesError, MixedPositionError
from app.analytics.cost_basis import calculate_positions, replay_transactions
from app.analytics.valuation import calculate_market_value, calculate_unrealized_pnl, calculate_return_pct, value_position
from app.analytics.portfolio import calculate_portfolio_weight, summarize_portfolio

__all__ = [
    "Position",
    "TransactionInput",
    "ValuedPosition",
    "InsufficientSharesError",
    "MixedPositionError",
    "calculate_positions",
    "replay_transactions",
    "calculate_market_value",
    "calculate_unrealized_pnl",
    "calculate_return_pct",
    "value_position",
    "calculate_portfolio_weight",
    "summarize_portfolio",
]

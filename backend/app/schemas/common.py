"""Shared schema building blocks. DecimalStr forces every money/quantity
field to serialize as a JSON string (exact digits preserved) instead of a
JSON number, so clients never have to round-trip financial values through
JS floats. Input still accepts a plain JSON number or string — Pydantic
coerces either into Decimal — but callers should send strings to avoid
handing a float-imprecise number in the first place.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

DecimalStr = Annotated[Decimal, PlainSerializer(lambda v: str(v), return_type=str, when_used="json")]

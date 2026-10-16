from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str
    email: str
    created_at: datetime

from models.Base import BaseModel
from enum import Enum
from dataclasses import dataclass, field
from models.Stock import Stock
from typing import Optional

@dataclass
class Position:
    stockid: int
    quantity: int
    distribution_target: Optional[float] = field(default=None)
    distribution_real: float = field(default=0.0)
    stock: Optional['Stock'] = field(default=None)

    def delta(self):
        return (self.distribution_target or 0.0) - self.distribution_real

    @classmethod
    def dataclass_factory(cls, cursor, row):
        fields = [column[0] for column in cursor.description]
        return Position(**{k: v for k, v in zip(fields, row)})


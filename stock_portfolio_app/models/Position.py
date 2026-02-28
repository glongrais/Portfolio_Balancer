from dataclasses import dataclass, field
from models.Stock import Stock
from typing import Optional

@dataclass
class Position:
    stockid: int
    quantity: float
    portfolio_id: int = field(default=1)
    average_cost_basis: Optional[float] = field(default=None)
    distribution_target: Optional[float] = field(default=None)
    distribution_real: float = field(default=0.0)
    stock: Optional['Stock'] = field(default=None)


    def delta(self):
        return (self.distribution_target or 0.0) - (self.distribution_real or 0.0)

    @classmethod
    def dataclass_factory(cls, cursor, row):
        fields = [column[0] for column in cursor.description]
        return Position(**{k: v for k, v in zip(fields, row)})


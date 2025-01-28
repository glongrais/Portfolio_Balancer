from services.data_processing import DataProcessing
from dataclasses import dataclass, field

@dataclass
class Stock:
    stockid: int
    symbol: str
    name: str = field(default="")
    price: float = field(default=0.0)
    dividend: float = field(default=0.0)
    dividend_yield: float = field(default=0.0)

    @classmethod
    def dataclass_factory(cls, cursor, row):
        fields = [column[0] for column in cursor.description]
        return Stock(**{k: v for k, v in zip(fields, row)})

from dataclasses import dataclass

@dataclass
class Stock:

    name: str
    symbol: str
    price: float
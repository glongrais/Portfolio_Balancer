from dataclasses import dataclass, field

@dataclass
class Stock:

    name: str = field(default="default")
    symbol: str = field(default="default")
    price: float = field(default=1.0)
    quantity: int = field(default=0)
    distribution_target: float = field(default=1.0)
    distribution_real: float = field(default=1.0)

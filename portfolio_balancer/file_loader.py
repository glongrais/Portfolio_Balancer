from portfolio_balancer.stock import Stock
import json

def load_file(filename: str) -> list[Stock]:
    f = open(filename)
    data = json.load(f)
    return [Stock(**i) for i in data]
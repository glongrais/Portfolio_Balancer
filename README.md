# Portfolio Balancing

Read a stock portfolio from either a JSON or Numbers file and calculate the number of shares to buy based on the specified investment amount.

## Status

![test status](https://github.com/glongrais/Portfolio_Balancer/actions/workflows/tests.yaml/badge.svg)

Run example:  
`python3 -m portfolio_balancer.balancer -f test.json -a 500 -fs`

JSON Input example:
````JSON
[
    {
        "symbol":"AAPl",
        "quantity":1,
        "distribution_target":10.0 
    },
    {
        "symbol":"MSFT",
        "quantity":1,
        "distribution_target":7.5
    },
    ...
]
````
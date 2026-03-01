from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(0.1, 1)

    @task
    def get_value(self):
        self.client.get("/api/v1/portfolios/1/value")

    @task
    def get_transactions(self):
        self.client.get("/api/v1/portfolios/1/transactions/")

    @task
    def get_net_worth(self):
        self.client.get("/api/v1/net-worth/current")

    @task
    def get_net_equity(self):
        self.client.get("/api/v1/equity/summary")

    @task
    def get_net_equity_history(self):
        self.client.get("/api/v1/equity/history?start_date=2026-01-01&end_date=2026-02-25")

    @task
    def get_stocks(self):
        self.client.get("/api/v1/stocks/")

    @task
    def post_balance(self):
        self.client.post("/api/v1/portfolios/1/balance", json={"amount_to_buy": 1000,
                                                               "min_amount_to_buy": 100,
                                                               "strategy": "proportional"})
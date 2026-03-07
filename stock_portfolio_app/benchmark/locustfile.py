import os
import random
from datetime import date, timedelta

from locust import HttpUser, between, task


class ApiUser(HttpUser):
    wait_time = between(0.1, 1.0)

    # read_heavy (default): no write endpoints.
    # mixed: includes a few controlled writes for clone DB only.
    profile = os.getenv("PERF_PROFILE", "read_heavy").strip().lower()
    portfolio_ids = [1, 2, 3]

    # (method_name, weight)
    read_heavy_actions = [
        ("get_health", 1),
        ("get_portfolio_positions", 7),
        ("get_portfolio_value", 8),
        ("get_portfolio_transactions", 6),
        ("get_portfolio_transaction_summary", 4),
        ("get_portfolio_deposits", 3),
        ("get_portfolio_total_deposits", 3),
        ("get_net_worth_current", 6),
        ("get_net_worth_history", 4),
        ("get_equity_summary", 4),
        ("get_equity_history", 3),
        ("get_savings_summary", 3),
        ("get_savings_history", 2),
        ("get_crypto_summary", 2),
        ("get_crypto_history", 2),
        ("get_stocks", 6),
    ]
    mixed_extra_actions = [
        ("post_portfolio_balance", 2),
        ("post_portfolio_transaction", 2),
        ("post_portfolio_deposit", 1),
    ]

    @classmethod
    def _date_range(cls):
        today = date.today()
        start = today - timedelta(days=365)
        return start.isoformat(), today.isoformat()

    def _pick_portfolio(self):
        return random.choice(self.portfolio_ids)

    def on_start(self):
        if self.profile not in ("read_heavy", "mixed"):
            self.profile = "read_heavy"
        self.read_actions = list(self.read_heavy_actions)
        if self.profile == "mixed":
            self.read_actions.extend(self.mixed_extra_actions)

    @task
    def perform_profile_action(self):
        action, _ = random.choices(
            self.read_actions,
            weights=[weight for _, weight in self.read_actions],
            k=1,
        )[0]
        getattr(self, action)()

    def get_health(self):
        self.client.get("/api/health", name="GET /api/health")

    def get_portfolio_positions(self):
        pid = self._pick_portfolio()
        self.client.get(
            f"/api/v1/portfolios/{pid}/positions",
            name="GET /api/v1/portfolios/{portfolio_id}/positions",
        )

    def get_portfolio_value(self):
        pid = self._pick_portfolio()
        self.client.get(
            f"/api/v1/portfolios/{pid}/value",
            name="GET /api/v1/portfolios/{portfolio_id}/value",
        )

    def get_portfolio_transactions(self):
        pid = self._pick_portfolio()
        self.client.get(
            f"/api/v1/portfolios/{pid}/transactions/?limit=100",
            name="GET /api/v1/portfolios/{portfolio_id}/transactions/",
        )

    def get_portfolio_transaction_summary(self):
        pid = self._pick_portfolio()
        self.client.get(
            f"/api/v1/portfolios/{pid}/transactions/summary",
            name="GET /api/v1/portfolios/{portfolio_id}/transactions/summary",
        )

    def get_portfolio_deposits(self):
        pid = self._pick_portfolio()
        self.client.get(
            f"/api/v1/portfolios/{pid}/deposits/?limit=100",
            name="GET /api/v1/portfolios/{portfolio_id}/deposits/",
        )

    def get_portfolio_total_deposits(self):
        pid = self._pick_portfolio()
        self.client.get(
            f"/api/v1/portfolios/{pid}/deposits/total",
            name="GET /api/v1/portfolios/{portfolio_id}/deposits/total",
        )

    def get_net_worth_current(self):
        self.client.get("/api/v1/net-worth/current", name="GET /api/v1/net-worth/current")

    def get_net_worth_history(self):
        start_date, end_date = self._date_range()
        self.client.get(
            f"/api/v1/net-worth/history?start_date={start_date}&end_date={end_date}",
            name="GET /api/v1/net-worth/history",
        )

    def get_equity_summary(self):
        self.client.get("/api/v1/equity/summary", name="GET /api/v1/equity/summary")

    def get_equity_history(self):
        start_date, end_date = self._date_range()
        self.client.get(
            f"/api/v1/equity/history?start_date={start_date}&end_date={end_date}",
            name="GET /api/v1/equity/history",
        )

    def get_savings_summary(self):
        self.client.get("/api/v1/savings/summary", name="GET /api/v1/savings/summary")

    def get_savings_history(self):
        start_date, end_date = self._date_range()
        self.client.get(
            f"/api/v1/savings/history?start_date={start_date}&end_date={end_date}",
            name="GET /api/v1/savings/history",
        )

    def get_crypto_summary(self):
        self.client.get("/api/v1/crypto/summary", name="GET /api/v1/crypto/summary")

    def get_crypto_history(self):
        start_date, end_date = self._date_range()
        self.client.get(
            f"/api/v1/crypto/history?start_date={start_date}&end_date={end_date}",
            name="GET /api/v1/crypto/history",
        )

    def get_stocks(self):
        self.client.get("/api/v1/stocks/", name="GET /api/v1/stocks/")

    def post_portfolio_balance(self):
        pid = self._pick_portfolio()
        self.client.post(
            f"/api/v1/portfolios/{pid}/balance",
            name="POST /api/v1/portfolios/{portfolio_id}/balance",
            json={
                "amount_to_buy": random.choice([1000, 2000, 3000]),
                "min_amount_to_buy": 100,
                "strategy": "proportional",
            },
        )

    def post_portfolio_transaction(self):
        pid = self._pick_portfolio()
        tx_date = date.today().isoformat()
        self.client.post(
            f"/api/v1/portfolios/{pid}/transactions/",
            name="POST /api/v1/portfolios/{portfolio_id}/transactions/",
            json={
                "symbol": "AAPL",
                "quantity": 1,
                "price": 100,
                "type": "BUY",
                "date": tx_date,
            },
        )

    def post_portfolio_deposit(self):
        pid = self._pick_portfolio()
        self.client.post(
            f"/api/v1/portfolios/{pid}/deposits/",
            name="POST /api/v1/portfolios/{portfolio_id}/deposits/",
            json={
                "datestamp": date.today().isoformat(),
                "amount": 100,
            },
        )
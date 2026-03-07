# Benchmark Run Summaries

This file is append-only and tracks benchmark outcomes over time.

## 2026-03-07 18:56:09 - read_heavy

- **Config:** users=10, spawn_rate=5/s, duration=20s, api_port=8011
- **DB Clone:** `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/data/benchmark/portfolio_benchmark_20260307_185545.db`
- **Artifacts:** `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185545_read_heavy_stats.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185545_read_heavy_failures.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185545_read_heavy_stats_history.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185545_read_heavy.html`

| Metric | Value |
|---|---|
| Requests | 248 |
| Failures | 0 (0.00%) |
| RPS | 13.197746586237509 |
| p50 (ms) | 9 |
| p95 (ms) | 1100 |
| p99 (ms) | 1400 |

| Slow Endpoints (p95) | p95 (ms) | Failures |
|---|---|---|
| `GET /api/v1/net-worth/history` | 1500 | 0 |
| `GET /api/v1/equity/summary` | 1400 | 0 |
| `GET /api/v1/portfolios/{portfolio_id}/deposits/` | 1400 | 0 |
| `GET /api/v1/portfolios/{portfolio_id}/deposits/total` | 1400 | 0 |
| `GET /api/v1/net-worth/current` | 1300 | 0 |

## 2026-03-07 18:57:11 - mixed

- **Config:** users=25, spawn_rate=8/s, duration=45s, api_port=8012
- **DB Clone:** `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/data/benchmark/portfolio_benchmark_20260307_185623.db`
- **Artifacts:** `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185623_mixed_stats.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185623_mixed_failures.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185623_mixed_stats_history.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_185623_mixed.html`

| Metric | Value |
|---|---|
| Requests | 1135 |
| Failures | 0 (0.00%) |
| RPS | 25.979733621200086 |
| p50 (ms) | 210 |
| p95 (ms) | 1200 |
| p99 (ms) | 1800 |

| Slow Endpoints (p95) | p95 (ms) | Failures |
|---|---|---|
| `GET /api/v1/net-worth/history` | 1600 | 0 |
| `GET /api/v1/portfolios/{portfolio_id}/transactions/summary` | 1600 | 0 |
| `POST /api/v1/portfolios/{portfolio_id}/balance` | 1600 | 0 |
| `GET /api/v1/crypto/history` | 1500 | 0 |
| `POST /api/v1/portfolios/{portfolio_id}/transactions/` | 1400 | 0 |

## 2026-03-07 19:06:14 - mixed

- **Config:** users=100, spawn_rate=20/s, duration=5m, api_port=8013
- **DB Clone:** `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/data/benchmark/portfolio_benchmark_20260307_190111.db`
- **Artifacts:** `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_190111_mixed_stats.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_190111_mixed_failures.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_190111_mixed_stats_history.csv`, `/Users/guillaumel/Personal/GitHub/Portfolio_Balancer/stock_portfolio_app/benchmark/results/run_20260307_190111_mixed.html`

| Metric | Value |
|---|---|
| Requests | 11549 |
| Failures | 0 (0.00%) |
| RPS | 38.798235686249754 |
| p50 (ms) | 2100 |
| p95 (ms) | 4000 |
| p99 (ms) | 5300 |

| Slow Endpoints (p95) | p95 (ms) | Failures |
|---|---|---|
| `POST /api/v1/portfolios/{portfolio_id}/deposits/` | 5300 | 0 |
| `POST /api/v1/portfolios/{portfolio_id}/transactions/` | 4800 | 0 |
| `GET /api/v1/net-worth/history` | 4600 | 0 |
| `GET /api/v1/portfolios/{portfolio_id}/deposits/total` | 4400 | 0 |
| `GET /api/v1/portfolios/{portfolio_id}/transactions/summary` | 4100 | 0 |


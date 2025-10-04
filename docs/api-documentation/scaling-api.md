# Scaling API

Base path: /api/v1/scaling
Authentication: required

Endpoints
- GET /status — queue metrics, recommendation, config, history summary
  - Rate limit: analytics (100/hour, 500/day)
- GET /metrics — detailed queue metrics per queue
  - Rate limit: analytics (100/hour, 500/day)
- GET /recommendation — current scaling recommendation only
  - Rate limit: analytics (100/hour, 500/day)
- POST /execute — execute current recommendation
  - Rate limit: job control (50/hour, 200/day)
- POST /manual — set a target worker count (validates min/max)
  - Body: { target_workers: int, reason?: string }
  - Rate limit: job control (50/hour, 200/day)
- GET /config — get current scaling config
  - Rate limit: analytics (100/hour, 500/day)
- PUT /config — update scaling config (min/max/thresholds)
  - Body: { min_workers?, max_workers?, scale_up_threshold?, scale_down_threshold? }
  - Rate limit: user update (50/hour, 200/day)
- GET /history — recent scaling events (up to 50)
  - Rate limit: analytics (100/hour, 500/day)
- DELETE /history — clear scaling history
  - Rate limit: user delete (10/hour, 50/day)

Notes
- Backed by Redis for metrics and event history.
- See rate limits in `rate-limits.md`.

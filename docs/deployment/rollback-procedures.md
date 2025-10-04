# Rollback Procedures

When to rollback
- Sustained 5xx error rate
- Severe performance regression
- Critical security issue
- Data corruption risk

Steps
1) Identify the last known good image tag (e.g., latest prior successful prod-<sha>)
2) Update ECS service to use that image (or re-run CI with that tag)
3) Wait for healthy tasks; monitor `/health` and ALB metrics
4) If needed, scale down failing deployment
5) Communicate status and open a post-mortem

Verification
- Health green
- Error rate normal
- Latency acceptable

Notes
- Keep immutable ECR tags for traceability (prod-<sha>).

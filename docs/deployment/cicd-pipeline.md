# CI/CD Pipeline

Current state
- Branch: prod — on push/PR, builds and deploys to production (see .github/workflows/ci-cd.yml)
- Security scan job runs on PRs to prod
- No staging auto-deploy is configured at this time

Pipeline steps
1) Install dependencies
2) Basic import/health checks
3) Login to ECR
4) Build one Docker image, push with tags:
   - prod-<short_sha>, latest, prod
5) Cleanup ECR untagged/dash-tagged images
6) Verify image presence and update ECS task definitions
7) Force new deployment on ECS services

Key env in workflow
- AWS_REGION: us-east-1
- ECR_REPOSITORY: accunode
- ECS_CLUSTER: AccuNode-Production
- ECS services: accunode-api-service, accunode-worker-service

Triggers
- push to prod (deploy)
- pull_request to prod (scan/build only)

Notes
- Update this doc if staging workflow is added.

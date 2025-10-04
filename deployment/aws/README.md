# AWS Configuration for CI/CD

This folder contains AWS configuration files needed for CI/CD pipeline deployment.

## Files:

### `ci-cd-iam-policy.json`
**Purpose**: IAM policy with comprehensive permissions for CI/CD deployment

**Contains permissions for**:
- ECS (Elastic Container Service) - For container deployment
- ECR (Elastic Container Registry) - For Docker image storage
- VPC & Networking - For infrastructure management
- RDS - For database access
- ElastiCache - For Redis management
- IAM - For role management
- CloudWatch - For logging and monitoring
- Application Load Balancer - For traffic management

**Usage in CI/CD**:
This policy should be attached to the IAM user/role used by GitHub Actions for deployment.

## Setup for CI/CD:

1. **Create IAM User for CI/CD**:
   ```bash
   aws iam create-user --user-name accunode-cicd
   ```

2. **Attach Policy**:
   ```bash
   aws iam put-user-policy \
     --user-name accunode-cicd \
     --policy-name AccuNodeCICDPolicy \
     --policy-document file://aws/ci-cd-iam-policy.json
   ```

3. **Create Access Keys**:
   ```bash
   aws iam create-access-key --user-name accunode-cicd
   ```

4. **Add to GitHub Secrets**:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY` 
   - `AWS_REGION` (us-east-1)

## Security Notes:

- These permissions are comprehensive and should only be used for CI/CD deployment
- For production, consider using more restrictive policies
- Regularly rotate access keys
- Monitor CloudTrail for usage

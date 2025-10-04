# Self-Hosted GitHub Runner Setup

## Overview
Run your own GitHub Actions runner to avoid usage costs completely.

## Setup Steps

### 1. Create EC2 Instance (AWS Free Tier)
```bash
# t2.micro instance (free tier eligible)
# Ubuntu 22.04 LTS
# 1GB RAM, 8GB storage
# Security group: Allow SSH (22), HTTP (80), HTTPS (443)
```

### 2. Install GitHub Runner
```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Create runner user
sudo useradd -m runner
sudo usermod -aG docker runner
sudo su - runner

# Download and configure runner
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.310.2.tar.gz -L https://github.com/actions/runner/releases/download/v2.310.2/actions-runner-linux-x64-2.310.2.tar.gz
tar xzf ./actions-runner-linux-x64-2.310.2.tar.gz

# Configure (get token from GitHub repo Settings > Actions > Runners)
./config.sh --url https://github.com/betterresumes/default-rate-backend --token YOUR_TOKEN

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 3. Update Pipeline
```yaml
jobs:
  deploy-production:
    runs-on: self-hosted  # Instead of ubuntu-latest
    # ... rest of your job
```

## Benefits
- ✅ **FREE** - No GitHub Actions minutes used
- ✅ Faster builds (no cold starts)
- ✅ Persistent cache between builds
- ✅ Full control over environment

## Costs
- AWS EC2 t2.micro: FREE (first 12 months)
- After free tier: ~$8.50/month

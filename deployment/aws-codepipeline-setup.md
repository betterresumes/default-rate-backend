# AWS CodePipeline Alternative

## Overview
Use AWS native CI/CD services instead of GitHub Actions.

## Architecture & Flow
```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  GitHub  │───▶│  CodeCommit  │───▶│  CodeBuild   │───▶│ CodeDeploy/  │───▶│   ECS    │
│ (Source) │    │  (Mirror)    │    │   (Build)    │    │   Manual     │    │(Target)  │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
     │                │                     │                    │               │
     │          Triggers on      Builds Docker        Updates ECS        New Tasks
  Git Push         push           Image & Tests       Task Definitions      Running
```

## Pipeline Stages Explained

### Stage 1: Source
- **Trigger**: Git push to specified branch
- **Action**: Fetch latest code
- **Provider**: GitHub, CodeCommit, or S3

### Stage 2: Build  
- **Service**: AWS CodeBuild
- **Action**: Run buildspec.yml commands
- **Output**: Docker image pushed to ECR

### Stage 3: Deploy
- **Service**: CodeDeploy or Manual Actions
- **Action**: Update ECS services
- **Result**: Rolling deployment to production

## Services & Costs
- **CodePipeline**: $1/month per active pipeline
- **CodeBuild**: $0.005/minute (much cheaper than GitHub)
- **CodeCommit**: Free for 5 users, 50GB storage

## Setup Steps

### 1. Create CodeCommit Repository
```bash
aws codecommit create-repository --repository-name accunode-backend
```

### 2. Create buildspec.yml
```yaml
version: 0.2
phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
```

### 3. Create Pipeline Configuration (pipeline.json)
```json
{
  "pipeline": {
    "name": "accunode-production-pipeline",
    "roleArn": "arn:aws:iam::ACCOUNT:role/CodePipelineRole",
    "artifactStore": {
      "type": "S3",
      "location": "accunode-pipeline-artifacts"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "SourceAction",
            "actionTypeId": {
              "category": "Source",
              "owner": "ThirdParty",
              "provider": "GitHub",
              "version": "1"
            },
            "configuration": {
              "Owner": "betterresumes",
              "Repo": "default-rate-backend",
              "Branch": "prod",
              "OAuthToken": "{{resolve:secretsmanager:github-token}}"
            },
            "outputArtifacts": [{"name": "SourceOutput"}]
          }
        ]
      },
      {
        "name": "Build",
        "actions": [
          {
            "name": "BuildAction",
            "actionTypeId": {
              "category": "Build",
              "owner": "AWS",
              "provider": "CodeBuild",
              "version": "1"
            },
            "configuration": {
              "ProjectName": "accunode-build"
            },
            "inputArtifacts": [{"name": "SourceOutput"}],
            "outputArtifacts": [{"name": "BuildOutput"}]
          }
        ]
      },
      {
        "name": "Deploy",
        "actions": [
          {
            "name": "DeployAction",
            "actionTypeId": {
              "category": "Deploy",
              "owner": "AWS", 
              "provider": "ECS",
              "version": "1"
            },
            "configuration": {
              "ClusterName": "AccuNode-Production",
              "ServiceName": "accunode-api-service"
            },
            "inputArtifacts": [{"name": "BuildOutput"}]
          }
        ]
      }
    ]
  }
}
```

### 4. Create CodePipeline
```bash
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

## GitHub Actions vs AWS CodePipeline Comparison

| Feature | GitHub Actions | AWS CodePipeline |
|---------|---------------|------------------|
| **Execution** | Runs on GitHub's infrastructure | Runs on AWS infrastructure |
| **Configuration** | `.github/workflows/ci-cd.yml` | `buildspec.yml` + Pipeline JSON |
| **Triggers** | Git events, schedules, manual | Git push, S3 changes, schedules |
| **Compute** | GitHub runners (or self-hosted) | AWS CodeBuild containers |
| **Integration** | Great with GitHub | Native AWS services |
| **Pricing** | $0.008/minute (after 2000 free) | $1/pipeline + $0.005/build minute |
| **Flexibility** | High (any language/tool) | High (but AWS-centric) |
| **Setup Complexity** | Simple YAML file | Multiple AWS services |

## Similarities
✅ Both use YAML configuration  
✅ Both support Docker builds  
✅ Both have conditional execution  
✅ Both support parallel execution  
✅ Both integrate with Git repositories  

## Key Differences
🔄 **GitHub Actions**: Git-native, runs anywhere  
🔄 **CodePipeline**: AWS-native, optimized for AWS deployments  

## Detailed Monthly Cost Analysis

### Scenario 1: Light Usage (10 deployments/month)

#### GitHub Actions Costs:
```
Free tier: 2,000 minutes/month
Your pipeline: ~33 minutes per deployment
Monthly usage: 10 deployments × 33 minutes = 330 minutes
✅ COST: $0/month (within free tier)
```

#### AWS CodePipeline Costs:
```
Pipeline fee: $1/month per active pipeline
CodeBuild: 10 deployments × 8 minutes × $0.005 = $0.40
Total: $1.40/month
```

### Scenario 2: Medium Usage (30 deployments/month)

#### GitHub Actions Costs:
```
Monthly usage: 30 deployments × 33 minutes = 990 minutes
Free tier: 2,000 minutes (still covered)
✅ COST: $0/month (within free tier)
```

#### AWS CodePipeline Costs:
```
Pipeline fee: $1/month
CodeBuild: 30 deployments × 8 minutes × $0.005 = $1.20
Total: $2.20/month
```

### Scenario 3: Heavy Usage (60 deployments/month)

#### GitHub Actions Costs:
```
Monthly usage: 60 deployments × 33 minutes = 1,980 minutes
Free tier: 2,000 minutes (still mostly covered)
Overage: 0 minutes
✅ COST: $0/month (just within free tier)
```

#### AWS CodePipeline Costs:
```
Pipeline fee: $1/month  
CodeBuild: 60 deployments × 8 minutes × $0.005 = $2.40
Total: $3.40/month
```

### Scenario 4: Very Heavy Usage (100 deployments/month)

#### GitHub Actions Costs:
```
Monthly usage: 100 deployments × 33 minutes = 3,300 minutes
Free tier: 2,000 minutes
Overage: 1,300 minutes × $0.008 = $10.40
🚨 COST: $10.40/month
```

#### AWS CodePipeline Costs:
```
Pipeline fee: $1/month
CodeBuild: 100 deployments × 8 minutes × $0.005 = $4.00  
Total: $5.00/month
```

### Scenario 5: Enterprise Usage (200 deployments/month)

#### GitHub Actions Costs:
```
Monthly usage: 200 deployments × 33 minutes = 6,600 minutes
Free tier: 2,000 minutes
Overage: 4,600 minutes × $0.008 = $36.80
🚨 COST: $36.80/month
```

#### AWS CodePipeline Costs:
```
Pipeline fee: $1/month
CodeBuild: 200 deployments × 8 minutes × $0.005 = $8.00
Total: $9.00/month
```

## Decision Matrix: Which Option to Choose?

### Choose **GitHub Actions** if:
✅ You want everything in one place (code + CI/CD)  
✅ Your team is already familiar with GitHub  
✅ You need complex workflows with many integrations  
✅ You're okay with the cost for convenience  

### Choose **AWS CodePipeline** if:
✅ You're already heavily invested in AWS  
✅ You want lower costs for frequent deployments  
✅ You prefer native AWS service integration  
✅ You don't mind managing multiple AWS services  

### Choose **Self-Hosted Runner** if:
✅ You want GitHub Actions convenience at lower cost  
✅ You have AWS infrastructure management skills  
✅ You need persistent build cache  
✅ You want maximum control over the build environment  

### Choose **Manual Script** if:
✅ You deploy infrequently  
✅ You want zero ongoing costs  
✅ You prefer simple, transparent processes  
✅ You're comfortable with command-line tools  

## My Recommendation for Your Use Case:
Given your concern about GitHub Actions costs and existing AWS setup, I'd recommend:

**Option 1**: Self-hosted GitHub runner (best of both worlds)
**Option 2**: Manual deployment script (simplest, no ongoing costs)
**Option 3**: AWS CodePipeline (if you want full automation with lower costs)

## 📊 Cost Comparison Summary

| Deployments/Month | GitHub Actions | AWS CodePipeline | Savings with AWS |
|-------------------|---------------|------------------|------------------|
| **10** | $0 (free) | $1.40 | -$1.40 (GitHub wins) |
| **30** | $0 (free) | $2.20 | -$2.20 (GitHub wins) |  
| **60** | $0 (free) | $3.40 | -$3.40 (GitHub wins) |
| **100** | $10.40 | $5.00 | **+$5.40 saved** |
| **200** | $36.80 | $9.00 | **+$27.80 saved** |
| **500** | $126.80 | $21.00 | **+$105.80 saved** |

## 🎯 Key Insights:

### ✅ GitHub Actions is BETTER for:
- **Low to medium usage** (up to ~60 deployments/month)
- **Teams just getting started** 
- **Occasional deployments**

### ✅ AWS CodePipeline is BETTER for:
- **High usage** (100+ deployments/month)
- **Mature teams with frequent releases**
- **Cost-conscious organizations**

## 💡 Additional Costs to Consider:

### GitHub Actions:
- ✅ **No setup costs**
- ✅ **No infrastructure management** 
- ❌ **Usage scales linearly with deployments**

### AWS CodePipeline:
- ❌ **S3 bucket for artifacts**: ~$1-2/month
- ❌ **IAM setup complexity**
- ❌ **Learning curve for AWS services**
- ✅ **Fixed base cost regardless of usage**

## 🏆 My Updated Recommendation:

**For your current usage** (likely 10-60 deployments/month):
1. **Stick with GitHub Actions** - it's free for your usage level
2. **Set up monitoring** to track your monthly minutes usage  
3. **Switch to AWS CodePipeline** only if you exceed 80+ deployments/month

**Best of both worlds**: Set up the **self-hosted runner** to get GitHub Actions convenience with zero usage costs!

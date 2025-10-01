# AWS Admin: AccuNode Deployment User Setup Guide

## Overview
This guide helps AWS administrators create a user account with the exact permissions needed to deploy the AccuNode application on AWS.

## Required User: `accunode-deployer`

### User Account Setup

#### Step 1: Create IAM User
1. **Login to AWS Console** as administrator
2. **Navigate to IAM** → **Users** → **Add users**
3. **User name**: `accunode-deployer` (or `pranit-accunode`)
4. **Access type**: ✅ **Programmatic access** (for AWS CLI)
5. **Console access**: ✅ **Optional** (for troubleshooting)

#### Step 2: Create Custom Policy for AccuNode
Create a custom policy with these exact permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AccuNodeEC2Permissions",
            "Effect": "Allow",
            "Action": [
                "ec2:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeRDSPermissions", 
            "Effect": "Allow",
            "Action": [
                "rds:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeElastiCachePermissions",
            "Effect": "Allow",
            "Action": [
                "elasticache:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeVPCPermissions",
            "Effect": "Allow",
            "Action": [
                "ec2:*Vpc*",
                "ec2:*Subnet*", 
                "ec2:*Gateway*",
                "ec2:*Route*",
                "ec2:*SecurityGroup*",
                "ec2:*NetworkAcl*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeIAMPermissions",
            "Effect": "Allow", 
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:DeleteInstanceProfile",
                "iam:AddRoleToInstanceProfile",
                "iam:RemoveRoleFromInstanceProfile",
                "iam:PassRole",
                "iam:GetRole",
                "iam:ListRoles",
                "iam:ListInstanceProfiles"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeUserSelfManagement",
            "Effect": "Allow",
            "Action": [
                "iam:GetUser",
                "iam:CreateAccessKey",
                "iam:DeleteAccessKey",
                "iam:ListAccessKeys",
                "iam:UpdateAccessKey",
                "iam:GetAccessKeyLastUsed",
                "iam:ChangePassword",
                "iam:UpdateLoginProfile",
                "iam:GetLoginProfile"
            ],
            "Resource": [
                "arn:aws:iam::*:user/pranit",
                "arn:aws:iam::*:user/${aws:username}"
            ]
        },
        {
            "Sid": "AccuNodeParameterStorePermissions",
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters", 
                "ssm:PutParameter",
                "ssm:DeleteParameter",
                "ssm:GetParametersByPath",
                "ssm:DescribeParameters"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/accunode/*"
        },
        {
            "Sid": "AccuNodeCloudWatchPermissions",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:*",
                "logs:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeLoadBalancerPermissions",
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeAutoScalingPermissions",
            "Effect": "Allow",
            "Action": [
                "autoscaling:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeECRPermissions",
            "Effect": "Allow",
            "Action": [
                "ecr:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeCertificatePermissions",
            "Effect": "Allow",
            "Action": [
                "acm:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeRoute53Permissions",
            "Effect": "Allow",
            "Action": [
                "route53:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeCostPermissions",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetUsageReport", 
                "budgets:ViewBudget"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Step 3: Alternative - Use AWS Managed Policies (Easier Option)
Instead of the custom policy above, attach these AWS managed policies:

1. ✅ **PowerUserAccess** (recommended - covers most services)
   - OR individually attach:
2. ✅ **AmazonEC2FullAccess**
3. ✅ **AmazonRDSFullAccess** 
4. ✅ **AmazonElastiCacheFullAccess**
5. ✅ **AmazonVPCFullAccess**
6. ✅ **ElasticLoadBalancingFullAccess**
7. ✅ **AutoScalingFullAccess**
8. ✅ **AmazonEC2ContainerRegistryFullAccess**
9. ✅ **CloudWatchFullAccess**
10. ✅ **AmazonSSMFullAccess** (for Parameter Store)
11. ✅ **IAMFullAccess** (for creating service roles)

#### Step 4: Create Access Keys
1. **Select the user** → **Security credentials** tab
2. **Click "Create access key"**
3. **Choose**: "Command Line Interface (CLI)"
4. **Add description**: "AccuNode Deployment"
5. **Download CSV** or copy both keys immediately

#### Step 5: Provide Credentials to Developer
Give these to your developer:

```text
AWS Access Key ID: AKIA...
AWS Secret Access Key: [long-secret-key]
Default Region: us-east-1
```

## Cost Controls & Budget Setup

### Recommended Budget Alerts
1. **Navigate to**: Billing → Budgets → Create budget
2. **Budget type**: Cost budget
3. **Budget amount**: $150/month
4. **Alert thresholds**: 
   - 80% of budgeted amount ($120)
   - 100% of budgeted amount ($150)
   - 120% of budgeted amount ($180)

### Cost Monitoring Tags
Add these tags to all AccuNode resources:
- **Project**: AccuNode
- **Environment**: Production
- **Owner**: [developer-email]
- **Cost-Center**: [your-cost-center]

## Security Considerations

### Resource Naming Convention
All resources will be prefixed with `accunode-`:
- VPC: `accunode-vpc`
- Subnets: `accunode-public-1a`, `accunode-private-1a`
- Security Groups: `accunode-api-sg`, `accunode-db-sg`
- RDS: `accunode-postgres`
- ElastiCache: `accunode-redis`

### Security Best Practices Applied
- ✅ **VPC Isolation**: Database in private subnets
- ✅ **Security Groups**: Minimal required ports only
- ✅ **Encryption**: All data encrypted at rest and in transit
- ✅ **Parameter Store**: Secure credential storage
- ✅ **IAM Roles**: Service-specific permissions only

## Expected Resource Creation

### Infrastructure Resources
- **1 VPC** with 4 subnets (2 public, 2 private)
- **1 Internet Gateway** and route tables
- **4 Security Groups** (API, Database, Cache, Load Balancer)
- **3 IAM Roles** (EC2, RDS, ElastiCache service roles)

### Compute & Storage Resources  
- **4 EC2 Instances** (t3.small) - 2 API + 2 Workers
- **1 RDS PostgreSQL** (t3.micro initially, auto-scaling enabled)
- **1 ElastiCache Redis** (cache.t3.micro initially)
- **1 Application Load Balancer**
- **1 ECR Repository** for Docker images

### Monitoring Resources
- **CloudWatch Log Groups** for application logging
- **CloudWatch Alarms** for performance monitoring
- **CloudWatch Dashboards** for system overview

## Deployment Timeline & Costs

### Phase 1: Infrastructure ($0 - setup only)
- VPC, subnets, security groups
- IAM roles and Parameter Store
- **Time**: 30 minutes

### Phase 2: Database Services ($25/month)
- RDS PostgreSQL + ElastiCache Redis
- **Time**: 25 minutes

### Phase 3: Application Deployment ($89/month)
- EC2 instances + Load Balancer
- **Time**: 45 minutes

### Phase 4: Production Configuration ($0 additional)
- Auto-scaling + SSL setup
- **Time**: 30 minutes  

### Phase 5: Monitoring Setup ($5/month)
- CloudWatch configuration
- **Time**: 20 minutes

**Total Deployment Time**: 2.5 hours
**Initial Monthly Cost**: $119/month
**Scaling Cost**: Up to $300/month at full scale

## Emergency Contacts & Rollback

### In Case of Issues
- **Developer Contact**: [developer-email]
- **Project Manager**: [pm-email]  
- **Expected Deployment Window**: [date/time]

### Rollback Procedure
If deployment fails or costs exceed budget:
1. **Immediate**: Terminate all EC2 instances (stops $60/month)
2. **Within 1 hour**: Delete RDS/ElastiCache (stops $25/month)
3. **Cleanup**: VPC and security groups (no cost impact)

### Cost Protection
- **Auto-scaling limits**: Maximum 4 API + 6 worker instances
- **RDS protection**: t3.medium maximum instance size
- **Budget alerts**: Email notifications at $120, $150, $180

## Admin Checklist

### Pre-Deployment ✅
- [ ] User `accunode-deployer` created
- [ ] PowerUserAccess policy attached (or custom policy)
- [ ] Access keys generated and shared securely
- [ ] Budget alerts configured ($150/month)
- [ ] Cost monitoring tags defined
- [ ] Developer contact information confirmed

### Post-Deployment ✅  
- [ ] Verify all resources have proper tags
- [ ] Confirm budget alerts are working
- [ ] Check initial cost projections
- [ ] Schedule monthly cost review
- [ ] Document any custom configurations

## Questions for Admin

1. **Budget Approval**: Is $119-300/month approved for AccuNode?
2. **Region Preference**: Is us-east-1 acceptable for lowest costs?
3. **Domain Setup**: Do we need custom domain (api.yourcompany.com)?
4. **SSL Certificates**: Should we use AWS Certificate Manager?
5. **Backup Retention**: How long to keep database backups? (default: 7 days)

## Support & Documentation

### AWS Documentation References
- [IAM User Creation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html)
- [Budget Setup](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/budgets-create.html)
- [Cost Monitoring](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-what-is.html)

### Next Steps
Once the user is created and credentials are shared:
1. Developer will configure AWS CLI
2. Begin Phase 1: Infrastructure setup
3. Deploy AccuNode application following the deployment plan
4. Validate system performance and costs

**Ready to proceed with AccuNode AWS deployment setup?**

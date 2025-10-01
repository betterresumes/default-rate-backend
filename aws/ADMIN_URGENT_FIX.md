# URGENT: Fix User Permissions for AccuNode Deployment

## Current Issue
User `pranit` cannot create access keys due to missing IAM permissions.

**Error**: `Access denied You don't have permission to iam:GetUser`

## Quick Fix Required

### Option 1: Add Missing IAM Policy (Recommended)
Add this policy statement to user `pranit`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "UserSelfManagement",
            "Effect": "Allow",
            "Action": [
                "iam:GetUser",
                "iam:CreateAccessKey",
                "iam:DeleteAccessKey",
                "iam:ListAccessKeys",
                "iam:UpdateAccessKey",
                "iam:GetAccessKeyLastUsed"
            ],
            "Resource": [
                "arn:aws:iam::461962182774:user/pranit"
            ]
        }
    ]
}
```

### Option 2: Admin Creates Keys (Faster - 2 minutes)
1. **Login as admin** → IAM → Users → pranit
2. **Security credentials** tab → **Create access key**
3. **Choose**: "Command Line Interface (CLI)"
4. **Copy both keys** and send securely to pranit

**What pranit needs:**
```text
AWS Access Key ID: AKIA...
AWS Secret Access Key: [secret-key]
Region: us-east-1
```

## Complete Corrected Policy
If you want to give the full policy with self-management permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AccuNodeEC2Permissions",
            "Effect": "Allow",
            "Action": ["ec2:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeRDSPermissions", 
            "Effect": "Allow",
            "Action": ["rds:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeElastiCachePermissions",
            "Effect": "Allow",
            "Action": ["elasticache:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeVPCPermissions",
            "Effect": "Allow",
            "Action": [
                "ec2:*Vpc*", "ec2:*Subnet*", "ec2:*Gateway*",
                "ec2:*Route*", "ec2:*SecurityGroup*", "ec2:*NetworkAcl*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeIAMPermissions",
            "Effect": "Allow", 
            "Action": [
                "iam:CreateRole", "iam:DeleteRole", "iam:AttachRolePolicy",
                "iam:DetachRolePolicy", "iam:CreateInstanceProfile",
                "iam:DeleteInstanceProfile", "iam:AddRoleToInstanceProfile",
                "iam:RemoveRoleFromInstanceProfile", "iam:PassRole",
                "iam:GetRole", "iam:ListRoles", "iam:ListInstanceProfiles"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeUserSelfManagement",
            "Effect": "Allow",
            "Action": [
                "iam:GetUser", "iam:CreateAccessKey", "iam:DeleteAccessKey",
                "iam:ListAccessKeys", "iam:UpdateAccessKey", "iam:GetAccessKeyLastUsed"
            ],
            "Resource": "arn:aws:iam::461962182774:user/pranit"
        },
        {
            "Sid": "AccuNodeParameterStorePermissions",
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter", "ssm:GetParameters", "ssm:PutParameter",
                "ssm:DeleteParameter", "ssm:GetParametersByPath", "ssm:DescribeParameters"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/accunode/*"
        },
        {
            "Sid": "AccuNodeCloudWatchPermissions",
            "Effect": "Allow",
            "Action": ["cloudwatch:*", "logs:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeLoadBalancerPermissions",
            "Effect": "Allow",
            "Action": ["elasticloadbalancing:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeAutoScalingPermissions",
            "Effect": "Allow",
            "Action": ["autoscaling:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeECRPermissions",
            "Effect": "Allow",
            "Action": ["ecr:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeCertificatePermissions",
            "Effect": "Allow",
            "Action": ["acm:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeRoute53Permissions",
            "Effect": "Allow",
            "Action": ["route53:*"],
            "Resource": "*"
        },
        {
            "Sid": "AccuNodeCostPermissions",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage", "ce:GetUsageReport", "budgets:ViewBudget"
            ],
            "Resource": "*"
        }
    ]
}
```

## Alternative: PowerUserAccess + IAMReadOnlyAccess
Instead of the custom policy above, you can attach these AWS managed policies:
1. ✅ **PowerUserAccess** (covers most services)
2. ✅ **IAMReadOnlyAccess** (allows viewing IAM resources)
3. ✅ **Custom inline policy** for self-management:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateAccessKey",
                "iam:DeleteAccessKey",
                "iam:ListAccessKeys",
                "iam:UpdateAccessKey"
            ],
            "Resource": "arn:aws:iam::461962182774:user/pranit"
        }
    ]
}
```

## Urgency
AccuNode deployment is waiting on this fix. Once resolved, deployment can begin immediately.

**Expected deployment time**: 2.5 hours
**Initial cost**: $119/month

Please fix ASAP so we can proceed with AccuNode deployment.

#!/bin/bash

# CloudWatch Logs Setup Script
# This script sets up CloudWatch logging for AccuNode instances

echo "🏗️ Setting up CloudWatch Logs for AccuNode..."

# 1. Create log groups
echo "📝 Creating CloudWatch log groups..."

aws logs create-log-group --log-group-name "/accunode/api" --region us-east-1 2>/dev/null || echo "API log group already exists"
aws logs create-log-group --log-group-name "/accunode/worker" --region us-east-1 2>/dev/null || echo "Worker log group already exists"
aws logs create-log-group --log-group-name "/accunode/nginx" --region us-east-1 2>/dev/null || echo "Nginx log group already exists"

# 2. Set retention policies (7 days)
echo "⏰ Setting log retention policies..."
aws logs put-retention-policy --log-group-name "/accunode/api" --retention-in-days 7 --region us-east-1
aws logs put-retention-policy --log-group-name "/accunode/worker" --retention-in-days 7 --region us-east-1
aws logs put-retention-policy --log-group-name "/accunode/nginx" --retention-in-days 7 --region us-east-1

echo "✅ CloudWatch log groups created:"
echo "  - /accunode/api"
echo "  - /accunode/worker" 
echo "  - /accunode/nginx"

# 3. Create IAM role for CloudWatch logs if needed
echo "🔐 Creating IAM role for CloudWatch logs..."
cat > /tmp/cloudwatch-logs-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create the policy
aws iam create-policy \
    --policy-name AccuNodeCloudWatchLogsPolicy \
    --policy-document file:///tmp/cloudwatch-logs-policy.json \
    --region us-east-1 2>/dev/null || echo "Policy already exists"

echo "📋 Next steps to enable logging:"
echo "1. Attach the CloudWatchLogsPolicy to your EC2 instance role"
echo "2. Install and configure CloudWatch agent on instances"
echo "3. Or use Docker logging driver to send logs directly"

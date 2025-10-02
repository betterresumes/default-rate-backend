#!/bin/bash

# Auto Scaling Configuration Script
# Configure optimal scaling for AccuNode API and Workers

echo "🔧 Configuring AccuNode Auto Scaling Groups"
echo "==========================================="

# API Auto Scaling Group Configuration
echo "📊 Configuring API Auto Scaling Group..."
aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name "AccuNode-API-ASG" \
    --min-size 1 \
    --max-size 2 \
    --desired-capacity 1 \
    --default-cooldown 300 \
    --health-check-grace-period 300 \
    --region us-east-1

echo "✅ API ASG: Min=1, Max=2, Desired=1"

# Worker Auto Scaling Group Configuration  
echo "📊 Configuring Worker Auto Scaling Group..."
aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name "AccuNode-Worker-ASG" \
    --min-size 1 \
    --max-size 4 \
    --desired-capacity 1 \
    --default-cooldown 300 \
    --health-check-grace-period 300 \
    --region us-east-1

echo "✅ Worker ASG: Min=1, Max=4, Desired=1"

# Create scaling policies for API
echo "📈 Creating API scaling policies..."

# API Scale Out Policy
API_SCALE_OUT_POLICY=$(aws autoscaling put-scaling-policy \
    --auto-scaling-group-name "AccuNode-API-ASG" \
    --policy-name "AccuNode-API-ScaleOut" \
    --policy-type "StepScaling" \
    --adjustment-type "ChangeInCapacity" \
    --step-adjustments MetricIntervalLowerBound=0,ScalingAdjustment=1 \
    --region us-east-1 \
    --query 'PolicyARN' --output text)

# API Scale In Policy
API_SCALE_IN_POLICY=$(aws autoscaling put-scaling-policy \
    --auto-scaling-group-name "AccuNode-API-ASG" \
    --policy-name "AccuNode-API-ScaleIn" \
    --policy-type "StepScaling" \
    --adjustment-type "ChangeInCapacity" \
    --step-adjustments MetricIntervalUpperBound=0,ScalingAdjustment=-1 \
    --region us-east-1 \
    --query 'PolicyARN' --output text)

echo "✅ API scaling policies created"

# Create scaling policies for Workers
echo "📈 Creating Worker scaling policies..."

# Worker Scale Out Policy (add 1 instance at a time)
WORKER_SCALE_OUT_POLICY=$(aws autoscaling put-scaling-policy \
    --auto-scaling-group-name "AccuNode-Worker-ASG" \
    --policy-name "AccuNode-Worker-ScaleOut" \
    --policy-type "StepScaling" \
    --adjustment-type "ChangeInCapacity" \
    --step-adjustments MetricIntervalLowerBound=0,MetricIntervalUpperBound=50,ScalingAdjustment=1 MetricIntervalLowerBound=50,ScalingAdjustment=2 \
    --region us-east-1 \
    --query 'PolicyARN' --output text)

# Worker Scale In Policy
WORKER_SCALE_IN_POLICY=$(aws autoscaling put-scaling-policy \
    --auto-scaling-group-name "AccuNode-Worker-ASG" \
    --policy-name "AccuNode-Worker-ScaleIn" \
    --policy-type "StepScaling" \
    --adjustment-type "ChangeInCapacity" \
    --step-adjustments MetricIntervalUpperBound=0,ScalingAdjustment=-1 \
    --region us-east-1 \
    --query 'PolicyARN' --output text)

echo "✅ Worker scaling policies created"

# Create CloudWatch Alarms for API scaling
echo "🚨 Creating CloudWatch alarms for API..."

# API High CPU Alarm (Scale Out)
aws cloudwatch put-metric-alarm \
    --alarm-name "AccuNode-API-HighCPU" \
    --alarm-description "Scale out API when CPU > 70%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 70 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=AutoScalingGroupName,Value=AccuNode-API-ASG \
    --alarm-actions "$API_SCALE_OUT_POLICY" \
    --region us-east-1

# API Low CPU Alarm (Scale In)
aws cloudwatch put-metric-alarm \
    --alarm-name "AccuNode-API-LowCPU" \
    --alarm-description "Scale in API when CPU < 25%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --evaluation-periods 3 \
    --threshold 25 \
    --comparison-operator LessThanThreshold \
    --dimensions Name=AutoScalingGroupName,Value=AccuNode-API-ASG \
    --alarm-actions "$API_SCALE_IN_POLICY" \
    --region us-east-1

# Create custom metric alarm for API based on request count
aws cloudwatch put-metric-alarm \
    --alarm-name "AccuNode-API-HighRequests" \
    --alarm-description "Scale out API when request rate > 100/min" \
    --metric-name RequestCount \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=LoadBalancer,Value="app/AccuNode-ALB/$(aws elbv2 describe-load-balancers --names AccuNode-ALB --query 'LoadBalancers[0].LoadBalancerArn' --output text | cut -d'/' -f2-)" \
    --alarm-actions "$API_SCALE_OUT_POLICY" \
    --region us-east-1

echo "✅ API CloudWatch alarms created"

# Create CloudWatch Alarms for Worker scaling
echo "🚨 Creating CloudWatch alarms for Workers..."

# Worker High CPU Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "AccuNode-Worker-HighCPU" \
    --alarm-description "Scale out Workers when CPU > 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=AutoScalingGroupName,Value=AccuNode-Worker-ASG \
    --alarm-actions "$WORKER_SCALE_OUT_POLICY" \
    --region us-east-1

# Worker Low CPU Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "AccuNode-Worker-LowCPU" \
    --alarm-description "Scale in Workers when CPU < 20%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --evaluation-periods 5 \
    --threshold 20 \
    --comparison-operator LessThanThreshold \
    --dimensions Name=AutoScalingGroupName,Value=AccuNode-Worker-ASG \
    --alarm-actions "$WORKER_SCALE_IN_POLICY" \
    --region us-east-1

echo "✅ Worker CloudWatch alarms created"

echo
echo "📊 Auto Scaling Summary:"
echo "======================="
echo "API Servers: 1 min → 2 max (scales on CPU > 70% or requests > 100/min)"
echo "Workers: 1 min → 4 max (scales on CPU > 80%)"
echo "Total EC2s: 2 min → 6 max"
echo
echo "🔍 Monitor scaling with:"
echo "aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names AccuNode-API-ASG AccuNode-Worker-ASG"

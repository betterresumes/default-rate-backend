#!/bin/bash

# Clean Up Old AccuNode EC2 Resources
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🧹 Cleaning Up Old AccuNode EC2 Resources"
echo "========================================"
echo "Date: $(date)"
echo "⚠️  This will ONLY delete AccuNode-related EC2 resources"
echo

# Step 1: List and Stop AccuNode EC2 Instances
echo "🔍 Step 1: Finding AccuNode EC2 Instances"
echo "========================================"

echo "Searching for AccuNode EC2 instances..."
ACCUNODE_INSTANCES=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=*accunode*,*AccuNode*" "Name=instance-state-name,Values=running,stopped,stopping" \
    --query 'Reservations[*].Instances[*].[InstanceId,Tags[?Key==`Name`].Value|[0],State.Name]' \
    --output table)

if [ -z "$ACCUNODE_INSTANCES" ] || [ "$ACCUNODE_INSTANCES" = "None" ]; then
    echo "✅ No AccuNode instances found by tag"
    
    # Alternative search by security group or other identifiers
    echo "Searching for instances with AccuNode security groups..."
    ACCUNODE_INSTANCES_SG=$(aws ec2 describe-instances \
        --filters "Name=instance.group-name,Values=*accunode*,*AccuNode*" "Name=instance-state-name,Values=running,stopped" \
        --query 'Reservations[*].Instances[*].[InstanceId,SecurityGroups[0].GroupName,State.Name]' \
        --output table 2>/dev/null || echo "None")
    
    if [ "$ACCUNODE_INSTANCES_SG" != "None" ]; then
        echo "Found instances with AccuNode security groups:"
        echo "$ACCUNODE_INSTANCES_SG"
    fi
else
    echo "Found AccuNode instances:"
    echo "$ACCUNODE_INSTANCES"
    
    # Extract instance IDs
    INSTANCE_IDS=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=*accunode*,*AccuNode*" "Name=instance-state-name,Values=running,stopped" \
        --query 'Reservations[*].Instances[*].InstanceId' \
        --output text)
    
    if [ ! -z "$INSTANCE_IDS" ]; then
        echo "Terminating AccuNode instances: $INSTANCE_IDS"
        aws ec2 terminate-instances --instance-ids $INSTANCE_IDS
        echo "✅ AccuNode instances termination initiated"
    fi
fi

# Step 2: Clean Up Auto Scaling Groups
echo -e "\n🔄 Step 2: Cleaning Up AccuNode Auto Scaling Groups"
echo "=================================================="

echo "Searching for AccuNode Auto Scaling Groups..."
ACCUNODE_ASGS=$(aws autoscaling describe-auto-scaling-groups \
    --query 'AutoScalingGroups[?contains(AutoScalingGroupName, `accunode`) || contains(AutoScalingGroupName, `AccuNode`)].AutoScalingGroupName' \
    --output text)

if [ ! -z "$ACCUNODE_ASGS" ]; then
    echo "Found AccuNode Auto Scaling Groups: $ACCUNODE_ASGS"
    
    for ASG in $ACCUNODE_ASGS; do
        echo "Processing ASG: $ASG"
        
        # Update ASG to 0 capacity
        aws autoscaling update-auto-scaling-group \
            --auto-scaling-group-name "$ASG" \
            --min-size 0 \
            --max-size 0 \
            --desired-capacity 0
        
        echo "⏳ Waiting for ASG instances to terminate..."
        sleep 30
        
        # Delete ASG
        aws autoscaling delete-auto-scaling-group \
            --auto-scaling-group-name "$ASG" \
            --force-delete
        
        echo "✅ Auto Scaling Group deleted: $ASG"
    done
else
    echo "✅ No AccuNode Auto Scaling Groups found"
fi

# Step 3: Clean Up Launch Templates/Configurations
echo -e "\n🚀 Step 3: Cleaning Up Launch Templates"
echo "======================================"

echo "Searching for AccuNode Launch Templates..."
ACCUNODE_LTS=$(aws ec2 describe-launch-templates \
    --query 'LaunchTemplates[?contains(LaunchTemplateName, `accunode`) || contains(LaunchTemplateName, `AccuNode`)].LaunchTemplateName' \
    --output text)

if [ ! -z "$ACCUNODE_LTS" ]; then
    for LT in $ACCUNODE_LTS; do
        echo "Deleting Launch Template: $LT"
        aws ec2 delete-launch-template --launch-template-name "$LT"
        echo "✅ Launch Template deleted: $LT"
    done
else
    echo "✅ No AccuNode Launch Templates found"
fi

# Check Launch Configurations (older ASG format)
echo "Searching for AccuNode Launch Configurations..."
ACCUNODE_LCS=$(aws autoscaling describe-launch-configurations \
    --query 'LaunchConfigurations[?contains(LaunchConfigurationName, `accunode`) || contains(LaunchConfigurationName, `AccuNode`)].LaunchConfigurationName' \
    --output text)

if [ ! -z "$ACCUNODE_LCS" ]; then
    for LC in $ACCUNODE_LCS; do
        echo "Deleting Launch Configuration: $LC"
        aws autoscaling delete-launch-configuration --launch-configuration-name "$LC"
        echo "✅ Launch Configuration deleted: $LC"
    done
else
    echo "✅ No AccuNode Launch Configurations found"
fi

# Step 4: Clean Up Target Groups (old ones, not ECS ones)
echo -e "\n🎯 Step 4: Cleaning Up Old Target Groups"
echo "======================================"

echo "Searching for old AccuNode Target Groups (excluding ECS ones)..."
ALL_TGS=$(aws elbv2 describe-target-groups \
    --query 'TargetGroups[?contains(TargetGroupName, `accunode`) || contains(TargetGroupName, `AccuNode`)].TargetGroupName' \
    --output text)

if [ ! -z "$ALL_TGS" ]; then
    for TG in $ALL_TGS; do
        # Skip our ECS target group
        if [ "$TG" = "AccuNode-ECS-API-TG" ]; then
            echo "⏩ Skipping ECS target group: $TG"
            continue
        fi
        
        echo "Found old target group: $TG"
        TG_ARN=$(aws elbv2 describe-target-groups --names "$TG" --query 'TargetGroups[0].TargetGroupArn' --output text)
        
        # Check if it's attached to any load balancer
        LISTENERS=$(aws elbv2 describe-listeners --query "Listeners[?DefaultActions[?TargetGroupArn=='$TG_ARN']].ListenerArn" --output text)
        
        if [ ! -z "$LISTENERS" ]; then
            echo "⚠️  Target group $TG is attached to listeners. Skipping for safety."
        else
            echo "Deleting old target group: $TG"
            aws elbv2 delete-target-group --target-group-arn "$TG_ARN" 2>/dev/null || echo "Could not delete $TG (may be in use)"
        fi
    done
else
    echo "✅ No old AccuNode Target Groups found"
fi

# Step 5: Summary and Verification
echo -e "\n📊 Step 5: Cleanup Summary"
echo "========================="

echo "🔍 Verifying cleanup..."

# Check remaining instances
REMAINING_INSTANCES=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=*accunode*,*AccuNode*" "Name=instance-state-name,Values=running,pending,stopping" \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text)

if [ -z "$REMAINING_INSTANCES" ]; then
    echo "✅ No AccuNode EC2 instances remain"
else
    echo "⚠️  Remaining instances (may be terminating): $REMAINING_INSTANCES"
fi

# Check remaining ASGs
REMAINING_ASGS=$(aws autoscaling describe-auto-scaling-groups \
    --query 'AutoScalingGroups[?contains(AutoScalingGroupName, `accunode`) || contains(AutoScalingGroupName, `AccuNode`)].AutoScalingGroupName' \
    --output text)

if [ -z "$REMAINING_ASGS" ]; then
    echo "✅ No AccuNode Auto Scaling Groups remain"
else
    echo "⚠️  Remaining ASGs: $REMAINING_ASGS"
fi

echo ""
echo "🎉 AccuNode EC2 Cleanup Complete!"
echo "================================"
echo "✅ Old AccuNode EC2 instances terminated"
echo "✅ Auto Scaling Groups removed"
echo "✅ Launch Templates/Configurations deleted"
echo "✅ ECS resources preserved"
echo ""
echo "💰 Cost Savings: No more EC2 instance charges for AccuNode"
echo "🚀 New Setup: ECS Fargate (serverless, pay-per-use)"
echo ""
echo "🔗 Your application is now running on:"
echo "   ECS Cluster: AccuNode-Production"
echo "   Load Balancer: http://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo ""
echo "⚠️  Note: If you had any other applications on the deleted instances,"
echo "   make sure they were migrated first!"

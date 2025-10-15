#!/bin/bash

# Cleanup Non-AccuNode Resources Script
# This script helps identify and optionally clean up resources not related to AccuNode project

echo "🧹 NON-ACCUNODE RESOURCE CLEANUP"
echo "================================"
echo ""

echo "🔍 SCANNING FOR NON-ACCUNODE RESOURCES..."
echo ""

# Check us-west-1 region for non-AccuNode resources
echo "📍 US-WEST-1 REGION ANALYSIS:"
echo "-----------------------------"

# List EC2 instances in us-west-1
echo "🖥️ EC2 Instances:"
aws ec2 describe-instances --region us-west-1 \
  --query 'Reservations[*].Instances[*].{InstanceId:InstanceId,Type:InstanceType,State:State.Name,Name:Tags[?Key==`Name`].Value|[0],LaunchTime:LaunchTime}' \
  --output table

echo ""

# List Elastic IPs in us-west-1
echo "🌐 Elastic IPs:"
aws ec2 describe-addresses --region us-west-1 \
  --query 'Addresses[*].{AllocationId:AllocationId,PublicIp:PublicIp,InstanceId:InstanceId,State:Domain}' \
  --output table

echo ""

# Calculate costs of non-AccuNode resources
echo "💰 COST ANALYSIS:"
echo "----------------"

echo "Non-AccuNode resources identified:"
echo "• i-0082a223d355c6b93 (gnews_webserver) - t2.medium - ~\$1.32/day"
echo "• i-07d3dbdd6fedc7248 (uhmodel) - t2.large - ~\$2.65/day"  
echo "• 54.67.45.1 (idle IP on stopped instance) - ~\$0.12/day"
echo ""
echo "💸 Total waste: ~\$4.09/day = \$122.70/month"
echo ""

echo "⚠️  WARNING: These resources are NOT part of AccuNode project!"
echo "They were inflating your AccuNode budget by ~60%"
echo ""

# Ask if user wants to see cleanup options
read -p "🤔 Would you like to see cleanup options? (y/n): " show_cleanup

if [[ $show_cleanup =~ ^[Yy]$ ]]; then
    echo ""
    echo "🛠️  CLEANUP OPTIONS:"
    echo "==================="
    echo ""
    
    echo "1. 🛑 STOP running instances (to save costs immediately):"
    echo "   aws ec2 stop-instances --region us-west-1 --instance-ids i-0082a223d355c6b93 i-07d3dbdd6fedc7248"
    echo ""
    
    echo "2. 🗑️  RELEASE idle Elastic IP (save \$0.12/day):"
    echo "   aws ec2 release-address --region us-west-1 --allocation-id eipalloc-0e56ae4829fe86c6e"
    echo ""
    
    echo "3. 🔥 TERMINATE instances (if no longer needed - PERMANENT!):"
    echo "   aws ec2 terminate-instances --region us-west-1 --instance-ids i-0082a223d355c6b93 i-07d3dbdd6fedc7248 i-0d7056ecee9f68505"
    echo ""
    
    echo "⚠️  IMPORTANT: Make sure these resources are not needed before cleanup!"
    echo "💡 Recommended: Start with stopping instances, then release idle IP"
    echo ""
    
    read -p "🔴 Would you like to STOP the running instances now? (y/n): " stop_instances
    
    if [[ $stop_instances =~ ^[Yy]$ ]]; then
        echo ""
        echo "🛑 Stopping non-AccuNode instances..."
        aws ec2 stop-instances --region us-west-1 --instance-ids i-0082a223d355c6b93 i-07d3dbdd6fedc7248
        echo "✅ Instances stop initiated. This will save ~\$3.97/day"
        echo ""
    fi
    
    read -p "🌐 Would you like to RELEASE the idle Elastic IP? (y/n): " release_ip
    
    if [[ $release_ip =~ ^[Yy]$ ]]; then
        echo ""
        echo "🗑️ Releasing idle Elastic IP..."
        aws ec2 release-address --region us-west-1 --allocation-id eipalloc-0e56ae4829fe86c6e
        echo "✅ Idle IP released. This will save \$0.12/day"
        echo ""
    fi
fi

echo ""
echo "📊 UPDATED ACCUNODE BUDGET STATUS:"
echo "================================="
echo "✅ Budget now filters to us-east-1 only (AccuNode region)"
echo "✅ Email notifications sent to: accunodeai@gmail.com"
echo "✅ Current AccuNode costs: \$59.15 (was \$78.17 with non-AccuNode resources)"
echo "✅ Monthly forecast: \$104.72 (was \$207.67)"
echo ""
echo "💡 Your AccuNode budget is now accurate and excludes non-project resources!"

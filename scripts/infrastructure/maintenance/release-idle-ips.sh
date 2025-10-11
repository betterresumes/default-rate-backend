#!/bin/bash

# URGENT: Release Idle Elastic IP Addresses
# These are costing $3.25/day ($97.50/month) for NOTHING!
# Run this immediately to stop the waste

echo "🚨 RELEASING IDLE ELASTIC IP ADDRESSES (URGENT COST SAVINGS)"
echo "💰 This will save $3.25/day ($97.50/month)"
echo ""

# Release Elastic IP from stopped gnews_webserver
echo "🔥 Releasing IP 50.18.252.63 from stopped gnews_webserver..."
aws ec2 disassociate-address --region us-west-1 --association-id eipassoc-0d92adbf9a21ed8ad
aws ec2 release-address --region us-west-1 --allocation-id eipalloc-0eeb94d67edabc1cc

# Release Elastic IP from stopped uhmodel  
echo "🔥 Releasing IP 52.53.114.88 from stopped uhmodel..."
aws ec2 disassociate-address --region us-west-1 --association-id eipassoc-06fb5b3900c729fb0
aws ec2 release-address --region us-west-1 --allocation-id eipalloc-02de941c411b0f054

# Release Elastic IP from stopped hate-speech-model
echo "🔥 Releasing IP 54.67.45.1 from stopped hate-speech-model..."
aws ec2 disassociate-address --region us-west-1 --association-id eipassoc-0c3d0a90d64ea572b
aws ec2 release-address --region us-west-1 --allocation-id eipalloc-0e56ae4829fe86c6e

echo ""
echo "✅ ALL IDLE ELASTIC IPs RELEASED!"
echo "💰 IMMEDIATE SAVINGS: $3.25/day ($97.50/month)"
echo "📉 Your VPC costs should drop from $8.23 to ~$5.00"
echo ""
echo "⚠️  NOTE: If you need these instances later, you'll get new random IPs"
echo "💡 Only keep Elastic IPs for running production services"

# Verify releases
echo "📊 Verifying releases..."
aws ec2 describe-addresses --region us-west-1 --output table

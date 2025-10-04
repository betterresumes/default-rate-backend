#!/bin/bash

# Setup SSH tunnel to private RDS through bastion host
# Usage: ./setup_rds_tunnel.sh

# Configuration - UPDATED WITH CORRECT VALUES
BASTION_IP="52.91.36.2"
KEY_PATH="../bastion-access-key.pem"
RDS_ENDPOINT="accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
LOCAL_PORT="5433"

echo "🚇 Setting up SSH tunnel to private RDS..."
echo "Bastion: $BASTION_IP"
echo "RDS: $RDS_ENDPOINT"
echo "Local Port: $LOCAL_PORT"
echo ""

# Create SSH tunnel
# This forwards local port 5433 to RDS port 5432 through bastion
ssh -i "$KEY_PATH" \
    -L $LOCAL_PORT:$RDS_ENDPOINT:5432 \
    -N \
    ubuntu@$BASTION_IP

echo "🔗 SSH tunnel established!"
echo "You can now connect to: localhost:$LOCAL_PORT"
echo "Press Ctrl+C to close the tunnel"

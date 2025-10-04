#!/bin/bash
# RDS Database Connection Script
export PGPASSWORD="AccuNode2024!SecurePass"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432

#!/bin/bash
# Convenience wrapper for status check
# Calls the organized infrastructure monitoring script

echo "🔗 Calling infrastructure monitoring script..."
exec "$(dirname "$0")/infrastructure/monitoring/check-status.sh" "$@"

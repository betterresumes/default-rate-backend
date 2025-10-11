#!/bin/bash
# Convenience wrapper for quick scale-down
# Calls the organized infrastructure scaling script

echo "🔗 Calling infrastructure scaling script..."
exec "$(dirname "$0")/infrastructure/scaling/quick-scale-down.sh" "$@"

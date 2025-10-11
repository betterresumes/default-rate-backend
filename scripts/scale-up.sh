#!/bin/bash
# Convenience wrapper for full scale-up
# Calls the organized infrastructure scaling script

echo "🔗 Calling infrastructure scaling script..."
exec "$(dirname "$0")/infrastructure/scaling/scale-up.sh" "$@"

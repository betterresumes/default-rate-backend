#!/bin/bash

# Financial Risk API - Postman Collection Combiner Script
# ========================================================
# This script combines two Postman collection parts into one complete collection

echo "🏦 Financial Risk API - Postman Collection Combiner"
echo "============================================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if the required files exist
if [ ! -f "UPDATED_POSTMAN_COLLECTION_PART1.json" ]; then
    echo "❌ UPDATED_POSTMAN_COLLECTION_PART1.json not found!"
    exit 1
fi

if [ ! -f "UPDATED_POSTMAN_COLLECTION_PART2.json" ]; then
    echo "❌ UPDATED_POSTMAN_COLLECTION_PART2.json not found!"
    exit 1
fi

# Check if combine script exists
if [ ! -f "combine_postman_collections.py" ]; then
    echo "❌ combine_postman_collections.py not found!"
    exit 1
fi

echo "🔄 Running collection combiner..."
echo ""

# Run the Python script
python3 combine_postman_collections.py

# Check if the output file was created
if [ -f "COMPLETE_UPDATED_POSTMAN_COLLECTION.json" ]; then
    echo ""
    echo "✅ Complete collection created successfully!"
    echo "📁 File: COMPLETE_UPDATED_POSTMAN_COLLECTION.json"
    echo "📦 Size: $(du -h COMPLETE_UPDATED_POSTMAN_COLLECTION.json | cut -f1)"
    echo ""
    echo "🚀 Next Steps:"
    echo "   1. Open Postman"
    echo "   2. Go to File → Import"
    echo "   3. Select 'COMPLETE_UPDATED_POSTMAN_COLLECTION.json'"
    echo "   4. Start testing your Financial Risk API!"
    echo ""
else
    echo "❌ Failed to create combined collection"
    exit 1
fi

#!/usr/bin/env python3
"""
Script to merge multiple Postman collection JSON files into one final collection.
This will combine COMPLETE_API_COLLECTION_PART1.json, PART2.json, and PART3.json
into final_postmain_api_collection.json
"""

import json
import os
from pathlib import Path

def merge_postman_collections():
    """Merge multiple Postman collection parts into one final collection."""
    
    # Define file paths
    current_dir = Path(__file__).parent
    part1_file = current_dir / "COMPLETE_API_COLLECTION_PART1.json"
    part2_file = current_dir / "COMPLETE_API_COLLECTION_PART2.json"
    part3_file = current_dir / "COMPLETE_API_COLLECTION_PART3.json"
    output_file = current_dir / "final_postmain_api_collection.json"
    
    # Check if all input files exist
    input_files = [part1_file, part2_file, part3_file]
    missing_files = []
    
    for file_path in input_files:
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print("❌ Missing files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n🔍 Available JSON files in current directory:")
        for json_file in current_dir.glob("*.json"):
            print(f"   - {json_file.name}")
        return False
    
    try:
        # Load all three parts
        print("📖 Loading collection parts...")
        
        with open(part1_file, 'r', encoding='utf-8') as f:
            part1 = json.load(f)
            print(f"✅ Part 1 loaded: {len(part1.get('item', []))} main sections")
        
        with open(part2_file, 'r', encoding='utf-8') as f:
            part2 = json.load(f)
            print(f"✅ Part 2 loaded: {len(part2.get('item', []))} main sections")
        
        with open(part3_file, 'r', encoding='utf-8') as f:
            part3 = json.load(f)
            print(f"✅ Part 3 loaded: {len(part3.get('item', []))} main sections")
        
        # Create the merged collection based on Part 1 structure
        merged_collection = {
            "info": {
                "name": "🏦 COMPLETE Financial Risk API - ALL ENDPOINTS",
                "description": "Complete Postman collection for multi-tenant financial risk prediction system - ALL 71+ endpoints in one collection for frontend development",
                "version": "1.0.0 - PRODUCTION READY - MERGED",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "variable": part1.get("variable", []),  # Use Part 1's variables (most comprehensive)
            "auth": part1.get("auth", {}),  # Use Part 1's auth settings
            "item": []
        }
        
        # Add all items from Part 1
        if "item" in part1:
            merged_collection["item"].extend(part1["item"])
            print(f"📦 Added Part 1 sections: {len(part1['item'])}")
        
        # Add all items from Part 2
        if "item" in part2:
            merged_collection["item"].extend(part2["item"])
            print(f"📦 Added Part 2 sections: {len(part2['item'])}")
        
        # Add all items from Part 3
        if "item" in part3:
            merged_collection["item"].extend(part3["item"])
            print(f"📦 Added Part 3 sections: {len(part3['item'])}")
        
        # Count total endpoints
        total_endpoints = 0
        section_summary = []
        
        for section in merged_collection["item"]:
            section_name = section.get("name", "Unknown Section")
            if "item" in section:
                endpoint_count = len(section["item"])
                total_endpoints += endpoint_count
                section_summary.append(f"   - {section_name}: {endpoint_count} endpoints")
            else:
                # Direct endpoint (not a folder)
                total_endpoints += 1
                section_summary.append(f"   - {section_name}: 1 endpoint")
        
        # Save the merged collection
        print(f"\n💾 Saving merged collection to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_collection, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n🎉 SUCCESS! Merged collection created successfully!")
        print(f"📊 FINAL COLLECTION SUMMARY:")
        print(f"   📁 Total Sections: {len(merged_collection['item'])}")
        print(f"   🔗 Total Endpoints: {total_endpoints}")
        print(f"   📄 Output File: final_postmain_api_collection.json")
        print(f"   💾 File Size: {output_file.stat().st_size / 1024:.1f} KB")
        
        print(f"\n📋 SECTION BREAKDOWN:")
        for summary in section_summary:
            print(summary)
        
        print(f"\n🚀 READY FOR FRONTEND DEVELOPMENT!")
        print(f"   1. Import 'final_postmain_api_collection.json' into Postman")
        print(f"   2. Set your baseUrl variable (default: http://localhost:8000)")
        print(f"   3. Start with Authentication endpoints to get your token")
        print(f"   4. Variables will auto-populate as you use the endpoints")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error merging collections: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Postman Collection Merger")
    print("=" * 50)
    
    success = merge_postman_collections()
    
    if success:
        print("\n✨ Collection merge completed successfully!")
        exit(0)
    else:
        print("\n💥 Collection merge failed!")
        exit(1)

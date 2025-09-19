#!/usr/bin/env python3
"""
Postman Collection Merger - Enhanced Version
Merges multiple Postman collection JSON files into one unified collection
Now includes the new dedicated predictions collection
"""

import json
import os
from pathlib import Path

def check_file_exists(file_path):
    """Check if file exists and return True/False"""
    return Path(file_path).exists()

def load_json_file(file_path):
    """Load and return JSON data from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {str(e)}")
        return None

def count_endpoints_in_section(section):
    """Recursively count endpoints in a section"""
    count = 0
    if "item" in section:
        for item in section["item"]:
            if "request" in item:  # This is an endpoint
                count += 1
            elif "item" in item:  # This is a subsection
                count += count_endpoints_in_section(item)
    return count

def main():
    print("🔄 ENHANCED POSTMAN COLLECTION MERGE PROCESS")
    print("=" * 65)
    
    # File paths - now including the new predictions collection
    part1_file = "COMPLETE_API_COLLECTION_PART1.json"
    part2_file = "COMPLETE_API_COLLECTION_PART2.json"
    part3_file = "COMPLETE_API_COLLECTION_PART3.json"
    predictions_file = "PREDICTIONS_COMPLETE_COLLECTION.json"
    output_file = "final_postmain_api_collection.json"
    
    files_to_merge = [part1_file, part2_file, part3_file, predictions_file]
    
    print("🔍 Checking for required files...")
    current_dir = Path(".")
    missing_files = []
    
    for file in files_to_merge:
        if not check_file_exists(file):
            missing_files.append(file)
        else:
            file_size = os.path.getsize(file) / 1024  # Size in KB
            print(f"✅ Found: {file} ({file_size:.1f} KB)")
    
    if missing_files:
        print("❌ Missing files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n🔍 Available JSON files in current directory:")
        for json_file in current_dir.glob("*.json"):
            print(f"   - {json_file.name}")
        return False
    
    try:
        # Load all collection parts
        print("\n📖 Loading collection parts...")
        
        part1 = load_json_file(part1_file)
        if part1:
            print(f"✅ Part 1 loaded: {len(part1.get('item', []))} main sections")
        
        part2 = load_json_file(part2_file)
        if part2:
            print(f"✅ Part 2 loaded: {len(part2.get('item', []))} main sections")
        
        part3 = load_json_file(part3_file)
        if part3:
            print(f"✅ Part 3 loaded: {len(part3.get('item', []))} main sections")
        
        predictions = load_json_file(predictions_file)
        if predictions:
            print(f"✅ Predictions loaded: {len(predictions.get('item', []))} main sections")
        
        if not all([part1, part2, part3, predictions]):
            print("❌ Failed to load one or more collection files")
            return False
        
        print("\n🔧 Creating merged collection...")
        
        # Create the merged collection with enhanced info
        merged_collection = {
            "info": {
                "name": "🏦 COMPLETE Financial Risk API - ALL ENDPOINTS (ENHANCED)",
                "description": "Complete Postman collection for multi-tenant financial risk prediction system - ALL endpoints including dedicated predictions section for frontend development",
                "version": "2.0.0 - PRODUCTION READY - ENHANCED MERGED",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "variable": part1.get("variable", []),  # Use Part 1's variables (most comprehensive)
            "auth": part1.get("auth", {}),  # Use Part 1's auth settings
            "item": []
        }
        
        # Add all items from each part
        collections_data = [
            (part1, "Part 1 - Auth & Core"),
            (part2, "Part 2 - Organizations & Users"),
            (part3, "Part 3 - Companies"),
            (predictions, "Predictions - Annual, Quarterly & Bulk")
        ]
        
        total_sections = 0
        total_endpoints = 0
        
        for collection, description in collections_data:
            if "item" in collection and collection["item"]:
                merged_collection["item"].extend(collection["item"])
                sections_added = len(collection["item"])
                total_sections += sections_added
                
                # Count endpoints in this collection
                collection_endpoints = 0
                for section in collection["item"]:
                    collection_endpoints += count_endpoints_in_section(section)
                total_endpoints += collection_endpoints
                
                print(f"📦 Added {description}: {sections_added} sections, {collection_endpoints} endpoints")
        
        print(f"\n📊 MERGE SUMMARY:")
        print(f"   📁 Total Sections: {total_sections}")
        print(f"   🔗 Total Endpoints: {total_endpoints}")
        
        # Save the merged collection
        print(f"\n💾 Saving merged collection to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_collection, f, indent=2, ensure_ascii=False)
        
        # Verify the output file
        if check_file_exists(output_file):
            output_size = os.path.getsize(output_file) / 1024  # Size in KB
            print(f"✅ Successfully created: {output_file} ({output_size:.1f} KB)")
            
            # Final verification
            verification = load_json_file(output_file)
            if verification:
                final_sections = len(verification.get('item', []))
                final_endpoints = 0
                for section in verification.get('item', []):
                    final_endpoints += count_endpoints_in_section(section)
                
                print(f"\n🎉 SUCCESS! Enhanced merged collection created successfully!")
                print(f"📊 FINAL COLLECTION SUMMARY:")
                print(f"   📁 Total Sections: {final_sections}")
                print(f"   🔗 Total Endpoints: {final_endpoints}")
                print(f"   📄 Output File: {output_file}")
                print(f"   💾 File Size: {output_size:.1f} KB")
                
                print(f"\n📋 SECTIONS INCLUDED:")
                for i, section in enumerate(verification.get('item', []), 1):
                    section_name = section.get('name', f'Section {i}')
                    section_endpoints = count_endpoints_in_section(section)
                    print(f"   {i}. {section_name} ({section_endpoints} endpoints)")
                
                return True
            else:
                print("❌ Failed to verify the created file")
                return False
        else:
            print("❌ Failed to create output file")
            return False
            
    except Exception as e:
        print(f"❌ Error during merge process: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 MERGE COMPLETED SUCCESSFULLY!")
        print("🚀 Your enhanced collection is ready for frontend development!")
    else:
        print("\n💥 MERGE FAILED!")
        print("🔧 Please check the error messages above and try again.")

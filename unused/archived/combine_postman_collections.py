#!/usr/bin/env python3
"""
Combine Postman Collection Parts Script
=====================================

This script combines UPDATED_POSTMAN_COLLECTION_PART1.json and 
UPDATED_POSTMAN_COLLECTION_PART2.json into a single complete collection.

Usage:
    python combine_postman_collections.py

Output:
    COMPLETE_UPDATED_POSTMAN_COLLECTION.json
"""

import json
import os
from datetime import datetime

def load_json_file(filename):
    """Load and parse a JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found!")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filename}': {e}")
        return None

def combine_collections():
    """Combine two Postman collection parts into one."""
    
    # File paths
    part1_file = "UPDATED_POSTMAN_COLLECTION_PART1.json"
    part2_file = "UPDATED_POSTMAN_COLLECTION_PART2.json"
    output_file = "final_postmain_apis_collection.json"
    
    print("🔄 Starting Postman Collection Combination...")
    print(f"📁 Part 1: {part1_file}")
    print(f"📁 Part 2: {part2_file}")
    
    # Load both collections
    part1 = load_json_file(part1_file)
    part2 = load_json_file(part2_file)
    
    if not part1 or not part2:
        print("❌ Failed to load collection files!")
        return False
    
    # Create the combined collection based on Part 1
    combined_collection = part1.copy()
    
    # Update the collection info
    combined_collection["info"]["name"] = "🏦 Financial Risk API - Complete Collection (Combined)"
    combined_collection["info"]["description"] = f"""Complete API collection for Financial Default Risk Prediction System v2.0.0

## 🎯 Current 5-Role System

### Role Hierarchy:
1. **super_admin** - Full system access, can manage everything
2. **tenant_admin** - Attached to 1 tenant, can manage multiple orgs within that tenant
3. **org_admin** - Attached to 1 organization, can manage users in that org
4. **org_member** - Attached to 1 organization, can access org resources and create predictions
5. **user** - No organization attachment, limited access

## 📋 Complete Collection Sections:

### Part 1 - Core Management:
1. 🔐 **USER AUTHENTICATION** - Registration, login, organization joining
2. 👨‍💼 **ADMIN AUTHENTICATION** - Super admin operations and user management
3. 🎯 **TENANT ADMIN MANAGEMENT** - Tenant creation and user assignment
4. 🏢 **TENANT MANAGEMENT** - Tenant CRUD operations and statistics

### Part 2 - Business Operations:
5. 🏛️ **ORGANIZATION MANAGEMENT** - Organization CRUD, join tokens, whitelists
6. 👥 **USER MANAGEMENT** - Profile management and admin operations
7. 🏭 **COMPANIES** - Company management with multi-tenant access
8. 📊 **PREDICTIONS** - ML prediction endpoints with role-based access
9. 📋 **API INFO** - Health check and documentation endpoints

## 🔧 Combined on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # Combine the items from both collections
    if "item" in part2 and isinstance(part2["item"], list):
        combined_collection["item"].extend(part2["item"])
        print(f"✅ Added {len(part2['item'])} sections from Part 2")
    
    # Add any additional variables from Part 2 (if they don't exist in Part 1)
    if "variable" in part2:
        part1_var_keys = {var["key"] for var in combined_collection.get("variable", [])}
        for var in part2["variable"]:
            if var["key"] not in part1_var_keys:
                combined_collection["variable"].append(var)
                print(f"✅ Added variable: {var['key']}")
    
    # Save the combined collection
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(combined_collection, file, indent=2, ensure_ascii=False)
        print(f"✅ Combined collection saved to: {output_file}")
        
        # Print summary
        total_sections = len(combined_collection["item"])
        total_requests = sum(len(section.get("item", [])) for section in combined_collection["item"])
        
        print("\n📊 Collection Summary:")
        print(f"   📁 Total Sections: {total_sections}")
        print(f"   🔗 Total Requests: {total_requests}")
        print(f"   📋 Variables: {len(combined_collection.get('variable', []))}")
        
        # List all sections
        print("\n📋 Combined Sections:")
        for i, section in enumerate(combined_collection["item"], 1):
            section_name = section.get("name", "Unknown")
            item_count = len(section.get("item", []))
            print(f"   {i}. {section_name} ({item_count} requests)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving combined collection: {e}")
        return False

def validate_combined_collection():
    """Validate the combined collection structure."""
    output_file = "COMPLETE_UPDATED_POSTMAN_COLLECTION.json"
    
    print(f"\n🔍 Validating {output_file}...")
    
    combined = load_json_file(output_file)
    if not combined:
        return False
    
    # Check required fields
    required_fields = ["info", "item", "variable"]
    for field in required_fields:
        if field not in combined:
            print(f"❌ Missing required field: {field}")
            return False
    
    # Check info structure
    if "name" not in combined["info"] or "description" not in combined["info"]:
        print("❌ Invalid info structure")
        return False
    
    # Check each section has required structure
    def validate_items(items, parent_name=""):
        for item in items:
            if "name" not in item:
                print(f"❌ Item missing name in {parent_name}: {item}")
                return False
            
            # If it has subitems (folder), validate those recursively
            if "item" in item:
                if not validate_items(item["item"], f"{parent_name}/{item['name']}"):
                    return False
            # If it's a request, it should have a request field
            elif "request" not in item:
                print(f"❌ Request missing 'request' field in {parent_name}: {item['name']}")
                return False
        return True
    
    if not validate_items(combined["item"], "root"):
        return False
    
    print("✅ Collection structure is valid!")
    return True

def main():
    """Main function to combine and validate collections."""
    print("🏦 Financial Risk API - Postman Collection Combiner")
    print("=" * 60)
    
    # Check if input files exist
    part1_exists = os.path.exists("UPDATED_POSTMAN_COLLECTION_PART1.json")
    part2_exists = os.path.exists("UPDATED_POSTMAN_COLLECTION_PART2.json")
    
    if not part1_exists:
        print("❌ UPDATED_POSTMAN_COLLECTION_PART1.json not found!")
        return
    
    if not part2_exists:
        print("❌ UPDATED_POSTMAN_COLLECTION_PART2.json not found!")
        return
    
    # Combine collections
    if combine_collections():
        # Validate the result
        if validate_combined_collection():
            print("\n🎉 Successfully created complete Postman collection!")
            print("📄 Import 'COMPLETE_UPDATED_POSTMAN_COLLECTION.json' into Postman")
        else:
            print("\n⚠️  Collection created but validation failed")
    else:
        print("\n❌ Failed to combine collections")

if __name__ == "__main__":
    main()

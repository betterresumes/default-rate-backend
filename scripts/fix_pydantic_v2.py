#!/usr/bin/env python3
"""
Fix Pydantic V2 Compatibility Issues
===================================

This script fixes all orm_mode and schema_extra issues for Pydantic V2 compatibility.
"""

import re
import os

def fix_pydantic_v2_issues():
    """Fix all Pydantic V2 compatibility issues in schemas.py"""
    
    schemas_file = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend/app/schemas/schemas.py"
    
    # Read the current content
    with open(schemas_file, 'r') as f:
        content = f.read()
    
    print("🔧 Fixing Pydantic V2 compatibility issues...")
    
    # Fix 1: Replace orm_mode = True with from_attributes = True
    original_count = content.count('orm_mode = True')
    content = content.replace('orm_mode = True', 'from_attributes = True')
    print(f"✅ Fixed {original_count} instances of 'orm_mode = True'")
    
    # Fix 2: Remove duplicate orm_mode lines in Config classes
    # Pattern to find Config classes with both from_attributes and orm_mode
    config_pattern = r'(class Config:\s*\n(?:\s*[^}]*\n)*?\s*from_attributes = True\s*\n)(\s*orm_mode = True\s*\n)'
    content = re.sub(config_pattern, r'\1', content, flags=re.MULTILINE)
    
    # Fix 3: Replace schema_extra with json_schema_extra if any exist
    if 'schema_extra' in content:
        content = content.replace('schema_extra', 'json_schema_extra')
        print("✅ Fixed 'schema_extra' references")
    
    # Write the fixed content back
    with open(schemas_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed Pydantic V2 compatibility in {schemas_file}")
    
    return True

if __name__ == "__main__":
    try:
        fix_pydantic_v2_issues()
        print("\n🎉 All Pydantic V2 compatibility issues fixed!")
    except Exception as e:
        print(f"❌ Error fixing Pydantic issues: {e}")

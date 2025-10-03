#!/usr/bin/env python3
"""
Fix Duplicate Request Parameters
Removes duplicate request parameters that were added by the comprehensive fix
"""

import os
import re
import sys

def fix_duplicate_request_params(file_path):
    """Fix duplicate request parameters in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match functions with duplicate request parameters
    # This will match: request: Request, request: Request, 
    duplicate_pattern = r'(\s*request:\s*Request,\s*)(request:\s*Request,\s*)'
    
    # Replace duplicates with single request parameter
    content = re.sub(duplicate_pattern, r'\1', content)
    
    # Also handle cases where there might be more than 2 duplicates
    # Keep applying the pattern until no more matches
    while re.search(duplicate_pattern, content):
        content = re.sub(duplicate_pattern, r'\1', content)
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def get_python_files():
    """Get all Python files that might have duplicates"""
    python_files = []
    
    # Search in API directories
    search_dirs = ['app/api/v1/', 'app/']
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
    
    return python_files

def check_for_duplicates(file_path):
    """Check if a file has duplicate request parameters"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for duplicate request parameters
        if re.search(r'request:\s*Request,\s*request:\s*Request', content):
            return True
        
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
    
    return False

def main():
    print("🔧 FIXING DUPLICATE REQUEST PARAMETERS")
    print("=" * 50)
    print("Scanning for duplicate request: Request parameters...\n")
    
    # Get all Python files
    python_files = get_python_files()
    
    files_with_duplicates = []
    files_fixed = []
    
    # Check each file for duplicates
    for file_path in python_files:
        if check_for_duplicates(file_path):
            files_with_duplicates.append(file_path)
            print(f"❌ Found duplicates in: {file_path}")
    
    if not files_with_duplicates:
        print("✅ No duplicate request parameters found!")
        return 0
    
    print(f"\n🔧 Fixing {len(files_with_duplicates)} files...")
    
    # Fix each file
    for file_path in files_with_duplicates:
        try:
            if fix_duplicate_request_params(file_path):
                files_fixed.append(file_path)
                print(f"✅ Fixed: {file_path}")
            else:
                print(f"⚠️ No changes needed: {file_path}")
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
    
    print(f"\n📊 SUMMARY")
    print("=" * 50)
    print(f"✅ Fixed {len(files_fixed)} files")
    print(f"📁 Files with duplicates found: {len(files_with_duplicates)}")
    
    if files_fixed:
        print(f"\n📝 Fixed files:")
        for file_path in files_fixed:
            print(f"   • {file_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

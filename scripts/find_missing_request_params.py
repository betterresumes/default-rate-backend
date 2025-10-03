#!/usr/bin/env python3
"""
Find and fix missing request parameters in rate-limited functions
"""

import os
import re
import glob

def check_file_for_missing_request(file_path):
    """Check a Python file for rate-limited functions missing request parameter"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all rate-limited functions
    rate_limit_pattern = r'@rate_limit_\w+\s*\n\s*async def (\w+)\s*\([^)]*\):'
    matches = re.finditer(rate_limit_pattern, content, re.MULTILINE)
    
    issues = []
    for match in matches:
        func_name = match.group(1)
        func_def = match.group(0)
        
        # Check if the function has request parameter
        if 'request:' not in func_def and 'request =' not in func_def:
            # Extract the full function signature
            start = match.start()
            end = content.find(':', match.end()) + 1
            full_signature = content[start:end]
            
            issues.append({
                'function': func_name,
                'signature': full_signature.strip(),
                'line': content[:start].count('\n') + 1
            })
    
    return issues

def main():
    """Check all API files for missing request parameters"""
    
    print("🔍 Checking for rate-limited functions missing request parameter...")
    
    api_files = glob.glob('app/api/v1/*.py')
    all_issues = {}
    
    for file_path in api_files:
        if os.path.basename(file_path).startswith('__'):
            continue
            
        issues = check_file_for_missing_request(file_path)
        if issues:
            all_issues[file_path] = issues
    
    if not all_issues:
        print("✅ No issues found! All rate-limited functions have request parameters.")
        return
    
    print(f"\n❌ Found {sum(len(issues) for issues in all_issues.values())} issues:")
    
    for file_path, issues in all_issues.items():
        print(f"\n📁 {file_path}:")
        for issue in issues:
            print(f"   ❌ Line {issue['line']}: {issue['function']}()")
            print(f"      Missing: request: Request parameter")
    
    print(f"\n🔧 Fix needed: Add 'request: Request' parameter to these functions")
    print(f"   Also ensure 'from fastapi import Request' is imported")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Complete Rate Limiting Fix - Find and Fix ALL Missing Request Parameters
"""

import os
import re
import sys

def get_all_rate_limited_files():
    """Get all Python files that contain rate limiting decorators"""
    files_with_rate_limits = []
    
    # Directories to search
    search_dirs = ['app/api/v1/', 'app/']
    
    for search_dir in search_dirs:
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if '@rate_limit_' in content:
                                files_with_rate_limits.append(file_path)
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
    
    return files_with_rate_limits

def analyze_rate_limited_function(file_path, content):
    """Analyze a file for rate-limited functions missing request parameter"""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if '@rate_limit_' in line and not line.strip().startswith('#'):
            # Found a rate limit decorator
            decorator_line = i
            
            # Find the corresponding function
            func_start = i + 1
            while func_start < len(lines):
                func_line = lines[func_start].strip()
                if func_line.startswith('async def ') or func_line.startswith('def '):
                    break
                if func_line and not func_line.startswith('@') and not func_line.startswith('#'):
                    # No function found, might be a different construct
                    break
                func_start += 1
            
            if func_start < len(lines):
                func_line = lines[func_start]
                
                # Get complete function signature (might span multiple lines)
                signature = func_line
                paren_count = signature.count('(') - signature.count(')')
                line_idx = func_start + 1
                
                while paren_count > 0 and line_idx < len(lines):
                    next_line = lines[line_idx]
                    signature += ' ' + next_line.strip()
                    paren_count += next_line.count('(') - next_line.count(')')
                    line_idx += 1
                
                # Extract function name
                func_match = re.search(r'async def (\w+)|def (\w+)', func_line)
                if func_match:
                    func_name = func_match.group(1) or func_match.group(2)
                    
                    # Check if request parameter exists
                    if 'request:' not in signature and 'request =' not in signature:
                        issues.append({
                            'file': file_path,
                            'line': func_start + 1,
                            'function': func_name,
                            'decorator_line': decorator_line + 1,
                            'signature': signature.strip()
                        })
    
    return issues

def fix_function_signature(file_path, function_name, signature):
    """Fix a function signature by adding request parameter"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the function and add request parameter
    pattern = rf'(async def {function_name}\s*\(\s*)'
    
    def replacer(match):
        return f"{match.group(1)}request: Request, "
    
    new_content = re.sub(pattern, replacer, content)
    
    # Also ensure Request is imported
    if 'from fastapi import' in new_content:
        # Check if Request is already in the import
        if ', Request' not in new_content and 'Request,' not in new_content and 'Request)' not in new_content:
            # Add Request to existing fastapi import
            new_content = re.sub(
                r'from fastapi import ([^)]+)',
                r'from fastapi import \1, Request',
                new_content
            )
    else:
        # Add new import line
        new_content = 'from fastapi import Request\n' + new_content
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return new_content != content

def main():
    print("🔍 COMPREHENSIVE RATE LIMITING FIX")
    print("=" * 60)
    print("Scanning ALL files for rate-limited functions missing request parameter...\n")
    
    # Get all files with rate limiting
    rate_limited_files = get_all_rate_limited_files()
    print(f"Found {len(rate_limited_files)} files with rate limiting decorators")
    
    all_issues = []
    
    # Analyze each file
    for file_path in rate_limited_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = analyze_rate_limited_function(file_path, content)
            if issues:
                print(f"\n❌ {file_path}:")
                for issue in issues:
                    print(f"   Line {issue['line']}: {issue['function']} (missing request parameter)")
                all_issues.extend(issues)
            else:
                print(f"✅ {file_path}: OK")
                
        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
    
    if not all_issues:
        print(f"\n🎉 All {len(rate_limited_files)} files are correctly configured!")
        print("✅ No missing request parameters found")
        return 0
    
    print(f"\n🔧 FIXING {len(all_issues)} ISSUES...")
    print("=" * 60)
    
    # Group issues by file for efficient fixing
    files_to_fix = {}
    for issue in all_issues:
        file_path = issue['file']
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(issue)
    
    fixed_count = 0
    
    for file_path, issues in files_to_fix.items():
        print(f"\n🔧 Fixing {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            modified_content = original_content
            
            # Sort issues by line number in reverse order to avoid line number shifts
            issues.sort(key=lambda x: x['line'], reverse=True)
            
            for issue in issues:
                func_name = issue['function']
                
                # Add request parameter to function
                pattern = rf'(async def {re.escape(func_name)}\s*\(\s*)'
                
                if re.search(pattern, modified_content):
                    modified_content = re.sub(pattern, r'\1request: Request, ', modified_content)
                    print(f"   ✅ Fixed {func_name}")
                    fixed_count += 1
                else:
                    print(f"   ❌ Could not fix {func_name} - pattern not found")
            
            # Ensure Request is imported
            if 'from fastapi import' in modified_content and ', Request' not in modified_content:
                # Find existing fastapi import and add Request
                if re.search(r'from fastapi import ([^\\n]+)', modified_content):
                    modified_content = re.sub(
                        r'from fastapi import ([^\\n]+)',
                        lambda m: f"from fastapi import {m.group(1).rstrip()}, Request" if not 'Request' in m.group(1) else m.group(0),
                        modified_content
                    )
            
            # Write the fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            print(f"   💾 Saved {file_path}")
            
        except Exception as e:
            print(f"   ❌ Error fixing {file_path}: {e}")
    
    print(f"\n📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Fixed {fixed_count} functions across {len(files_to_fix)} files")
    print(f"📁 Files modified: {len(files_to_fix)}")
    
    if fixed_count > 0:
        print(f"\n🎯 Run this to verify fixes:")
        print(f"   python3 scripts/find_missing_request_params.py")
        return 0
    else:
        print(f"\n⚠️ No fixes applied - manual intervention may be needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Quick test script to verify the safe_quarter function works correctly
"""

def safe_quarter(value):
    """Convert quarter value to integer, handling Q1, Q2, Q3, Q4 format"""
    if value is None or value == '':
        return None
    
    # Handle string values
    if isinstance(value, str):
        value = value.strip().upper()
        
        # Handle Q1, Q2, Q3, Q4 format
        if value.startswith('Q') and len(value) == 2:
            try:
                quarter_num = int(value[1])
                if 1 <= quarter_num <= 4:
                    return quarter_num
            except ValueError:
                pass
        
        # Handle direct number strings
        try:
            quarter_num = int(value)
            if 1 <= quarter_num <= 4:
                return quarter_num
        except ValueError:
            pass
    
    # Handle integer values
    elif isinstance(value, int):
        if 1 <= value <= 4:
            return value
    
    # Return None for invalid values
    return None

def test_safe_quarter():
    """Test cases for safe_quarter function"""
    test_cases = [
        # (input, expected_output)
        ("Q1", 1),
        ("Q2", 2), 
        ("Q3", 3),
        ("Q4", 4),
        ("q1", 1),  # lowercase
        ("q4", 4),  # lowercase  
        ("1", 1),   # string number
        ("4", 4),   # string number
        (1, 1),     # integer
        (4, 4),     # integer
        ("Q5", None),  # invalid quarter
        ("Q0", None),  # invalid quarter
        ("5", None),   # invalid quarter string
        (5, None),     # invalid quarter integer
        ("", None),    # empty string
        (None, None),  # None value
        ("invalid", None),  # invalid string
    ]
    
    print("Testing safe_quarter function:")
    print("=" * 40)
    
    all_passed = True
    for i, (input_val, expected) in enumerate(test_cases, 1):
        result = safe_quarter(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"Test {i:2d}: {str(input_val):10} -> {str(result):4} (expected: {str(expected):4}) {status}")
        
        if result != expected:
            all_passed = False
    
    print("=" * 40)
    print(f"Overall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    test_safe_quarter()

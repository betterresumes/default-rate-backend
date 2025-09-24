# Celery Error Fixes Summary

## Issues Fixed

### 1. ❌ NaN Input Error in ML Models
**Error**: `Input X contains NaN. LogisticRegression does not accept missing values encoded as NaN natively`

**Root Cause**: The ML models were receiving NaN values after the binned scoring process, causing the LogisticRegression model to fail.

**Fixes Applied**:

1. **Improved `binned_runscoring` function** in both `ml_service.py` and `quarterly_ml_service.py`:
   - Better handling of None, NaN, and missing values
   - Added fallback values when data doesn't fall in any bin (returns first rate instead of None)
   - Enhanced NaN detection and replacement

2. **Added NaN detection and filling** in ML prediction methods:
   - Check for NaN values in feature matrices before prediction
   - Fill NaN values with sensible defaults from scoring info
   - Provide clear warnings when NaN values are found and filled

### 2. ❌ Permission Error for Company Creation
**Error**: `Only super admin can create global companies`

**Root Cause**: Non-super-admin users were trying to create companies with `organization_id=None`, which the system interpreted as "global companies" that only super admins can create.

**Fix Applied**:

1. **Updated `create_or_get_company` function** in `tasks.py`:
   - Changed logic to allow non-super-admin users to create user-specific companies
   - When `organization_id=None` and user is not super admin, create `is_global=False` companies
   - Only super admins can create actual global companies (`is_global=True`)
   - Added proper company lookup for user-specific companies vs global companies

### 3. ✅ Improved Error Handling
**Bonus fixes**:

1. **Better exception handling** in Celery tasks:
   - Return error dictionaries instead of raising exceptions to avoid serialization issues
   - Added proper database session cleanup with `finally` blocks
   - Fixed duplicate `finally` statements that caused syntax errors

2. **Enhanced Celery configuration**:
   - Added better result backend settings for error handling
   - Improved Redis connection configuration

## Files Modified

1. **`app/services/ml_service.py`**:
   - Enhanced `binned_runscoring` method with better NaN handling
   - Added NaN detection and filling in prediction method

2. **`app/services/quarterly_ml_service.py`**:
   - Enhanced `binned_runscoring` method with better NaN handling
   - Added NaN detection and filling in prediction method
   - Updated to use only logistic probability as main probability (per user request)

3. **`app/workers/tasks.py`**:
   - Fixed `create_or_get_company` function to allow user-specific companies
   - Improved error handling in both annual and quarterly bulk upload tasks
   - Added proper database session cleanup

4. **`app/workers/celery_app.py`**:
   - Enhanced Celery configuration for better error handling
   - Added result backend transport options

## Expected Results

After these fixes:

✅ **NaN values** will be properly handled by filling them with sensible defaults from scoring information

✅ **Non-super-admin users** can create companies within their scope (user-specific companies when they have no organization)

✅ **Celery tasks** will complete successfully without serialization errors

✅ **Both annual and quarterly** bulk uploads should work properly

## Usage Notes

- **For Quarterly predictions**: The system now uses only the logistic model probability as the main probability (as requested)
- **Company creation**: Non-super-admin users create user-specific companies (not global ones)
- **Error handling**: Tasks return structured error responses instead of raising exceptions
- **NaN handling**: Missing or invalid financial data gets replaced with sensible defaults

The Celery worker should now run without the previous errors and successfully process both annual and quarterly bulk uploads.

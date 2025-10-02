# Archive Folder

This folder contains files that were moved out of the main project structure during CI/CD setup preparation.

## Contents:

### `/test-files/`
- `test_quarterly_fix.py` - Test script for verifying quarterly ML processing fix
- `QUARTERLY_PROCESSING_FIX_SUMMARY.md` - Comprehensive documentation of quarterly processing issues and solutions

### `/scripts/`
- Various development and testing scripts that were used during debugging and development
- Build scripts that are now replaced by CI/CD pipeline
- Database setup and migration scripts
- Performance optimization scripts
- Deployment helper scripts

### `/deployment-scripts/`
- Local deployment scripts
- Worker startup scripts
- Development environment scripts

### `/aws-setup-docs/` (moved from /aws/)
- AWS admin setup documentation
- Email templates for requesting access
- User setup guides
- Empty configuration files
- SSL security notices (duplicate)

## Note:
These files are kept for historical reference and may contain useful debugging information or scripts that could be needed in the future. They were removed from the main codebase to clean up the project structure before implementing CI/CD.

## Date Archived:
October 2, 2025

## Reason:
Cleaning up project structure before implementing CI/CD pipeline to automate build and deployment process.

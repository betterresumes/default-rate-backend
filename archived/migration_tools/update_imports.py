#!/usr/bin/env python3
"""
Script to update import paths after restructuring the codebase.
"""

import os
import re
from pathlib import Path

def update_imports_in_file(filepath, replacements):
    """Update import statements in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_import, new_import in replacements.items():
            content = re.sub(old_import, new_import, content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated imports in {filepath}")
        else:
            print(f"📝 No changes needed in {filepath}")
            
    except Exception as e:
        print(f"❌ Error updating {filepath}: {e}")

def main():
    """Update all import paths in the app directory."""
    
    # Define import path replacements
    replacements = {
        # Database imports
        r'from \.\.database import': 'from ...core.database import',
        r'from \.database import': 'from ..core.database import',
        r'from src\.database import': 'from app.core.database import',
        
        # Schema imports  
        r'from \.\.schemas import': 'from ...schemas.schemas import',
        r'from \.schemas import': 'from ..schemas.schemas import',
        r'from src\.schemas import': 'from app.schemas.schemas import',
        
        # Utils imports
        r'from \.\.tenant_utils import': 'from ...utils.tenant_utils import',
        r'from \.tenant_utils import': 'from ..utils.tenant_utils import',
        r'from src\.tenant_utils import': 'from app.utils.tenant_utils import',
        
        # Service imports
        r'from \.\.services import': 'from ...services.services import',
        r'from \.services import': 'from ..services.services import', 
        r'from src\.services import': 'from app.services.services import',
        
        r'from \.\.email_service import': 'from ...services.email_service import',
        r'from \.email_service import': 'from ..services.email_service import',
        r'from src\.email_service import': 'from app.services.email_service import',
        
        r'from \.\.ml_service import': 'from ...services.ml_service import',
        r'from \.ml_service import': 'from ..services.ml_service import',
        r'from src\.ml_service import': 'from app.services.ml_service import',
        
        r'from \.\.quarterly_ml_service import': 'from ...services.quarterly_ml_service import',
        r'from \.quarterly_ml_service import': 'from ..services.quarterly_ml_service import',
        r'from src\.quarterly_ml_service import': 'from app.services.quarterly_ml_service import',
        
        # Worker imports
        r'from \.\.celery_app import': 'from ...workers.celery_app import',
        r'from \.celery_app import': 'from ..workers.celery_app import',
        r'from src\.celery_app import': 'from app.workers.celery_app import',
        
        r'from \.\.tasks import': 'from ...workers.tasks import',
        r'from \.tasks import': 'from ..workers.tasks import',
        r'from src\.tasks import': 'from app.workers.tasks import',
        
        # Router imports (for main app)
        r'from src\.routers\.': 'from app.api.v1.',
        r'from \.routers\.': 'from .api.v1.',
    }
    
    # Find all Python files in app directory
    app_dir = Path('app')
    if not app_dir.exists():
        print("❌ app directory not found!")
        return
    
    python_files = list(app_dir.rglob('*.py'))
    
    print(f"🔍 Found {len(python_files)} Python files to update")
    print("=" * 50)
    
    for filepath in python_files:
        update_imports_in_file(filepath, replacements)
    
    print("=" * 50)
    print("✅ Import path updates complete!")

if __name__ == "__main__":
    main()

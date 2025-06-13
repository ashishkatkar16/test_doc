"""
Complete setup script for the document processing system
"""

import os
import sys
import subprocess
import logging
from pathlib import Path


def setup_environment():
    """Set up the complete environment"""

    print("🚀 Setting up Document Processing System...")

    # Create directory structure
    directories = [
        "app", "services", "workers", "templates",
        "robot_folder", "processed", "logs", "tests",
        "scripts", "docs", "backups"
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

    # Create empty __init__.py files
    init_files = [
        "app/__init__.py",
        "services/__init__.py",
        "workers/__init__.py",
        "tests/__init__.py"
    ]

    for init_file in init_files:
        Path(init_file).touch()
        print(f"✅ Created: {init_file}")

    # Copy environment file
    if not Path(".env").exists():
        if Path(".env.development").exists():
            import shutil
            shutil.copy(".env.development", ".env")
            print("✅ Created .env from .env.development")
        else:
            print("⚠️  Please create .env file with your configuration")

    print("\n🎉 Environment setup completed!")
    print("\nNext steps:")
    print("1. Update .env file with your configuration")
    print("2. Run: python scripts/init_db.py")
    print("3. Run: python scripts/seed_data.py (optional)")
    print("4. Run: docker-compose up -d")


if __name__ == "__main__":
    setup_environment()
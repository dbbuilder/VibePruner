#!/usr/bin/env python3
"""
Setup script for VibePruner
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Setup VibePruner environment"""
    print("🔧 Setting up VibePruner...")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Error: VibePruner requires Python 3.7 or higher")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Install requirements
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)
    
    # Create default config if it doesn't exist
    config_path = Path("config.json")
    if not config_path.exists():
        print("\n📝 Creating default configuration...")
        example_config = Path("config.example.json")
        if example_config.exists():
            config_path.write_text(example_config.read_text())
            print("✅ Created config.json from example")
        else:
            print("⚠️  Warning: config.example.json not found")
    
    # Make the main script executable on Unix-like systems
    if os.name != 'nt':
        vibepruner_path = Path("vibepruner.py")
        if vibepruner_path.exists():
            os.chmod(vibepruner_path, 0o755)
            print("\n✅ Made vibepruner.py executable")
    
    print("\n🎉 Setup complete! You can now run:")
    print("   python vibepruner.py /path/to/your/project")
    print("\nFor more information, see README.md")


if __name__ == "__main__":
    main()

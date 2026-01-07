"""
Quick setup and validation script.
Run this first time to ensure everything is configured correctly.
"""
import os
import sys
from pathlib import Path
import subprocess

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_python_version():
    """Check Python version is 3.10+"""
    print_header("Checking Python Version")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} detected")
        print("  Python 3.10 or higher is required")
        return False

def check_env_file():
    """Check if .env file exists"""
    print_header("Checking Environment File")
    env_path = Path(".env")
    
    if env_path.exists():
        print("✓ .env file exists")
        
        # Check if OpenAI key is set
        with open(env_path) as f:
            content = f.read()
            if "OPENAI_API_KEY=your_api_key_here" in content:
                print("⚠️  OpenAI API key not configured (using template value)")
                print("   Set ENABLE_AI_FEATURES=false for demo mode")
            elif "OPENAI_API_KEY=" in content:
                print("✓ OpenAI API key appears to be set")
        
        return True
    else:
        print("✗ .env file not found")
        print("  Creating from template...")
        
        try:
            import shutil
            shutil.copy(".env.example", ".env")
            print("✓ Created .env file")
            print("  Edit .env to configure your settings")
            return True
        except Exception as e:
            print(f"✗ Failed to create .env: {e}")
            return False

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'streamlit',
        'python-dotenv',
        'pydantic',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} not installed")
            missing.append(package)
    
    if missing:
        print("\n⚠️  Missing packages detected")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")
    
    dirs = [
        'uploads',
        'summaries',
        'uploads/temp',
        'logs',
    ]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            print(f"✓ Created {dir_name}/")
        else:
            print(f"✓ {dir_name}/ exists")
    
    return True

def print_next_steps():
    """Print next steps"""
    print_header("Setup Complete! 🎉")
    
    print("""
Next steps:

1. Configure your environment (optional):
   - Edit .env file
   - Set OPENAI_API_KEY (or leave ENABLE_AI_FEATURES=false)

2. Start the application:

   Option A - Use start script (Windows):
   $ .\\start.ps1

   Option B - Manual start:
   
   Terminal 1 (Backend):
   $ uvicorn app.main:app --reload
   
   Terminal 2 (Frontend):
   $ streamlit run streamlit_app.py

3. Validate everything works:
   $ python validate_demo.py

4. Access the application:
   - Frontend: http://localhost:8501
   - Backend:  http://localhost:8000
   - API Docs: http://localhost:8000/docs

See README.md for detailed documentation.
""")

def main():
    """Run setup checks"""
    print("\n" + "="*60)
    print("  CODEBASE EXPLAINER - SETUP WIZARD")
    print("="*60)
    
    all_passed = True
    
    # Run checks
    all_passed &= check_python_version()
    all_passed &= check_env_file()
    all_passed &= check_dependencies()
    all_passed &= create_directories()
    
    if all_passed:
        print_next_steps()
    else:
        print("\n⚠️  Setup incomplete. Please fix the issues above and run again.")
        sys.exit(1)

if __name__ == "__main__":
    main()

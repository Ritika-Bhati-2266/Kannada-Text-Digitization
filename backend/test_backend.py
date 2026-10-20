"""
Quick sanity check for backend configuration, dependencies, and health.
"""
import sys
import os

def test_environment():
    print("=== Testing Kannada Lipi Mitra Backend Setup ===")
    
    # 1. Test .env presence
    env_exists = os.path.exists(".env")
    print(f"[{'OK' if env_exists else 'WARN'}] .env file exists: {env_exists}")
    
    # 2. Test imports
    try:
        import fastapi
        import uvicorn
        import pydantic
        import PIL
        from gtts import gTTS
        print("[OK] Core Python packages imported successfully.")
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

    # 3. Test ocr_service loading
    try:
        from ocr_service import ocr_manager
        active_name = ocr_manager.get_configured_engine_name()
        print(f"[INFO] Active Engine: {active_name.upper()}")
        all_status = ocr_manager.check_all_engines()
        for name, info in all_status.items():
            ready_str = "READY" if info.get("ready") else f"NOT READY ({info.get('error')})"
            is_active = " [ACTIVE]" if name == active_name else ""
            print(f"  • {name.upper()}{is_active}: {ready_str}")
    except Exception as e:
        print(f"[ERROR] Failed to load ocr_service: {e}")
        return False

    print("\nSanity check passed!")
    return True

if __name__ == "__main__":
    test_environment()

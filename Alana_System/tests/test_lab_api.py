import os
import sys
from pathlib import Path

def test_alana_lab_integrity():
    print("--- Testing Alana Lab Integrity ---")
    lab_path = Path("data/sandbox/alana_lab.py")
    if not lab_path.exists():
        print("[ERRO]: alana_lab.py missing from sandbox!")
        return
    
    # Check if sandbox is in python path logic
    sandbox_dir = str(Path("data/sandbox").absolute())
    sys.path.append(sandbox_dir)
    
    try:
        import alana_lab
        print("[OK]: alana_lab imported successfully.")
        if hasattr(alana_lab, 'save_figure') and hasattr(alana_lab, 'save_metrics'):
            print("[OK]: alana_lab API matches expectations.")
        else:
            print("[ERRO]: alana_lab API missing functions!")
    except Exception as e:
        print(f"[ERRO]: Failed to import alana_lab: {e}")

if __name__ == "__main__":
    test_alana_lab_integrity()

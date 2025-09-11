# run.py  (place in your Main/ folder)

import os, sys, traceback

def main():
    # 1) Always run from the folder that contains this file
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    # 2) Ensure imports (main_menu, chess_offline, etc.) resolve from here
    if base not in sys.path:
        sys.path.insert(0, base)

    print("[run.py] cwd =", os.getcwd())
    try:
        from main_menu import run as run_menu
    except Exception as e:
        print("[run.py] Failed to import main_menu.run()")
        traceback.print_exc()
        input("Press Enter to exit...")
        return

    try:
        run_menu()
    except SystemExit:
        # allow pygame/sys.exit() to close cleanly
        pass
    except Exception:
        print("[run.py] Unhandled exception while running the menu:")
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Commits Mining and Classification Tool - Main Entry Point with Fallback
"""

import sys

if __name__ == "__main__":
    try:
        print("Commits Mining and Classification Tool")
        from ui.main_window import main
        main()
    except Exception as e:
        print(f"\n⚠️  Modern UI failed to launch: {e}")
        print("Falling back to legacy UI...\n")
        try:
            from gui import CommitsToolGUI
            app = CommitsToolGUI()
            app.mainloop()
        except Exception as fallback_error:
            print(f"❌ Both UIs failed!")
            print(f"Modern UI error: {e}")
            print(f"Legacy UI error: {fallback_error}")
            sys.exit(1)

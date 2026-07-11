"""
Simplified main application window - minimal version to debug crash
"""
import customtkinter as ctk
import sys
from ui.theme import get_theme
from ui.components import ModernLabel


class MainWindowSimple(ctk.CTk):
    """Simplified main application window."""
    
    def __init__(self):
        print("DEBUG: Before super().__init__()", flush=True)
        sys.stdout.flush()
        
        super().__init__()
        
        print("DEBUG: After super().__init__()", flush=True)
        sys.stdout.flush()
        
        self.title("CBSoft 2026 - Commits Analysis Suite")
        self.geometry("1600x950")
        
        print("DEBUG: Title and geometry set", flush=True)
        sys.stdout.flush()
        
        theme = get_theme()
        self.configure(fg_color=theme.bg_primary)
        
        print("DEBUG: Colors configured", flush=True)
        sys.stdout.flush()
        
        # Simple layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        print("DEBUG: Grid configured", flush=True)
        sys.stdout.flush()
        
        # Simple label
        frame = ctk.CTkFrame(self, fg_color=theme.card_bg)
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        label = ModernLabel(frame, text="CBSoft 2026", size="heading")
        label.pack(padx=10, pady=10)
        
        print("DEBUG: Widgets created", flush=True)
        sys.stdout.flush()


def main():
    """Launch the simple application."""
    try:
        print("Initializing CBSoft 2026 application...", flush=True)
        print(f"Platform: {sys.platform}", flush=True)
        if sys.platform == "linux":
            print(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}", flush=True)
        
        print("Creating main window...", flush=True)
        sys.stdout.flush()
        app = MainWindowSimple()
        
        print("Launching application...", flush=True)
        sys.stdout.flush()
        app.mainloop()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()

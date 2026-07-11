"""
Main application window with tab navigation and theme management.
"""
import customtkinter as ctk
import os
import sys
from ui.theme import get_theme, apply_theme_to_widget
from ui.components import ModernLabel, show_toast
from ui.tabs.mining_tab import MiningTab
from ui.tabs.classification_tab import ClassificationTab
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.file_manager_tab import FileManagerTab

# Fix for potential X11/display issues on Linux
if sys.platform == "linux":
    # Try to use xvfb-run or set display if needed
    if not os.environ.get("DISPLAY"):
        try:
            # Attempt to find a valid display
            import subprocess
            result = subprocess.run(["ps", "-e"], capture_output=True, timeout=2)
            if b"X11" not in result.stdout and b"Xvfb" not in result.stdout:
                # Try to use a virtual framebuffer if available
                pass
        except Exception:
            pass


class MainWindow(ctk.CTk):
    """Main application window with modern UI."""
    
    def __init__(self):
        try:
            super().__init__()
        except Exception as e:
            print(f"Error initializing CTk: {e}", file=sys.stderr)
            raise
        
        try:
            ctk.set_appearance_mode("Dark")
            ctk.set_default_color_theme("green")
            self.title("Commit Miner - Commits Analysis Suite")
            self.geometry("1600x950")
            
            self.theme = get_theme()
            self.configure(fg_color=self.theme.bg_primary)
        except Exception as e:
            print(f"Error configuring window: {e}", file=sys.stderr)
            raise
        
        try:
            # Main layout
            self.grid_rowconfigure(1, weight=1)
            self.grid_columnconfigure(0, weight=1)
            
            # Top header with title and theme toggle
            self._setup_header()
            
            # Tab navigation and content
            self._setup_tabs()
            
            # Status bar
            self._setup_status_bar()
            
            # Log callback
            self.log_messages = []
        except Exception as e:
            print(f"Error setting up UI: {e}", file=sys.stderr)
            self.destroy()
            raise
    
    def _setup_header(self):
        """Setup top header with title and controls."""
        header = ctk.CTkFrame(self, fg_color=self.theme.card_bg, border_color=self.theme.card_border, border_width=1)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)
        
        # Left: Title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="both", expand=True, padx=self.theme.PADDING_LG, pady=self.theme.PADDING_MD)
        
        title_label = ModernLabel(title_frame, text="Commit Miner", size="heading")
        title_label.pack(anchor="w")
        
        subtitle_label = ModernLabel(title_frame, text="Commits Mining & Classification Suite", size="label")
        subtitle_label.pack(anchor="w")
        
        # Right: Theme toggle
        controls_frame = ctk.CTkFrame(header, fg_color="transparent")
        controls_frame.pack(side="right", fill="both", expand=False, padx=self.theme.PADDING_LG, pady=self.theme.PADDING_MD)
        
        self.theme_btn = ctk.CTkButton(
            controls_frame,
            text="Light Mode",
            command=self._toggle_theme,
            fg_color=self.theme.button_bg,
            hover_color=self.theme.button_hover,
            text_color=self.theme.button_text,
            font=self.theme.FONT_LABEL,
            corner_radius=self.theme.BUTTON_RADIUS,
            width=120,
            height=self.theme.BUTTON_HEIGHT
        )
        self.theme_btn.pack()
        
        self.is_dark_mode = self.theme.mode == "dark"
    
    def _apply_theme(self):
        """Apply the current theme to the whole window."""
        theme = get_theme()
        ctk.set_appearance_mode("Dark" if theme.mode == "dark" else "Light")
        ctk.set_default_color_theme("green")
        self.configure(fg_color=theme.bg_primary)
        apply_theme_to_widget(self, theme)
        self._update_tab_display()
        self.theme_btn.configure(
            text="Light Mode" if theme.mode == "dark" else "Dark Mode",
            fg_color=theme.button_bg,
            hover_color=theme.button_hover,
            text_color=theme.button_text,
        )
        self.is_dark_mode = theme.mode == "dark"
    
    def _setup_tabs(self):
        """Setup tab navigation and content area."""
        # Tab buttons container
        tabs_frame = ctk.CTkFrame(self, fg_color=self.theme.card_bg, border_color=self.theme.card_border, border_width=1)
        tabs_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        tabs_frame.grid_columnconfigure(1, weight=1)
        tabs_frame.grid_rowconfigure(1, weight=1)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(tabs_frame, fg_color=self.theme.bg_secondary)
        nav_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        
        self.tab_buttons = {}
        tabs = ["Mining", "Classification", "Analysis", "Files"]
        tab_ids = ["mining", "classification", "analysis", "files"]
        
        for i, (tab_name, tab_id) in enumerate(zip(tabs, tab_ids)):
            btn = ctk.CTkButton(
                nav_frame,
                text=tab_name,
                command=lambda tid=tab_id: self._switch_tab(tid),
                fg_color=self.theme.bg_secondary,
                hover_color=self.theme.bg_tertiary,
                text_color=self.theme.text_primary,
                font=self.theme.FONT_LABEL,
                corner_radius=0,
                border_width=0,
                height=40
            )
            btn.pack(side="left", fill="x", expand=True)
            self.tab_buttons[tab_id] = btn
        
        # Content area
        self.content_frame = ctk.CTkFrame(tabs_frame, fg_color=self.theme.bg_primary)
        self.content_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Tab containers - created lazily on first access
        self.tabs = {}
        self.current_tab = "mining"
        
        # Schedule tab creation after window is rendered
        self.after(100, self._initialize_tabs)
    
    def _switch_tab(self, tab_id):
        """Switch to a different tab."""
        if self.current_tab in self.tabs:
            self.tabs[self.current_tab].on_hide()
            self.tabs[self.current_tab].grid_forget()
        
        self.current_tab = tab_id
        self.tabs[tab_id].grid(row=0, column=0, sticky="nsew")
        self.tabs[tab_id].on_show()
        
        self._update_tab_display()
    
    def _initialize_tabs(self):
        """Initialize tabs after window is rendered (deferred initialization)."""
        try:
            self.tabs["mining"] = MiningTab(self.content_frame, log_callback=self._log)
            
            self.tabs["classification"] = ClassificationTab(self.content_frame, log_callback=self._log)
            
            self.tabs["analysis"] = DashboardTab(self.content_frame, log_callback=self._log)
            
            self.tabs["files"] = FileManagerTab(self.content_frame)
            
            # Show first tab
            self._switch_tab(self.current_tab)
        except Exception as e:
            print(f"Error initializing tabs: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    def _update_tab_display(self):
        """Update tab button appearances."""
        for tab_id, btn in self.tab_buttons.items():
            if tab_id == self.current_tab:
                btn.configure(
                    fg_color=self.theme.accent,
                    hover_color=self.theme.accent_light,
                    text_color=self.theme.button_text
                )
            else:
                btn.configure(
                    fg_color=self.theme.bg_secondary,
                    hover_color=self.theme.bg_tertiary,
                    text_color=self.theme.text_primary
                )
    
    def _setup_status_bar(self):
        """Setup bottom status bar."""
        status_bar = ctk.CTkFrame(self, fg_color=self.theme.card_bg, border_color=self.theme.card_border, border_width=1, height=30)
        status_bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        status_bar.pack_propagate(False)
        
        self.status_label = ModernLabel(status_bar, text="Ready", size="label")
        self.status_label.pack(side="left", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
    
    def _toggle_theme(self):
        """Toggle between dark and light modes."""
        self.theme.toggle_mode()
        self._apply_theme()
        show_toast(self, f"Switched to {self.theme.mode} mode", level="info")
    
    def _log(self, message):
        """Central logging callback."""
        self.log_messages.append(message)
        # Keep only last 1000 messages
        if len(self.log_messages) > 1000:
            self.log_messages = self.log_messages[-1000:]


def main():
    """Launch the application."""
    try:
        print("Initializing Commit Miner application...")
        print(f"Platform: {sys.platform}")
        if sys.platform == "linux":
            print(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
        
        print("Creating main window...")
        app = MainWindow()
        
        print("Launching application...")
        app.mainloop()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

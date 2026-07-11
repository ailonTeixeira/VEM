"""
Base class for all tab views.
"""
import customtkinter as ctk
from ui.theme import get_theme


class BaseTab(ctk.CTkFrame):
    """Abstract base class for all tab views."""
    
    def __init__(self, master, **kwargs):
        theme = get_theme()
        super().__init__(
            master,
            fg_color=theme.bg_primary,
            **kwargs
        )
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
    
    def on_show(self):
        """Called when tab becomes visible. Override in subclasses."""
        pass
    
    def on_hide(self):
        """Called when tab becomes hidden. Override in subclasses."""
        pass

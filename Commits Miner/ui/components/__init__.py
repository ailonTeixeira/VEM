"""
Custom UI components for modern styling and functionality.
"""
import customtkinter as ctk
from tkinter import ttk
import threading
from ui.theme import get_theme


class ModernButton(ctk.CTkButton):
    """Enhanced button with modern styling."""
    
    def __init__(self, master, text="", command=None, state="normal", width=100, height=32, **kwargs):
        theme = get_theme()
        
        super().__init__(
            master,
            text=text,
            command=command,
            state=state,
            width=width,
            height=height,
            fg_color=theme.button_bg,
            hover_color=theme.button_hover,
            text_color=theme.button_text,
            font=theme.FONT_LABEL,
            corner_radius=theme.BUTTON_RADIUS,
            **kwargs
        )


class ModernEntry(ctk.CTkEntry):
    """Enhanced text entry with modern styling."""
    
    def __init__(self, master, placeholder="", **kwargs):
        theme = get_theme()
        
        super().__init__(
            master,
            fg_color=theme.input_bg,
            border_color=theme.input_border,
            text_color=theme.text_primary,
            placeholder_text=placeholder,
            font=theme.FONT_BODY,
            border_width=theme.BORDER_WIDTH,
            **kwargs
        )


class ModernLabel(ctk.CTkLabel):
    """Enhanced label with modern styling."""
    
    def __init__(self, master, text="", size="body", **kwargs):
        theme = get_theme()
        
        if size == "heading":
            font = theme.FONT_HEADING
        elif size == "subheading":
            font = theme.FONT_SUBHEADING
        elif size == "label":
            font = theme.FONT_LABEL
        else:  # body
            font = theme.FONT_BODY
        
        super().__init__(
            master,
            text=text,
            text_color=theme.text_primary,
            font=font,
            **kwargs
        )


class ModernCard(ctk.CTkFrame):
    """Card component with modern styling."""
    
    def __init__(self, master, title="", use_grid=False, **kwargs):
        theme = get_theme()
        
        super().__init__(
            master,
            fg_color=theme.card_bg,
            border_color=theme.card_border,
            border_width=theme.BORDER_WIDTH,
            corner_radius=theme.CARD_RADIUS,
            **kwargs
        )
        
        self.use_grid = use_grid
        
        # For grid-based layouts, configure the grid
        if use_grid:
            self.grid_columnconfigure(1, weight=1)
        
        if title:
            title_label = ModernLabel(self, text=title, size="subheading")
            if use_grid:
                title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=theme.PADDING_LG, pady=(theme.PADDING_LG, theme.PADDING_MD))
            else:
                title_label.pack(anchor="w", padx=theme.PADDING_LG, pady=(theme.PADDING_LG, theme.PADDING_MD))


class ToastNotification(ctk.CTkToplevel):
    """Non-blocking toast notification that appears and disappears automatically."""
    
    def __init__(self, master, message, level="info", duration=3000):
        """
        Args:
            master: Parent window
            message: Notification message text
            level: 'info', 'success', 'warning', 'error'
            duration: Time in milliseconds before auto-dismiss
        """
        super().__init__(master)
        self.withdraw()
        self.attributes("-topmost", True)
        self.geometry("400x80")
        self.resizable(False, False)
        
        theme = get_theme()
        
        # Set background color based on level
        if level == "success":
            bg_color = theme.success
        elif level == "error":
            bg_color = theme.error
        elif level == "warning":
            bg_color = theme.warning
        else:  # info
            bg_color = theme.info
        
        self.configure(fg_color=bg_color)
        
        # Message label
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            text_color="#ffffff",
            font=theme.FONT_BODY,
            wraplength=350
        )
        msg_label.pack(fill="both", expand=True, padx=theme.PADDING_LG, pady=theme.PADDING_MD)
        
        # Position top-right
        self.update()
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        x = screen_width - 420
        y = 20
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        
        # Auto-dismiss after duration
        self.after(duration, self.destroy)


def show_toast(parent, message, level="info", duration=3000):
    """Convenience function to show a toast notification."""
    ToastNotification(parent, message, level=level, duration=duration)


class ModernTooltip:
    """A professional floating tooltip for previewing long content."""
    
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
        self.text = ""
        self.theme = get_theme()

    def show_tip(self, text):
        """Display text in tooltip window."""
        self.text = text
        if self.tip_window or not self.text:
            return
        
        # Calculate position
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        
        self.tip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.attributes("-topmost", True)
        
        # Frame for border/padding
        container = ctk.CTkFrame(
            tw, 
            fg_color=self.theme.bg_tertiary,
            border_color=self.theme.accent,
            border_width=1,
            corner_radius=6
        )
        container.pack()
        
        label = ctk.CTkLabel(
            container, 
            text=self.text, 
            justify="left",
            font=self.theme.FONT_BODY,
            padx=10, 
            pady=5,
            wraplength=400
        )
        label.pack()

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class ModernProgressBar(ctk.CTkProgressBar):
    """Modern progress bar with percentage display (0-100%)."""
    
    def __init__(self, master, **kwargs):
        theme = get_theme()
        super().__init__(
            master,
            fg_color=theme.bg_tertiary,
            progress_color=theme.accent,
            border_width=0,
            **kwargs
        )
        
        self.set(0)
    
    def set(self, value):
        """Set progress bar value (0-100)."""
        # CTkProgressBar expects 0.0-1.0
        normalized_value = max(0.0, min(1.0, value / 100.0))
        super().set(normalized_value)


class ModernLogViewer(ctk.CTkTextbox):
    """Enhanced log viewer with monospace font and color coding."""
    
    def __init__(self, master, **kwargs):
        theme = get_theme()
        
        super().__init__(
            master,
            fg_color=theme.log_bg,
            text_color=theme.log_text,
            font=theme.FONT_MONO,
            border_color=theme.card_border,
            border_width=theme.BORDER_WIDTH,
            **kwargs
        )
    
    def log(self, message, level="info"):
        """Add a timestamped log message with color coding."""
        import datetime
        theme = get_theme()
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Determine color based on level
        if level == "error":
            color = theme.log_error
        elif level == "warning":
            color = theme.log_warning
        elif level == "success":
            color = theme.log_success
        else:  # info
            color = theme.text_secondary
        
        # Configure tag for color
        self.tag_config(level, foreground=color)
        
        # Insert with tag
        self.insert("end", log_entry + "\n", level)
        self.see("end")  # Auto-scroll to bottom


class CollapsibleSection(ctk.CTkFrame):
    """Collapsible frame section for organizing related options."""
    
    def __init__(self, master, title="", **kwargs):
        theme = get_theme()
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.is_expanded = True
        self.content_frame = None
        
        # Header with toggle button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=theme.PADDING_MD, pady=(theme.PADDING_MD, 0))
        
        self.toggle_btn = ModernButton(
            header,
            text=f"▼ {title}",
            width=30,
            height=24,
            command=self._toggle
        )
        self.toggle_btn.pack(anchor="w")
        
        self.title_text = title
        
        # Content frame (collapsible)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=theme.PADDING_MD, pady=(0, theme.PADDING_MD))
    
    def _toggle(self):
        """Toggle content visibility."""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.content_frame.pack(fill="both", expand=True)
            self.toggle_btn.configure(text=f"▼ {self.title_text}")
        else:
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text=f"► {self.title_text}")
    
    def get_content_frame(self):
        """Return the content frame for adding child widgets."""
        return self.content_frame

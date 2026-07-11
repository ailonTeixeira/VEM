"""
Modern theme system with dark/light mode support for CommitsMiner.
"""
import customtkinter as ctk

_COLOR_ATTRS = (
    'bg_primary', 'bg_secondary', 'bg_tertiary',
    'text_primary', 'text_secondary', 'text_disabled',
    'button_bg', 'button_hover', 'button_active', 'button_disabled', 'button_text',
    'input_bg', 'input_border', 'input_border_focus',
    'card_bg', 'card_border',
    'log_bg', 'log_text',
    'accent', 'accent_light',
    'success', 'error', 'warning', 'info',
    'log_error', 'log_warning', 'log_success',
)

_REFERENCE_THEMES = {}


class Theme:
    """Central theme configuration for the application."""
    
    def __init__(self, mode="dark"):
        self.mode = mode
        self._init_colors()
    
    def _init_colors(self):
        """Initialize color scheme based on current mode."""
        if self.mode == "dark":
            self._init_dark_colors()
        else:
            self._init_light_colors()
    
    def _init_dark_colors(self):
        """Dark mode color palette."""
        # Primary colors
        self.bg_primary = "#1a1a1a"
        self.bg_secondary = "#2a2a2a"
        self.bg_tertiary = "#3a3a3a"
        self.accent = "#0d7377"
        self.accent_light = "#14a085"
        
        # Text colors
        self.text_primary = "#e0e0e0"
        self.text_secondary = "#a0a0a0"
        self.text_disabled = "#707070"
        
        # Status colors
        self.success = "#28a745"
        self.error = "#dc3545"
        self.warning = "#ffc107"
        self.info = "#17a2b8"
        
        # Component backgrounds
        self.button_bg = "#0d7377"
        self.button_hover = "#14a085"
        self.button_active = "#0a5c65"
        self.button_disabled = "#505050"
        self.button_text = "#ffffff"
        
        self.input_bg = "#2a2a2a"
        self.input_border = "#505050"
        self.input_border_focus = "#0d7377"
        
        self.card_bg = "#2a2a2a"
        self.card_border = "#404040"
        
        self.log_bg = "#1a1a1a"
        self.log_text = "#e0e0e0"
        self.log_error = "#ff6b6b"
        self.log_warning = "#ffd93d"
        self.log_success = "#51cf66"
    
    def _init_light_colors(self):
        """Light mode color palette."""
        self.bg_primary = "#eef1f6"
        self.bg_secondary = "#f6f8fb"
        self.bg_tertiary = "#dfe5ee"
        self.accent = "#0d7377"
        self.accent_light = "#109e84"

        self.text_primary = "#1e293b"
        self.text_secondary = "#64748b"
        self.text_disabled = "#94a3b8"

        self.success = "#15803d"
        self.error = "#b91c1c"
        self.warning = "#b45309"
        self.info = "#0369a1"

        self.button_bg = "#0d7377"
        self.button_hover = "#109e84"
        self.button_active = "#0a5c65"
        self.button_disabled = "#cbd5e1"
        self.button_text = "#ffffff"

        self.input_bg = "#ffffff"
        self.input_border = "#cbd5e1"
        self.input_border_focus = "#0d7377"

        self.card_bg = "#ffffff"
        self.card_border = "#d5dbe6"

        self.log_bg = "#f8fafc"
        self.log_text = "#334155"
        self.log_error = "#dc2626"
        self.log_warning = "#d97706"
        self.log_success = "#16a34a"
    
    def toggle_mode(self):
        """Switch between dark and light modes."""
        self.mode = "light" if self.mode == "dark" else "dark"
        self._init_colors()
    
    # Font configurations
    FONT_HEADING = ("Segoe UI", 16, "bold")
    FONT_SUBHEADING = ("Segoe UI", 12, "bold")
    FONT_LABEL = ("Segoe UI", 10)
    FONT_BODY = ("Segoe UI", 10)
    FONT_MONO = ("Courier New", 9)
    
    # Spacing
    PADDING_XS = 4
    PADDING_SM = 8
    PADDING_MD = 12
    PADDING_LG = 16
    PADDING_XL = 24
    
    # Sizes
    BUTTON_HEIGHT = 32
    INPUT_HEIGHT = 32
    CARD_RADIUS = 12
    BUTTON_RADIUS = 8
    
    # Borders
    BORDER_WIDTH = 1
    BORDER_STYLE = "solid"


# Global theme instance
_global_theme = Theme(mode="dark")


def get_theme():
    """Get the current global theme instance."""
    return _global_theme


def set_theme_mode(mode):
    """Set the global theme mode ('dark' or 'light')."""
    _global_theme.mode = mode
    _global_theme._init_colors()


def _reference_themes():
    if "dark" not in _REFERENCE_THEMES:
        _REFERENCE_THEMES["dark"] = Theme(mode="dark")
        _REFERENCE_THEMES["light"] = Theme(mode="light")
    return _REFERENCE_THEMES["dark"], _REFERENCE_THEMES["light"]


def map_theme_color(color, target_theme):
    """Map a color from either mode to the equivalent in target_theme."""
    if not color or str(color).lower() == "transparent":
        return color

    color_lower = str(color).lower()
    dark, light = _reference_themes()
    for attr in _COLOR_ATTRS:
        dark_val = getattr(dark, attr).lower()
        light_val = getattr(light, attr).lower()
        if color_lower == dark_val or color_lower == light_val:
            return getattr(target_theme, attr)
    return color


def is_accent_button(fg_color, theme):
    """Return True when a button uses the accent/action palette."""
    fg_lower = str(fg_color).lower()
    accent_colors = {
        theme.button_bg.lower(),
        theme.button_hover.lower(),
        theme.button_active.lower(),
        theme.accent.lower(),
        theme.accent_light.lower(),
    }
    dark, light = _reference_themes()
    for ref in (dark, light):
        accent_colors.update({
            ref.button_bg.lower(),
            ref.button_hover.lower(),
            ref.button_active.lower(),
            ref.accent.lower(),
            ref.accent_light.lower(),
        })
    return fg_lower in accent_colors


def apply_theme_to_widget(widget, theme):
    """Reconfigure a widget tree node with the current theme."""
    try:
        if isinstance(widget, ctk.CTkButton):
            fg_color = map_theme_color(widget.cget("fg_color"), theme)
            hover_color = map_theme_color(widget.cget("hover_color"), theme)
            text_color = (
                theme.button_text
                if is_accent_button(fg_color, theme)
                else map_theme_color(widget.cget("text_color"), theme)
            )
            widget.configure(
                fg_color=fg_color,
                hover_color=hover_color,
                text_color=text_color,
            )
        elif isinstance(widget, ctk.CTkEntry):
            widget.configure(
                fg_color=map_theme_color(widget.cget("fg_color"), theme),
                border_color=map_theme_color(widget.cget("border_color"), theme),
                text_color=map_theme_color(widget.cget("text_color"), theme),
            )
        elif isinstance(widget, ctk.CTkLabel):
            widget.configure(
                text_color=map_theme_color(widget.cget("text_color"), theme),
            )
        elif isinstance(widget, ctk.CTkFrame):
            fg_color = widget.cget("fg_color")
            if str(fg_color).lower() != "transparent":
                widget.configure(
                    fg_color=map_theme_color(fg_color, theme),
                    border_color=map_theme_color(widget.cget("border_color"), theme),
                )
        elif isinstance(widget, ctk.CTkTextbox):
            widget.configure(
                fg_color=map_theme_color(widget.cget("fg_color"), theme),
                text_color=map_theme_color(widget.cget("text_color"), theme),
                border_color=map_theme_color(widget.cget("border_color"), theme),
            )
        elif isinstance(widget, ctk.CTkProgressBar):
            widget.configure(
                fg_color=map_theme_color(widget.cget("fg_color"), theme),
                progress_color=map_theme_color(widget.cget("progress_color"), theme),
            )
        elif isinstance(widget, ctk.CTkComboBox):
            widget.configure(
                fg_color=theme.input_bg,
                text_color=theme.text_primary,
                border_color=theme.card_border,
                button_color=theme.accent,
                button_hover_color=theme.accent_light,
                dropdown_fg_color=theme.bg_secondary,
                dropdown_text_color=theme.text_primary,
                dropdown_hover_color=theme.bg_tertiary,
            )
        elif isinstance(widget, ctk.CTkScrollableFrame):
            fg_color = widget.cget("fg_color")
            if str(fg_color).lower() != "transparent":
                widget.configure(fg_color=map_theme_color(fg_color, theme))
    except Exception:
        pass

    for child in widget.winfo_children():
        apply_theme_to_widget(child, theme)

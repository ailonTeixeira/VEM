"""
File Manager Tab UI - CSV viewing and file browsing.
"""
import customtkinter as ctk
from tkinter import filedialog, scrolledtext
from tkinter import ttk
import pandas as pd
import os
import sys
from ui.tabs import BaseTab
from ui.theme import get_theme
from ui.components import ModernButton, ModernCard, ModernLabel, show_toast, ModernTooltip


class FileManagerTab(BaseTab):
    """Tab for browsing and viewing CSV files."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = get_theme()
        self.loaded_df = None
        self.loaded_file_path = None
        self.filtered_df = None
        self.original_df = None
        self.original_file_path = None
        self.page_size = 100
        self.current_page = 0
        self.total_pages = 0
        
        # Tooltip management
        self.tooltip = ModernTooltip(self)
        
        # Main layout
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=self.theme.PADDING_LG, pady=self.theme.PADDING_LG)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        
        # Top control bar
        self._setup_controls(main_container)
        
        # Table display area
        self._setup_table_area(main_container)
    
    def _setup_controls(self, parent):
        """Setup control bar at the top."""
        control_card = ModernCard(parent)
        control_card.grid(row=0, column=0, sticky="ew", pady=(0, self.theme.PADDING_MD))
        
        # Tools on the left
        left_controls = ctk.CTkFrame(control_card, fg_color="transparent")
        left_controls.pack(side="left", padx=10, pady=5)
        
        self.open_csv_btn = ModernButton(
            left_controls, 
            text="Open CSV", 
            command=self._open_csv
        )
        self.open_csv_btn.pack(side="left", padx=(0, 10))
        
        self.file_path_label = ModernLabel(
            left_controls, 
            text="No file selected"
        )
        self.file_path_label.pack(side="left")
        
        # Tools on the right
        right_controls = ctk.CTkFrame(control_card, fg_color="transparent")
        right_controls.pack(side="right", padx=10, pady=5)
        
        self.dir_btn = ModernButton(
            right_controls, 
            text="Open Directory", 
            command=self._open_directory
        )
        self.dir_btn.pack(side="left")

        # --- Diff Size Filter ---
        filter_frame = ctk.CTkFrame(control_card, fg_color="transparent")
        filter_frame.pack(side="right", padx=10, pady=5)

        self.min_diff_label = ModernLabel(filter_frame, text="Min Diff:")
        self.min_diff_label.pack(side="left", padx=5)

        self.min_diff_entry = ctk.CTkEntry(filter_frame, width=80, placeholder_text="e.g. 4000")
        self.min_diff_entry.pack(side="left", padx=5)

        self.max_diff_label = ModernLabel(filter_frame, text="Max Diff:")
        self.max_diff_label.pack(side="left", padx=5)

        self.max_diff_entry = ctk.CTkEntry(filter_frame, width=80, placeholder_text="e.g. 8000")
        self.max_diff_entry.pack(side="left", padx=5)

        self.filter_btn = ModernButton(
            filter_frame,
            text="Filter Dataset",
            command=self._filter_and_download
        )
        self.filter_btn.pack(side="left", padx=5)

        self.filter_range_btn = ModernButton(
            filter_frame,
            text="Filter Range",
            command=self._filter_range
        )
        self.filter_range_btn.pack(side="left", padx=5)

        self.save_filtered_btn = ModernButton(
            filter_frame,
            text="Save Filtered",
            command=self._save_filtered_dataset
        )
        self.save_filtered_btn.pack(side="left", padx=5)
        self.save_filtered_btn.configure(state="disabled")

        self.clear_filter_btn = ModernButton(
            filter_frame,
            text="Clear Filter",
            command=self._clear_filter
        )
        self.clear_filter_btn.pack(side="left", padx=5)
        self.clear_filter_btn.configure(state="disabled")

        repo_frame = ctk.CTkFrame(control_card, fg_color="transparent")
        repo_frame.pack(side="right", padx=10, pady=5)

        self.repo_dir_label = ModernLabel(repo_frame, text="Repos Dir:")
        self.repo_dir_label.pack(side="left", padx=5)

        self.repo_dir_entry = ctk.CTkEntry(repo_frame, width=180)
        self.repo_dir_entry.insert(0, "cloned_repos")
        self.repo_dir_entry.pack(side="left", padx=5)

        self.repo_dir_btn = ModernButton(
            repo_frame,
            text="Browse",
            command=self._browse_repos_dir
        )
        self.repo_dir_btn.pack(side="left", padx=5)
        
    def _setup_table_area(self, parent):
        """Setup the table display area with pagination."""
        table_frame = ctk.CTkFrame(parent, fg_color=self.theme.card_bg, border_color=self.theme.card_border, border_width=self.theme.BORDER_WIDTH, corner_radius=self.theme.CARD_RADIUS)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(0, self.theme.PADDING_MD))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Treeview with scrollbars
        treeview_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        treeview_frame.grid(row=0, column=0, sticky="nsew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        treeview_frame.grid_columnconfigure(0, weight=1)
        treeview_frame.grid_rowconfigure(0, weight=1)
        
        v_scrollbar = ttk.Scrollbar(treeview_frame, orient='vertical')
        h_scrollbar = ttk.Scrollbar(treeview_frame, orient='horizontal')
        
        self.table = ttk.Treeview(
            treeview_frame,
            show='headings',
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            height=15
        )
        
        v_scrollbar.config(command=self.table.yview)
        h_scrollbar.config(command=self.table.xview)
        
        self.table.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Enhanced Interactivity
        self.table.bind('<Double-1>', self._on_cell_double_click)
        self.table.bind('<Motion>', self._on_table_hover)
        self.table.bind('<Leave>', lambda e: self.tooltip.hide_tip())
        self.table.bind('<Button-1>', self._on_cell_click)
        
        # Pagination controls
        pagination_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        pagination_frame.grid(row=1, column=0, sticky="ew", padx=self.theme.PADDING_MD, pady=(self.theme.PADDING_MD, 0))
        pagination_frame.grid_columnconfigure(4, weight=1)
        
        ModernButton(pagination_frame, text="← Prev", width=60, command=self._prev_page).grid(row=0, column=0, padx=(0, self.theme.PADDING_SM))
        
        self.page_label = ModernLabel(pagination_frame, text="Page 1/1", size="label")
        self.page_label.grid(row=0, column=1, padx=self.theme.PADDING_SM)
        
        ModernButton(pagination_frame, text="Next →", width=60, command=self._next_page).grid(row=0, column=2, padx=(0, self.theme.PADDING_SM))
        
        ModernLabel(pagination_frame, text="Page size:", size="label").grid(row=0, column=3, padx=(0, self.theme.PADDING_SM))
        
        self.page_size_entry = ctk.CTkEntry(
            pagination_frame,
            width=60,
            fg_color=self.theme.input_bg,
            border_color=self.theme.card_border,
            text_color=self.theme.text_primary,
            font=self.theme.FONT_BODY,
            border_width=self.theme.BORDER_WIDTH
        )
        self.page_size_entry.insert(0, str(self.page_size))
        self.page_size_entry.grid(row=0, column=4, padx=(0, self.theme.PADDING_SM))
        
        ModernButton(pagination_frame, text="Set", width=50, command=self._set_page_size).grid(row=0, column=5)

        self.file_info_label = ModernLabel(pagination_frame, text="No file loaded", size="label")
        self.file_info_label.grid(row=1, column=0, columnspan=6, sticky="w", pady=(self.theme.PADDING_SM, 0))
    
    def _open_csv(self):
        """Open and load a CSV file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*")]
        )
        if not file_path:
            return
        
        try:
            df = pd.read_csv(file_path)
            self.loaded_df = df
            self.loaded_file_path = file_path
            self.filtered_df = None
            self.original_df = df
            self.original_file_path = file_path
            self.save_filtered_btn.configure(state="disabled")
            self.clear_filter_btn.configure(state="disabled")
            self.current_page = 0
            self.total_pages = max(1, (len(df) + self.page_size - 1) // self.page_size)
            
            self._populate_table()
            
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            self.file_path_label.configure(
                text=f"{os.path.basename(file_path)} • {len(df)} rows • {len(df.columns)} cols • {file_size:.2f} MB"
            )
            show_toast(self.master, "CSV loaded successfully", level="success")
        except Exception as e:
            show_toast(self.master, f"Failed to load CSV: {str(e)}", level="error")
    
    def _open_directory(self):
        """Open a directory and show path."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.file_path_label.configure(text=dir_path)
            show_toast(self, "Directory selected", "success")

    def _browse_repos_dir(self):
        """Browse for cloned repositories directory."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.repo_dir_entry.delete(0, "end")
            self.repo_dir_entry.insert(0, dir_path)

    def _filter_range(self):
        """Filter commits between min and max diff lengths."""
        try:
            min_size_str = self.min_diff_entry.get().strip()
            max_size_str = self.max_diff_entry.get().strip()
            if not min_size_str or not max_size_str:
                show_toast(self, "Enter both min and max diff sizes", "error")
                return
            min_size = int(min_size_str)
            max_size = int(max_size_str)
            if min_size > max_size:
                show_toast(self, "Min diff must be <= max diff", "error")
                return
        except ValueError:
            show_toast(self, "Invalid diff size format", "error")
            return

        if not self.loaded_file_path or not os.path.exists(self.loaded_file_path):
            show_toast(self, "No valid CSV loaded", "error")
            return

        preview_path = os.path.join(os.getcwd(), "filtered_preview.csv")
        repos_dir = self.repo_dir_entry.get().strip() or "cloned_repos"

        import subprocess
        script_path = os.path.join("scripts", "prompt_preview.py")
        cmd = [
            sys.executable, script_path,
            "--input", self.loaded_file_path,
            "--dir", repos_dir,
            "--filter-diff-min", str(min_size),
            "--filter-diff-max", str(max_size),
            "--filter-output", preview_path
        ]

        show_toast(self, f"Filtering dataset {min_size}-{max_size} chars...", "info")

        import threading
        def _run_filter():
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                filtered_df = pd.read_csv(preview_path)

                def _update_ui():
                    self.loaded_df = filtered_df
                    self.loaded_file_path = preview_path
                    self.filtered_df = filtered_df
                    self.current_page = 0
                    self.total_pages = max(1, (len(filtered_df) + self.page_size - 1) // self.page_size)
                    self._populate_table()

                    file_size = os.path.getsize(preview_path) / (1024 * 1024)
                    self.file_path_label.configure(
                        text=f"{os.path.basename(preview_path)} • {len(filtered_df)} rows • {len(filtered_df.columns)} cols • {file_size:.2f} MB"
                    )
                    self.save_filtered_btn.configure(state="normal")
                    self.clear_filter_btn.configure(state="normal")
                    show_toast(self, "Dataset successfully filtered!", "success")

                self.after(0, _update_ui)
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.strip() if e.stderr else str(e)
                self.after(0, lambda msg=err_msg: show_toast(self, f"Error running filter: {msg}", "error"))
                print(f"Filter Error: {err_msg}")
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: show_toast(self, f"Unexpected error: {msg}", "error"))
                print(f"Unexpected filter error: {err_msg}")

        threading.Thread(target=_run_filter, daemon=True).start()

    def _clear_filter(self):
        """Restore the original dataset after filtering."""
        if self.original_df is None or self.original_file_path is None:
            show_toast(self, "No original dataset loaded", "error")
            return

        self.loaded_df = self.original_df
        self.loaded_file_path = self.original_file_path
        self.filtered_df = None
        self.current_page = 0
        self.total_pages = max(1, (len(self.loaded_df) + self.page_size - 1) // self.page_size)
        self._populate_table()

        file_size = os.path.getsize(self.loaded_file_path) / (1024 * 1024)
        self.file_path_label.configure(
            text=f"{os.path.basename(self.loaded_file_path)} • {len(self.loaded_df)} rows • {len(self.loaded_df.columns)} cols • {file_size:.2f} MB"
        )
        self.save_filtered_btn.configure(state="disabled")
        self.clear_filter_btn.configure(state="disabled")
        show_toast(self, "Filter cleared", "success")

    def _save_filtered_dataset(self):
        """Save the currently filtered dataset to a user-selected file."""
        if self.filtered_df is None or self.filtered_df.empty:
            show_toast(self, "No filtered dataset to save", "error")
            return

        out_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Filtered Commits As"
        )
        if not out_path:
            return

        try:
            self.filtered_df.to_csv(out_path, index=False)
            show_toast(self, f"Filtered dataset saved to {os.path.basename(out_path)}", "success")
        except Exception as e:
            show_toast(self, f"Failed to save filtered dataset: {str(e)}", "error")

    def _filter_and_download(self):
        """Filters the currently loaded dataset based on diff size via prompt_preview.py script."""
        try:
            max_size_str = self.max_diff_entry.get().strip()
            if not max_size_str:
                show_toast(self, "Enter max diff size", "error")
                return
            max_size = int(max_size_str)
        except ValueError:
            show_toast(self, "Invalid max diff size format", "error")
            return
            
        if not self.loaded_file_path or not os.path.exists(self.loaded_file_path):
            show_toast(self, "No valid CSV loaded", "error")
            return

        preview_path = os.path.join(os.getcwd(), "filtered_preview.csv")

        import subprocess
        repos_dir = self.repo_dir_entry.get().strip() or "cloned_repos"
        script_path = os.path.join("scripts", "prompt_preview.py")
        cmd = [
            sys.executable, script_path,
            "--input", self.loaded_file_path,
            "--dir", repos_dir,
            "--filter-diff-max", str(max_size),
            "--filter-output", preview_path
        ]
        
        show_toast(self, f"Filtering dataset < {max_size} chars...", "info")
        
        import threading
        def _run_filter():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                filtered_df = pd.read_csv(preview_path)

                def _update_ui():
                    self.loaded_df = filtered_df
                    self.loaded_file_path = preview_path
                    self.filtered_df = filtered_df
                    self.current_page = 0
                    self.total_pages = max(1, (len(filtered_df) + self.page_size - 1) // self.page_size)
                    self._populate_table()

                    file_size = os.path.getsize(preview_path) / (1024 * 1024)
                    self.file_path_label.configure(
                        text=f"{os.path.basename(preview_path)} • {len(filtered_df)} rows • {len(filtered_df.columns)} cols • {file_size:.2f} MB"
                    )
                    self.save_filtered_btn.configure(state="normal")
                    self.clear_filter_btn.configure(state="normal")
                    show_toast(self, "Dataset successfully filtered!", "success")

                self.after(0, _update_ui)
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.strip() if e.stderr else str(e)
                self.after(0, lambda msg=err_msg: show_toast(self, f"Error running filter: {msg}", "error"))
                print(f"Filter Error: {err_msg}")
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: show_toast(self, f"Unexpected error: {msg}", "error"))
                print(f"Unexpected filter error: {err_msg}")

        threading.Thread(target=_run_filter, daemon=True).start()

    def _populate_table(self):
        """Populate table with current page data."""
        if self.loaded_df is None:
            return
        
        # Clear existing items
        self.table.delete(*self.table.get_children())
        
        # Setup columns
        cols = list(self.loaded_df.columns.astype(str))
        self.table['columns'] = cols
        self.table['show'] = 'headings'
        
        for col in cols:
            self.table.heading(col, text=col)
            self.table.column(col, width=150, anchor='w')
        
        # Get page data
        start = self.current_page * self.page_size
        end = min(len(self.loaded_df), start + self.page_size)
        page_data = self.loaded_df.iloc[start:end]
        
        # Insert rows
        for i, (idx, row) in enumerate(page_data.iterrows()):
            values = [str(row.get(c, '')) for c in cols]
            self.table.insert('', 'end', iid=i, values=values)
        
        # Update pagination label
        self.page_label.configure(text=f"Page {self.current_page + 1}/{self.total_pages}")
        
        # Update file info
        total_rows = len(self.loaded_df)
        showing_start = start + 1
        showing_end = end
        self.file_info_label.configure(
            text=f"{os.path.basename(self.loaded_file_path)} • Showing rows {showing_start}-{showing_end} of {total_rows}"
        )
    
    def _prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._populate_table()
    
    def _next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._populate_table()
    
    def _set_page_size(self):
        """Update page size."""
        try:
            new_size = int(self.page_size_entry.get())
            if new_size <= 0:
                raise ValueError()
            self.page_size = new_size
            self.total_pages = max(1, (len(self.loaded_df) + self.page_size - 1) // self.page_size)
            self.current_page = 0
            self._populate_table()
            show_toast(self.master, f"Page size set to {new_size}", level="success")
        except ValueError:
            show_toast(self.master, "Page size must be a positive integer", level="error")
    
    def _on_table_hover(self, event):
        """Show full content in a tooltip on hover."""
        region = self.table.identify('region', event.x, event.y)
        if region == 'cell':
            row_id = self.table.identify_row(event.y)
            col_id = self.table.identify_column(event.x)
            
            if row_id and col_id:
                col_index = int(col_id.replace('#', '')) - 1
                try:
                    # Get values from loaded_df using current pagination
                    row_index = int(row_id)
                    df_index = self.current_page * self.page_size + row_index
                    val = str(self.loaded_df.iloc[df_index, col_index])
                    
                    # Only show if value is long or has newlines
                    if len(val) > 20 or '\n' in val:
                        self.tooltip.show_tip(val)
                    else:
                        self.tooltip.hide_tip()
                except:
                    self.tooltip.hide_tip()
        else:
            self.tooltip.hide_tip()

    def _on_cell_click(self, event):
        """Auto-expand row height or prepare for detail view."""
        region = self.table.identify('region', event.x, event.y)
        if region == 'cell':
            # Highlight selected row specifically
            pass

    def _on_cell_double_click(self, event):
        """Show cell content in a modern popup with word wrap."""
        region = self.table.identify('region', event.x, event.y)
        if region != 'cell':
            return
        
        row_id = self.table.identify_row(event.y)
        col_id = self.table.identify_column(event.x)
        
        if not row_id or not col_id:
            return
        
        col_index = int(col_id.replace('#', '')) - 1
        row_index = int(row_id)
        
        try:
            df_index = self.current_page * self.page_size + row_index
            cols = list(self.loaded_df.columns)
            cell_value = str(self.loaded_df.iloc[df_index, col_index])
        except:
            return
        
        # Create professional popup
        popup = ctk.CTkToplevel(self)
        popup.title("Detail View")
        popup.geometry("800x600")
        popup.attributes("-topmost", True)
        
        # Main layout
        content_frame = ctk.CTkFrame(popup, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=self.theme.PADDING_LG, pady=self.theme.PADDING_LG)
        
        # Header with Pill/Tag style
        header_frame = ctk.CTkFrame(content_frame, fg_color=self.theme.bg_tertiary, corner_radius=8)
        header_frame.pack(fill="x", pady=(0, self.theme.PADDING_MD))
        
        ModernLabel(header_frame, text=f"Column: {cols[col_index]}", size="subheading").pack(side="left", padx=15, pady=10)
        
        # Content display with modern styling
        text_container = ctk.CTkFrame(content_frame, fg_color=self.theme.bg_secondary, border_color=self.theme.card_border, border_width=1)
        text_container.pack(fill="both", expand=True)
        
        text_display = scrolledtext.ScrolledText(
            text_container,
            wrap="word",
            font=self.theme.FONT_MONO,
            bg=self.theme.bg_secondary,
            fg=self.theme.text_primary,
            insertbackground=self.theme.accent,
            padx=15,
            pady=15,
            borderwidth=0,
            highlightthickness=0
        )
        text_display.pack(fill="both", expand=True)
        text_display.insert("1.0", cell_value)
        text_display.configure(state="disabled")
        
        # Actions
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(self.theme.PADDING_MD, 0))
        
        ModernButton(button_frame, text="Copy to Clipboard", command=lambda: self._copy_to_clipboard(cell_value)).pack(side="right")
        ModernButton(button_frame, text="Close", command=popup.destroy, fg_color="transparent", border_width=1).pack(side="right", padx=10)
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.destroy()
        show_toast(self.master, "Copied to clipboard", level="success")
    
    def _clear_table(self):
        """Clear the table display."""
        self.table.delete(*self.table.get_children())
        self.table['columns'] = []
        self.loaded_df = None
        self.loaded_file_path = None
        self.filtered_df = None
        self.original_df = None
        self.original_file_path = None
        self.save_filtered_btn.configure(state="disabled")
        self.clear_filter_btn.configure(state="disabled")
        self.file_info_label.configure(text="No file loaded")
        show_toast(self.master, "Table cleared", level="info")

"""
Mining Tab UI - Repository search, cloning, and commit scanning.
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import json
from ui.tabs import BaseTab
from ui.theme import get_theme
from ui.components import (
    ModernButton, ModernCard, ModernEntry, ModernLabel, 
    ModernProgressBar, ModernLogViewer, CollapsibleSection,
    show_toast
)
from src.miner import GitHubMiner


class MiningTab(BaseTab):
    """Tab for GitHub repository mining and commit scanning."""
    
    def __init__(self, master, log_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = get_theme()
        self.log_callback = log_callback or print
        self.mining_thread = None
        self.is_mining = False
        
        # Create main layout: left form + right progress
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=self.theme.PADDING_LG, pady=self.theme.PADDING_LG)
        
        # Left panel: form (40%)
        left_panel = ctk.CTkScrollableFrame(main_container, fg_color="transparent", width=400)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, self.theme.PADDING_LG))
        
        self._setup_form(left_panel)
        
        # Right panel: progress (60%)
        right_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)
        right_panel.pack_propagate(False)
        
        self._setup_progress_panel(right_panel)
    
    def _setup_form(self, parent):
        """Setup the form section with search criteria."""
        # Search Criteria Card
        search_card = ModernCard(parent, title="Repository Search", use_grid=True)
        search_card.pack(fill="x", padx=0, pady=(0, self.theme.PADDING_MD))
        
        # Language
        ModernLabel(search_card, text="Language:", size="label").grid(row=1, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.lang_entry = ModernEntry(search_card)
        self.lang_entry.insert(0, "kotlin")
        self.lang_entry.grid(row=1, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Topic
        ModernLabel(search_card, text="Topic:", size="label").grid(row=2, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.topic_entry = ModernEntry(search_card)
        self.topic_entry.insert(0, "android")
        self.topic_entry.grid(row=2, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Min Stars
        ModernLabel(search_card, text="Min Stars:", size="label").grid(row=3, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.stars_entry = ModernEntry(search_card)
        self.stars_entry.insert(0, "500")
        self.stars_entry.grid(row=3, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # GitHub Token (sensitive)
        ModernLabel(search_card, text="GitHub Token:", size="label").grid(row=4, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.token_entry = ModernEntry(search_card, placeholder="Enter your GitHub token", show="*")
        self.token_entry.grid(row=4, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Output Configuration Card
        output_card = ModernCard(parent, title="Output Configuration", use_grid=True)
        output_card.pack(fill="x", padx=0, pady=(0, self.theme.PADDING_MD))
        
        # Max Repos
        ModernLabel(output_card, text="Max Repos:", size="label").grid(row=1, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.max_repos_entry = ModernEntry(output_card)
        self.max_repos_entry.insert(0, "100")
        self.max_repos_entry.grid(row=1, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Max Commits per Repo
        ModernLabel(output_card, text="Max Commits/Repo:", size="label").grid(row=2, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.max_commits_entry = ModernEntry(output_card, placeholder="Leave empty for all")
        self.max_commits_entry.grid(row=2, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Recent Activity
        ModernLabel(output_card, text="Recent Activity (YYYY-MM-DD):", size="label").grid(row=3, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.recent_activity_entry = ModernEntry(output_card)
        self.recent_activity_entry.insert(0, "2023-01-01")
        self.recent_activity_entry.grid(row=3, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Output CSV Path
        ModernLabel(output_card, text="Output CSV:", size="label").grid(row=4, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        csv_frame = ctk.CTkFrame(output_card, fg_color="transparent")
        csv_frame.grid(row=4, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        csv_frame.grid_columnconfigure(0, weight=1)
        self.output_csv_entry = ModernEntry(csv_frame)
        self.output_csv_entry.insert(0, "mined_commits.csv")
        self.output_csv_entry.grid(row=0, column=0, sticky="ew")
        ModernButton(csv_frame, text="Browse", width=80, command=self._browse_output_csv).grid(row=0, column=1, padx=(self.theme.PADDING_SM, 0))
        
        # Repos Directory
        ModernLabel(output_card, text="Repos Dir:", size="label").grid(row=5, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        repos_frame = ctk.CTkFrame(output_card, fg_color="transparent")
        repos_frame.grid(row=5, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        repos_frame.grid_columnconfigure(0, weight=1)
        self.repos_dir_entry = ModernEntry(repos_frame)
        self.repos_dir_entry.insert(0, "cloned_repos")
        self.repos_dir_entry.grid(row=0, column=0, sticky="ew")
        ModernButton(repos_frame, text="Browse", width=80, command=self._browse_repos_dir).grid(row=0, column=1, padx=(self.theme.PADDING_SM, 0))
        
        # Keywords Configuration Card
        keywords_card = ModernCard(parent, title="Keywords Configuration", use_grid=True)
        keywords_card.pack(fill="both", expand=True, padx=0)
        keywords_card.grid_columnconfigure(0, weight=1)
        keywords_card.grid_rowconfigure(0, weight=1)
        
        # Keywords Editor
        self.keywords_text = ctk.CTkTextbox(
            keywords_card,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text_primary,
            border_color=self.theme.card_border,
            border_width=self.theme.BORDER_WIDTH,
            font=self.theme.FONT_MONO,
            height=150
        )
        self.keywords_text.grid(row=0, column=0, sticky="nsew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        
        # Default keywords
        default_keywords = {
            "EnergySmell": ["battery", "power", "energy", "wakelock", "drain", "sleep", "performance", "optimization", "efficient"],
            "ConcurrencySmell": ["race condition", "deadlock", "thread safety", "concurrency", "synchronize", "atomic", "volatile", "coroutine bug", "thread-safe"],
            "StorageBloatSmell": ["apk size", "storage", "bloat", "compress", "webp", "shrink", "proguard", "asset"],
            "SecurityVulnerability": ["security", "vulnerability", "cve-", "xss", "injection", "rce", "exploit", "harden", "sanitize"],
            "HighComplexityDebt": ["refactor", "cleanup", "simplify", "readability", "maintainability", "spaghetti", "tech debt", "refactoring"]
        }
        self.keywords_text.insert("0.0", json.dumps(default_keywords, indent=2))
        
        # Keywords buttons
        keywords_buttons = ctk.CTkFrame(keywords_card, fg_color="transparent")
        keywords_buttons.grid(row=1, column=0, padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        ModernButton(keywords_buttons, text="Load File", command=self._load_keywords_file).pack(side="left", padx=(0, self.theme.PADDING_SM))
        ModernButton(keywords_buttons, text="Save File", command=self._save_keywords_file).pack(side="left", padx=(0, self.theme.PADDING_SM))
    
    def _setup_progress_panel(self, parent):
        """Setup the right panel showing mining progress."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_rowconfigure(3, weight=0)
        
        # Status indicator
        status_frame = ModernCard(parent, title="Mining Status")
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.theme.PADDING_MD))
        
        self.status_label = ModernLabel(status_frame, text="⏸ Idle", size="subheading")
        self.status_label.pack(anchor="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        
        self.status_detail = ModernLabel(status_frame, text="Ready to start mining", size="body")
        self.status_detail.pack(anchor="w", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        # Progress bar
        progress_frame = ModernCard(parent, title="Progress")
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.theme.PADDING_MD))
        
        self.progress_bar = ModernProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=0, pady=self.theme.PADDING_MD)
        
        # Mining counter
        self.counter_label = ModernLabel(progress_frame, text="Commits: 0 scanned, 0 flagged", size="body")
        self.counter_label.pack(anchor="w", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        # Activity log
        log_frame = ModernCard(parent, title="Activity Log", use_grid=True)
        log_frame.grid( row=2, column=0, sticky="nsew", pady=0 )

        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_viewer = ModernLogViewer(log_frame, height=200)
        self.log_viewer.grid( row=1, column=0, columnspan=2, sticky="nsew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD )
        
        # Buttons area
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", pady=(self.theme.PADDING_MD, 0))

        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.start_button = ModernButton( button_frame, text="Start Mining", 
        command=self._start_mining, height=40)

        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, self.theme.PADDING_SM))

        self.stop_button = ModernButton(button_frame, text="Stop Mining", command=self.stop_mining, height=40 )
        self.stop_button.grid( row=0, column=1, sticky="ew", padx=(self.theme.PADDING_SM, 0) )
    
    def _start_mining(self):
        """Validate inputs and start mining in background thread."""
        # Validation
        token = self.token_entry.get().strip()
        if not token:
            show_toast(self.master, "GitHub Token is required", level="error")
            self.log_viewer.log("Error: GitHub Token is required", level="error")
            return
        
        try:
            keywords = json.loads(self.keywords_text.get("0.0", "end"))
        except json.JSONDecodeError:
            show_toast(self.master, "Keywords JSON is invalid", level="error")
            self.log_viewer.log("Error: Keywords JSON is invalid", level="error")
            return
        
        lang = self.lang_entry.get().strip()
        topic = self.topic_entry.get().strip()
        stars = self.stars_entry.get().strip()
        max_repos = self.max_repos_entry.get().strip()
        
        if not all([lang, topic, stars, max_repos]):
            show_toast(self.master, "All required fields must be filled", level="error")
            self.log_viewer.log("Error: All required fields must be filled", level="error")
            return
        
        # Disable button and start
        self.is_mining = True
        self.start_button.configure(state="disabled", text="Mining in progress...")
        self.status_label.configure(text="⏳ Mining in progress...")
        
        max_commits = self.max_commits_entry.get().strip()
        max_commits_val = int(max_commits) if max_commits else None
        recent_activity = self.recent_activity_entry.get().strip()
        
        query = f"language:{lang} topic:{topic} stars:>{stars}"
        if recent_activity:
            query += f" pushed:>={recent_activity}"
        
        output_csv = self.output_csv_entry.get().strip()
        repos_dir = self.repos_dir_entry.get().strip()
        
        def run_mining():
            try:
                self.miner = GitHubMiner(
                    token, query, int(max_repos), output_csv, repos_dir, 
                    keywords, self._log_with_level, max_commits_per_repo=max_commits_val
                )
                self.miner.mine()
                if self.miner.running:
                    self.after(0, self._mining_complete)
                else:
                    self.after(0, self._mining_stopped)
            except Exception as e:
                self._log_with_level(f"Mining failed: {str(e)}", level="error")
                self.after(0, self._mining_failed)
        
        self.mining_thread = threading.Thread(target=run_mining, daemon=True)
        self.mining_thread.start()
    
    def _log_with_level(self, message, level="info"):
        """Log message with level to both log viewer and callback."""
        self.log_viewer.log(message, level=level)
        self.log_callback(message)
        self.update()
    
    def _mining_complete(self):
        """Called when mining completes successfully."""
        self.is_mining = False
        self.start_button.configure(state="normal", text="Start Mining")
        self.status_label.configure(text="✓ Mining Complete")
        self.status_detail.configure(text="Check the output CSV for results")
        show_toast(self.master, "Mining completed successfully!", level="success")
    
    def _mining_failed(self):
        """Called when mining fails."""
        self.is_mining = False
        self.start_button.configure(state="normal", text="Start Mining")
        self.status_label.configure(text="✗ Mining Failed")
        self.status_detail.configure(text="Check the log for details")
        show_toast(self.master, "Mining failed. Check logs for details", level="error")
    
    def _mining_stopped(self):
        """Called when mining thread exits after user stop."""
        self.is_mining = False
        self.start_button.configure(state="normal", text="Start Mining")

    def stop_mining(self):
        """Stop Mining process."""
        self.is_mining = False
        if hasattr(self, "miner"):
            self.miner.stop()
        self.start_button.configure(
            state="normal",
            text="Start Mining"
        )
        self.status_label.configure(text="Mining stopped")
        self.status_detail.configure(text="Process paused by user")
        self.log_viewer.log(
            "Mining stop requested.",
            level="info"
        )

    def _browse_output_csv(self):
        """Browse and select output CSV file."""
        file_path = filedialog.asksaveasfilename(filetypes=[("CSV files", "*.csv")], defaultextension=".csv")
        if file_path:
            self.output_csv_entry.delete(0, "end")
            self.output_csv_entry.insert(0, file_path)
    
    def _browse_repos_dir(self):
        """Browse and select repos directory."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.repos_dir_entry.delete(0, "end")
            self.repos_dir_entry.insert(0, dir_path)
    
    def _load_keywords_file(self):
        """Load keywords from JSON file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.keywords_text.delete("0.0", "end")
                    self.keywords_text.insert("0.0", json.dumps(data, indent=2))
                show_toast(self.master, "Keywords loaded successfully", level="success")
            except Exception as e:
                show_toast(self.master, f"Failed to load keywords: {str(e)}", level="error")
    
    def _save_keywords_file(self):
        """Save keywords to JSON file."""
        file_path = filedialog.asksaveasfilename(filetypes=[("JSON files", "*.json")], defaultextension=".json")
        if file_path:
            try:
                keywords = json.loads(self.keywords_text.get("0.0", "end"))
                with open(file_path, 'w') as f:
                    json.dump(keywords, f, indent=2)
                show_toast(self.master, "Keywords saved successfully", level="success")
            except Exception as e:
                show_toast(self.master, f"Failed to save keywords: {str(e)}", level="error")

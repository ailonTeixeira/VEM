"""
Classification Tab UI - LLM-based commit classification with Ollama.
"""
import customtkinter as ctk
from tkinter import filedialog
import threading
from ui.tabs import BaseTab
from ui.theme import get_theme
from ui.components import (
    ModernButton, ModernCard, ModernEntry, ModernLabel, 
    ModernLogViewer, show_toast
)
from src.classifier import LLMClassifier


class ClassificationTab(BaseTab):
    """Tab for LLM-based classification of commits."""
    
    def __init__(self, master, log_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = get_theme()
        self.log_callback = log_callback or print
        self.classification_thread = None
        self.is_classifying = False
        
        # Main layout: left form + right progress
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
        """Setup the form section."""
        # LLM Configuration Card
        llm_card = ModernCard(parent, title="LLM Configuration", use_grid=True)
        llm_card.pack(fill="x", padx=0, pady=(0, self.theme.PADDING_MD))
        
        # Ollama Host
        ModernLabel(llm_card, text="Ollama Host:", size="label").grid(row=1, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.host_entry = ModernEntry(llm_card)
        self.host_entry.insert(0, "http://localhost:11440")
        self.host_entry.grid(row=1, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Provider selection
        ModernLabel(llm_card, text="Provider:", size="label").grid(row=1, column=2, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.provider_var = ctk.StringVar(value="ollama")
        self.provider_dropdown = ctk.CTkComboBox(llm_card, values=["ollama", "openai", "gemini"], variable=self.provider_var)
        self.provider_dropdown.grid(row=1, column=3, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Model
        ModernLabel(llm_card, text="Model:", size="label").grid(row=2, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.model_var = ctk.StringVar(value="GPT-OSS:20B")
        self.model_dropdown = ctk.CTkComboBox(
            llm_card,
            values=["aya:35b", "codegemma:7b", "codellama:7b", "codellama:70b", "deepseek-coder:6.7b", "deepseek-coder-v2:16b", "deepseek-r1:32b", "gemma2:9b", "gemma3:27b", "llama3:8b", "llama3:70b", "llama3.1:8b", "mistral:latest", "mistral:7b-instruct-v0.3-q8_0", "mistral-small3.2:latest", "phind-codellama:34b", "qwen3-coder-next:latest", "qwen2.5-coder:7b", "qwen3:30b", "qwen3-coder:30b", "wizardcoder:33b"],
            variable=self.model_var,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text_primary,
            border_color=self.theme.card_border,
            button_color=self.theme.accent,
            button_hover_color=self.theme.accent_light,
            dropdown_fg_color=self.theme.bg_secondary,
            dropdown_text_color=self.theme.text_primary,
            dropdown_hover_color=self.theme.bg_tertiary,
            font=self.theme.FONT_LABEL
        )
        self.model_dropdown.grid(row=2, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Temperature
        ModernLabel(llm_card, text="Temperature:", size="label").grid(row=3, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.temperature_entry = ModernEntry(llm_card)
        self.temperature_entry.insert(0, "0.1")
        self.temperature_entry.grid(row=3, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Max Tokens
        ModernLabel(llm_card, text="Max Tokens:", size="label").grid(row=4, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.max_tokens_entry = ModernEntry(llm_card)
        self.max_tokens_entry.insert(0, "256")
        self.max_tokens_entry.grid(row=4, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Diff Extensions
        ModernLabel(llm_card, text="Diff Extensions:", size="label").grid(row=5, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.diff_extensions_entry = ModernEntry(llm_card, placeholder="e.g., .kt,.java")
        self.diff_extensions_entry.insert(0, ".kt")
        self.diff_extensions_entry.grid(row=5, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Diff truncation size
        ModernLabel(llm_card, text="Diff text size:", size="label").grid(row=5, column=2, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.diff_trunc_entry = ModernEntry(llm_card)
        self.diff_trunc_entry.insert(0, "400000")
        self.diff_trunc_entry.grid(row=5, column=3, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)

        # API Key (for OpenAI/Gemini)
        ModernLabel(llm_card, text="API Key:", size="label").grid(row=6, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        self.api_key_entry = ModernEntry(llm_card, placeholder="Optional API key for OpenAI/Gemini")
        self.api_key_entry.grid(row=6, column=1, columnspan=3, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        
        # Input/Output Card
        io_card = ModernCard(parent, title="Input/Output", use_grid=True)
        io_card.pack(fill="x", padx=0, pady=(0, self.theme.PADDING_MD))
        
        # Input CSV
        ModernLabel(io_card, text="Input CSV:", size="label").grid(row=1, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        input_frame = ctk.CTkFrame(io_card, fg_color="transparent")
        input_frame.grid(row=1, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        input_frame.grid_columnconfigure(0, weight=1)
        self.input_csv_entry = ModernEntry(input_frame)
        self.input_csv_entry.insert(0, "mined_commits.csv")
        self.input_csv_entry.grid(row=0, column=0, sticky="ew")
        ModernButton(input_frame, text="Browse", width=80, command=self._browse_input_csv).grid(row=0, column=1, padx=(self.theme.PADDING_SM, 0))
        
        # Output CSV
        ModernLabel(io_card, text="Output CSV:", size="label").grid(row=2, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        output_frame = ctk.CTkFrame(io_card, fg_color="transparent")
        output_frame.grid(row=2, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        output_frame.grid_columnconfigure(0, weight=1)
        self.output_csv_entry = ModernEntry(output_frame)
        self.output_csv_entry.insert(0, "classified_commits.csv")
        self.output_csv_entry.grid(row=0, column=0, sticky="ew")
        ModernButton(output_frame, text="Browse", width=80, command=self._browse_output_csv).grid(row=0, column=1, padx=(self.theme.PADDING_SM, 0))
        
        # Repos Dir
        ModernLabel(io_card, text="Repos Dir:", size="label").grid(row=3, column=0, sticky="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        repos_frame = ctk.CTkFrame(io_card, fg_color="transparent")
        repos_frame.grid(row=3, column=1, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_SM)
        repos_frame.grid_columnconfigure(0, weight=1)
        self.repos_dir_entry = ModernEntry(repos_frame)
        self.repos_dir_entry.insert(0, "cloned_repos")
        self.repos_dir_entry.grid(row=0, column=0, sticky="ew")
        ModernButton(repos_frame, text="Browse", width=80, command=self._browse_repos_dir).grid(row=0, column=1, padx=(self.theme.PADDING_SM, 0))
        
        # Prompt Template Card
        prompt_card = ModernCard(parent, title="Prompt Template", use_grid=True)
        prompt_card.pack(fill="both", expand=True, padx=0)
        
        self.prompt_text = ctk.CTkTextbox(
            prompt_card,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text_primary,
            border_color=self.theme.card_border,
            border_width=self.theme.BORDER_WIDTH,
            font=self.theme.FONT_MONO,
            height=150
        )
        self.prompt_text.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        
        default_prompt = """
CONTEXT AND PERSONA
You are an automated static code analyst. Your expertise is identifying and classifying code smells in commits, focusing on the Kotlin ecosystem for Android. Your analysis should be technical, meticulous, and based exclusively on the metadata, message and changes (diff) provided.

TASK
Analyze the following COMMIT DATA by following these steps:
1. REVIEW the commit metadata (stats and files changed) to grasp the scope of the change.
2. INTERPRET the commit message to understand the developer's stated intent.
3. EXAMINE the code diff line by line to validate the actual changes.
4. CLASSIFY whether the changes correspond to fixing code smells from CODE SMELL CATEGORIES or NONE.
5. JUSTIFY your decision based on the evidence found in the diff and metadata.

COMMIT DATA
[METADATA]:
{commit_metadata}

[MESSAGE]:
{commit_message}

[DIFF]:
{commit_diff}

CODE SMELL CATEGORIES
Use ONLY these categories for your classification:
EnergySmell: Optimizations related to battery/CPU consumption (e.g., improper wakelock management, unnecessary polling, blocking operations in the main thread, inefficient coroutines).
ConcurrencySmell: Concurrency and thread-safety issues (e.g., race conditions, deadlocks, incorrect use of coroutine scopes/dispatchers, access to shared state without synchronization).
StorageBloatSmell: Storage optimizations (disk/APK) (e.g., removing redundant assets or resources, optimizing image size, clearing the cache, reducing disk writes).
SecurityVulnerability: Security vulnerability fixes (e.g., (exposure of sensitive data, lack of input sanitization, use of insecure APIs, or excessive permissions).
HighComplexityDebt: Refactoring to reduce technical debt and improve code structure (e.g., removing long methods, eliminating duplicate code, simplifying complex conditions, improving variable names).

OUTPUT FORMAT (STRICT)
Return ONLY a single valid JSON object. No markdown blocks, no code fences, no conversational text.
The JSON must contain exactly these two keys:

   "classification": "EnergySmell" | "ConcurrencySmell" | "StorageBloatSmell" | "SecurityVulnerability" | "HighComplexityDebt" | "None",
   "reason": "A short technical justification grounded in the diff evidence (1-4 sentences)."
"""
        
        self.prompt_text.insert("0.0", default_prompt)
        
        # Prompt buttons
        prompt_buttons = ctk.CTkFrame(prompt_card, fg_color="transparent")
        prompt_buttons.grid(row=2, column=0, columnspan=2, padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        ModernButton(prompt_buttons, text="Load File", command=self._load_prompt_file).pack(side="left", padx=(0, self.theme.PADDING_SM))
        ModernButton(prompt_buttons, text="Save File", command=self._save_prompt_file).pack(side="left", padx=(0, self.theme.PADDING_SM))
    
    def _setup_progress_panel(self, parent):
        """Setup the right panel showing classification progress."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_rowconfigure(3, weight=0)
        
        # Status indicator
        status_frame = ModernCard(parent, title="Classification Status")
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.theme.PADDING_MD))
        
        self.status_label = ModernLabel(status_frame, text="⏸ Idle", size="subheading")
        self.status_label.pack(anchor="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        
        self.status_detail = ModernLabel(status_frame, text="Ready to start classification", size="body")
        self.status_detail.pack(anchor="w", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        # Progress info
        progress_frame = ModernCard(parent, title="Processing")
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.theme.PADDING_MD))
        
        self.counter_label = ModernLabel(progress_frame, text="Commits: 0 / 0", size="body")
        self.counter_label.pack(anchor="w", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        
        self.resume_label = ModernLabel(progress_frame, text="", size="body")
        self.resume_label.pack(anchor="w", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
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

        self.start_button = ModernButton( button_frame, text="Start Classification", 
        command=self._start_classification, height=40)

        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, self.theme.PADDING_SM))

        self.stop_button = ModernButton(button_frame, text="Stop Classification", command=self.stop_classification, height=40 )
        self.stop_button.grid( row=0, column=1, sticky="ew", padx=(self.theme.PADDING_SM, 0) )
       
    def _start_classification(self):
        """Validate inputs and start classification in background thread."""
        input_csv = self.input_csv_entry.get().strip()
        output_csv = self.output_csv_entry.get().strip()
        repos_dir = self.repos_dir_entry.get().strip()
        host = self.host_entry.get().strip()
        model = self.model_var.get().strip()
        diff_extensions = self.diff_extensions_entry.get().strip()
        prompt = self.prompt_text.get("0.0", "end")
        
        if not all([input_csv, output_csv, repos_dir, host, model]):
            show_toast(self.master, "All required fields must be filled", level="error")
            self.log_viewer.log("Error: All required fields must be filled", level="error")
            return
        
        try:
            temperature = float(self.temperature_entry.get())
            max_tokens = int(self.max_tokens_entry.get())
        except ValueError:
            show_toast(self.master, "Temperature must be a number, Max Tokens must be an integer", level="error")
            self.log_viewer.log("Error: Invalid temperature or max tokens", level="error")
            return
        
        self.is_classifying = True
        self.start_button.configure(state="disabled", text="Classification in progress...")
        self.status_label.configure(text="⏳ Classification in progress...")
        
        def run_classification():
            try:
                provider = self.provider_var.get().strip()
                api_key = self.api_key_entry.get().strip() or None
                diff_trunc = int(self.diff_trunc_entry.get().strip() or 400000)
                self.classifier = LLMClassifier(
                    input_csv, output_csv, repos_dir, provider=provider, model=model, host=host,
                    temperature=temperature, max_tokens=max_tokens,
                    prompt_template=prompt, log_callback=self._log_with_level,
                    diff_extensions=diff_extensions, diff_trunc=diff_trunc, api_key=api_key
                )
                self.classifier.classify()
                if self.classifier.running:
                    self.after(0, self._classification_complete)
                else:
                    self.after(0, self._classification_stopped)
            except Exception as e:
                self._log_with_level(f"Classification failed: {str(e)}", level="error")
                self.after(0, self._classification_failed)
        
        self.classification_thread = threading.Thread(target=run_classification, daemon=True)
        self.classification_thread.start()
    
    def _log_with_level(self, message, level="info"):
        """Log message with level."""
        if "error" in message.lower():
            level = "error"
        elif "success" in message.lower() or "complete" in message.lower():
            level = "success"
        
        self.log_viewer.log(message, level=level)
        self.log_callback(message)
        self.update()
    
    def _classification_complete(self):
        """Called when classification completes successfully."""
        self.is_classifying = False
        self.start_button.configure(state="normal", text="Start Classification")
        self.status_label.configure(text="✓ Classification Complete")
        self.status_detail.configure(text="Check the output CSV for results")
        show_toast(self.master, "Classification completed successfully!", level="success")
    
    def _classification_failed(self):
        """Called when classification fails."""
        self.is_classifying = False
        self.start_button.configure(state="normal", text="Start Classification")
        self.status_label.configure(text="✗ Classification Failed")
        self.status_detail.configure(text="Check the log for details")
        show_toast(self.master, "Classification failed. Check logs for details", level="error")
    
    def _classification_stopped(self):
        """Called when classification thread exits after user stop."""
        self.is_classifying = False
        self.start_button.configure(state="normal", text="Start Classification")

    def stop_classification(self):
        """Stop Classification process."""
        self.is_classifying = False
        if hasattr(self, "classifier"):
            self.classifier.stop()
        self.start_button.configure(
            state="normal",
            text="Start Classification"
        )
        self.status_label.configure(text="Classification stopped")
        self.status_detail.configure(text="Process paused by user")
        self.log_viewer.log(
            "Classification stop requested.",
            level="info"
        )

    def _browse_input_csv(self):
        """Browse and select input CSV file."""
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.input_csv_entry.delete(0, "end")
            self.input_csv_entry.insert(0, file_path)
    
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
    
    def _load_prompt_file(self):
        """Load prompt template from file."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    self.prompt_text.delete("0.0", "end")
                    self.prompt_text.insert("0.0", content)
                show_toast(self.master, "Prompt loaded successfully", level="success")
            except Exception as e:
                show_toast(self.master, f"Failed to load prompt: {str(e)}", level="error")
    
    def _save_prompt_file(self):
        """Save prompt template to file."""
        file_path = filedialog.asksaveasfilename(filetypes=[("Text files", "*.txt")], defaultextension=".txt")
        if file_path:
            try:
                content = self.prompt_text.get("0.0", "end")
                with open(file_path, 'w') as f:
                    f.write(content)
                show_toast(self.master, "Prompt saved successfully", level="success")
            except Exception as e:
                show_toast(self.master, f"Failed to save prompt: {str(e)}", level="error")

"""
Dashboard Tab UI - Visualization and analysis of classification results.
"""
import customtkinter as ctk
from tkinter import filedialog
import threading
import webbrowser
import tempfile
from ui.tabs import BaseTab
from ui.theme import get_theme
from ui.components import ModernButton, ModernCard, ModernLabel, ModernLogViewer, show_toast
from src.analyzer import ClassificationAnalyzer
from plotly.io import to_html


class DashboardTab(BaseTab):
    """Tab for analyzing and visualizing classification results."""
    
    def __init__(self, master, log_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = get_theme()
        self.log_callback = log_callback or print
        self.selected_files = []
        self.analysis_thread = None
        
        # Main layout
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=self.theme.PADDING_LG, pady=self.theme.PADDING_LG)
        
        self._setup_controls(main_container)
        self._setup_results_panel(main_container)
    
    def _setup_controls(self, parent):
        """Setup file selection and analysis controls."""
        controls_card = ModernCard(parent, title="Classification Files")
        controls_card.pack(fill="x", pady=(0, self.theme.PADDING_MD))
        
        # File selection area
        self.files_display = ctk.CTkTextbox(
            controls_card,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text_primary,
            border_color=self.theme.card_border,
            border_width=self.theme.BORDER_WIDTH,
            font=self.theme.FONT_MONO,
            height=80
        )
        self.files_display.pack(fill="both", expand=True, padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        self.files_display.configure(state="disabled")
        
        # Control buttons
        button_frame = ctk.CTkFrame(controls_card, fg_color="transparent")
        button_frame.pack(fill="x", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        ModernButton(button_frame, text="Select CSV Files", command=self._select_csv_files).pack(side="left", padx=(0, self.theme.PADDING_SM))
        ModernButton(button_frame, text="Clear Selection", command=self._clear_selection).pack(side="left", padx=(0, self.theme.PADDING_SM))
        ModernButton(button_frame, text="Analyze", command=self._start_analysis, width=120).pack(side="left", padx=(0, self.theme.PADDING_SM))
    
    def _setup_results_panel(self, parent):
        """Setup results display area."""
        results_card = ModernCard(parent, title="Analysis Results", use_grid=True)
        results_card.pack(fill="both", expand=True)
        
        # Status and info
        info_frame = ctk.CTkFrame(results_card, fg_color="transparent")
        info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=self.theme.PADDING_MD, pady=self.theme.PADDING_MD)
        
        self.status_label = ModernLabel(info_frame, text="No analysis performed yet", size="body")
        self.status_label.pack(anchor="w")
        
        # Log viewer
        self.log_viewer = ModernLogViewer(results_card, height=150)
        self.log_viewer.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        # Results info
        results_info_frame = ctk.CTkFrame(results_card, fg_color="transparent")
        results_info_frame.grid(row=2, column=0, sticky="ew", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        self.results_info = ModernLabel(results_info_frame, text="Results will be displayed here", size="body")
        self.results_info.pack(anchor="w")
        
        # Open results button
        self.open_results_btn = ModernButton(
            results_card,
            text="Open Results in Browser",
            command=self._open_results,
            state="disabled"
        )
        self.open_results_btn.grid(row=3, column=0, sticky="ew", padx=self.theme.PADDING_MD, pady=(0, self.theme.PADDING_MD))
        
        self.last_results_path = None
    
    def _select_csv_files(self):
        """Select multiple CSV files for analysis."""
        file_paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
        if file_paths:
            for path in file_paths:
                # Extract model name from filename
                import os
                model_name = os.path.splitext(os.path.basename(path))[0].replace("commits_classification_", "").replace(".csv", "")
                
                # Check if already selected
                if not any(p == path for _, p in self.selected_files):
                    self.selected_files.append((model_name, path))
            
            self._update_files_display()
            show_toast(self.master, f"Added {len(file_paths)} file(s)", level="success")
    
    def _update_files_display(self):
        """Update the files display area."""
        self.files_display.configure(state="normal")
        self.files_display.delete("0.0", "end")
        
        if self.selected_files:
            for model_name, file_path in self.selected_files:
                self.files_display.insert("end", f"{model_name}: {file_path}\n")
        else:
            self.files_display.insert("0.0", "No files selected")
        
        self.files_display.configure(state="disabled")
    
    def _clear_selection(self):
        """Clear all selected files."""
        self.selected_files = []
        self._update_files_display()
        self.status_label.configure(text="Selection cleared")
        show_toast(self.master, "Files cleared", level="info")
    
    def _start_analysis(self):
        """Start analysis in background thread."""
        if len(self.selected_files) < 2:
            show_toast(self.master, "Select at least 2 CSV files for analysis", level="warning")
            self.log_viewer.log("Error: Need at least 2 CSV files for comparison", level="error")
            return
        
        self.status_label.configure(text="⏳ Analysis in progress...")
        self.open_results_btn.configure(state="disabled")
        
        def run_analysis():
            try:
                analyzer = ClassificationAnalyzer(self.selected_files, self._log_with_level)
                plots = analyzer.analyze()
                self.after(0, lambda: self._analysis_complete(plots))
            except Exception as e:
                self._log_with_level(f"Analysis failed: {str(e)}", level="error")
                self.after(0, self._analysis_failed)
        
        self.analysis_thread = threading.Thread(target=run_analysis, daemon=True)
        self.analysis_thread.start()
    
    def _analysis_complete(self, plots):
        """Called when analysis completes successfully."""
        # Generate combined HTML with modern dark theme
        html_content = f"""
        <html>
        <head>
            <title>Commit Miner - Scientific Analysis</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #1a1a1a;
                    --card: #2a2a2a;
                    --accent: #0d7377;
                    --accent-light: #14a085;
                    --text: #e0e0e0;
                    --text-muted: #a0a0a0;
                    --border: #3a3a3a;
                }}
                body {{ 
                    font-family: 'Roboto', sans-serif; 
                    background: var(--bg); 
                    color: var(--text);
                    margin: 0; 
                    padding: 40px; 
                }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                header {{ 
                    border-bottom: 2px solid var(--accent); 
                    padding-bottom: 20px; 
                    margin-bottom: 40px; 
                    text-align: center;
                }}
                h1 {{ color: var(--accent-light); margin: 0; font-size: 2.5em; }}
                .tagline {{ color: var(--text-muted); font-size: 1.1em; }}
                
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 30px; }}
                
                .card {{ 
                    background: var(--card); 
                    border-radius: 12px; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3); 
                    padding: 25px; 
                    border: 1px solid var(--border);
                    transition: transform 0.2s;
                }}
                .card:hover {{ transform: translateY(-5px); }}
                .card.full-width {{ grid-column: 1 / -1; }}
                
                h2 {{ color: var(--accent); margin-top: 0; font-size: 1.5em; border-left: 4px solid var(--accent); padding-left: 15px; }}
                
                .metric-box {{ text-align: center; padding: 20px; }}
                
                footer {{ 
                    margin-top: 60px; 
                    text-align: center; 
                    color: var(--text-muted); 
                    font-size: 0.9em; 
                    border-top: 1px solid var(--border);
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Commit Miner Analytics</h1>
                    <p class="tagline">Scientific Multi-LLM Benchmark & Stability Analysis</p>
                </header>
                
                <div class="grid">
        """
        
        # Priority mapping for layout
        priority = {
            'global_metrics': {'title': 'Global Reliability', 'class': 'full-width'},
            'pairwise_kappa': {'title': "Cohen's Kappa (Pairwise Agreement)", 'class': 'full-width'},
            'distributions': {'title': 'Category Prevalence', 'class': ''},
            'agreement_matrices': {'title': 'Agreement Matrices', 'class': ''},
            'ambiguity_analysis': {'title': 'Classification Uncertainty & Entropy', 'class': 'full-width'},
            'stability_radar': {'title': 'Model Robustness Profile', 'class': ''},
            'ensemble_consensus': {'title': 'Ensemble Decision Profile', 'class': ''}
        }

        for key, info in priority.items():
            if key in plots:
                fig = plots[key]
                html_content += f"""
                <div class="card {info['class']}">
                    <h2>{info['title']}</h2>
                    {to_html(fig, full_html=False, include_plotlyjs=False)}
                </div>
                """
        
        html_content += """
                </div>
                <footer>
                    Scientific Platform for LLM Commit Classification Analysis | Source: Commit Miner Suite 2026
                </footer>
            </div>
        </body>
        </html>
        """
        
        # Save to temp file
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            self.last_results_path = f.name
        
        self.status_label.configure(text="✓ Analysis complete")
        self.results_info.configure(text=f"Results generated. {len(plots)} visualizations created.")
        self.open_results_btn.configure(state="normal")
        show_toast(self.master, "Analysis completed successfully!", level="success")
    
    def _analysis_failed(self):
        """Called when analysis fails."""
        self.status_label.configure(text="✗ Analysis failed")
        self.open_results_btn.configure(state="disabled")
        show_toast(self.master, "Analysis failed. Check logs for details", level="error")
    
    def _log_with_level(self, message, level="info"):
        """Log message with level."""
        self.log_viewer.log(message, level=level)
        self.log_callback(message)
        self.update()
    
    def _open_results(self):
        """Open the results HTML file in browser."""
        if self.last_results_path:
            webbrowser.open(self.last_results_path)
            show_toast(self.master, "Opening results in browser...", level="info")
        else:
            show_toast(self.master, "No results to open. Run analysis first.", level="warning")

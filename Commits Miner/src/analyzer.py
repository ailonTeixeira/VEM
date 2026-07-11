import pandas as pd
import os
import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score
from collections import Counter
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import re
from scipy.stats import entropy
import statsmodels.stats.inter_rater as ir

class ClassificationAnalyzer:
    def __init__(self, csv_files_list, log_callback=None):
        # csv_files_list is list of (model_name, file_path)
        self.csv_files = {model: path for model, path in csv_files_list}
        self.log_callback = log_callback or print
        self.theme = {
            'bg': '#1a1a1a',
            'card': '#2a2a2a',
            'accent': '#0d7377',
            'accent_light': '#14a085',
            'text': '#e0e0e0',
            'text_muted': '#a0a0a0',
            'grid': '#3a3a3a',
            'colorscale': [[0, '#1a1a1a'], [0.5, '#0d7377'], [1, '#14a085']]
        }
        self.categories = [
            "EnergySmell",
            "ConcurrencySmell",
            "StorageBloatSmell",
            "SecurityVulnerability",
            "HighComplexityDebt",
            "None",
            "parse_error"
        ]

    def analyze(self):
        all_data = []
        for model, path in self.csv_files.items():
            df = self._load_data(path, model)
            if not df.empty:
                all_data.append(df)

        if not all_data:
            self.log_callback("No valid classification data found.")
            return {}

        # Merge all models on commit_sha using INNER join to ensure we only analyze common commits
        combined_df = None
        for df in all_data:
            model_name = df['model'].iloc[0]
            # Use inner join to keep only shared commits (intersection)
            temp = df[['commit_sha', 'classification_primary']].rename(columns={'classification_primary': model_name})
            if combined_df is None:
                combined_df = temp
            else:
                combined_df = pd.merge(combined_df, temp, on='commit_sha', how='inner')

        if combined_df is None or combined_df.empty:
            self.log_callback("No common commits found across all models.")
            return {}

        models = list(self.csv_files.keys())

        total_commits = len(combined_df)
        self.log_callback(f"Analyzing {total_commits} commits (union) across {len(models)} models.")

        plots = {}

        # 1. Fleiss' Kappa (Global Agreement)
        plots['global_metrics'] = self._calc_global_metrics(combined_df, models)

        # 1.5 Cohen's Kappa for Pairwise Model Comparisons
        plots['pairwise_kappa'] = self._plot_pairwise_kappa(combined_df, models)

        # 2. Advanced Distributions
        plots['distributions'] = self._plot_distributions(combined_df, models)

        # 3. Scientific Agreement Matrices
        plots['agreement_matrices'] = self._plot_agreement_matrices(combined_df, models)

        # 4. Ambiguity & Entropy Analysis
        plots['ambiguity_analysis'] = self._plot_ambiguity_analysis(combined_df, models)

        # 5. Stability Radar
        plots['stability_radar'] = self._plot_stability_radar(combined_df, models)

        # 6. Ensemble Consensus
        plots['ensemble_consensus'] = self._plot_ensemble_consensus(combined_df, models)

        # 7. Mock Ground Truth Analysis (if applicable)
        # Search for ground truth in columns
        ground_truth_col = None
        for col in combined_df.columns:
            if 'ground_truth' in col.lower() or 'label' in col.lower() or 'manual' in col.lower():
                ground_truth_col = col
                break

        if ground_truth_col:
            plots['performance_metrics'] = self._plot_performance_metrics(combined_df, models, ground_truth_col)

        # Attach metadata (total commits) so UI can display exact counts
        plots['meta'] = {'total_commits': total_commits}
        return plots

    def _load_data(self, file_path, model_name):
        try:
            df = pd.read_csv(file_path)
            
            # Remove duplicated SHAs in the same file to prevent join multiplication (fan-out)
            # We keep the first occurrence as the representant
            df = df.drop_duplicates(subset=['commit_sha'], keep='first')
            
            # Find classification column
            col = None
            for c in df.columns:
                if 'classification' in c.lower() and ('llm' in c.lower() or model_name.lower() in c.lower() or c.lower() == 'classification'):
                    col = c
                    break
            
            if col is None:
                self.log_callback(f"No classification column found in {file_path}")
                return pd.DataFrame()
            # Keep rows where the commit SHA exists. Do NOT drop rows with missing classification values
            # because missing/NaN should be treated as the 'None' category instead of being removed.
            df = df[['commit_sha', col]]
            df = df[df['commit_sha'].notna()]
            # Fill NaN classification values with explicit 'None' so they are counted in analyses
            df[col] = df[col].fillna('None')
            df['classification_primary'] = df[col].apply(self._normalize_class)
            df['model'] = model_name
            return df
        except Exception as e:
            self.log_callback(f"Failed to load {file_path}: {e}")
            return pd.DataFrame()

    def _normalize_class(self, val):
        if pd.isna(val): return "None"
        val = str(val).strip()
        # Extract from JSON if needed
        if val.startswith('{'):
            try:
                d = json.loads(val)
                val = d.get('classification', 'None')
            except: pass
        
        # Mapping to standard categories
        for cat in self.categories:
            if cat.lower() in val.lower():
                return cat
        return "None"

    def _calc_global_metrics(self, df, models):
        # Fleiss' Kappa
        # Prepare matrix of counts: rows=commits, cols=categories
        matrix = []
        for _, row in df[models].iterrows():
            counts = [list(row).count(cat) for cat in self.categories]
            matrix.append(counts)
        
        kappa = ir.fleiss_kappa(matrix)
        
        # Interpretation
        if kappa < 0: interp = "Poor"
        elif kappa <= 0.2: interp = "Slight"
        elif kappa <= 0.4: interp = "Fair"
        elif kappa <= 0.6: interp = "Moderate"
        elif kappa <= 0.8: interp = "Substantial"
        else: interp = "Almost Perfect"

        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = kappa,
            title = {'text': f"Fleiss' Kappa (Global Agreement)<br><span style='font-size:0.8em;color:gray'>{interp} Agreement</span>"},
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [-1, 1], 'tickwidth': 1},
                'bar': {'color': self.theme['accent']},
                'steps': [
                    {'range': [-1, 0], 'color': "#333"},
                    {'range': [0, 0.4], 'color': "#444"},
                    {'range': [0.4, 0.7], 'color': "#555"},
                    {'range': [0.7, 1], 'color': "#666"}
                ],
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': kappa
                }
            }
        ))
        fig.update_layout(paper_bgcolor=self.theme['bg'], font={'color': self.theme['text']}, height=400)
        return fig

    def _plot_pairwise_kappa(self, df, models):
        # Calculate Cohen's Kappa score for all pairs of models
        matrix = []
        for m1 in models:
            row_data = []
            for m2 in models:
                if m1 == m2:
                    row_data.append(1.0)
                else:
                    score = cohen_kappa_score(df[m1], df[m2])
                    row_data.append(round(score, 3))
            matrix.append(row_data)

        # Plot as a heatmap
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=models,
            y=models,
            colorscale=self.theme['colorscale'],
            text=matrix,
            texttemplate="%{text}",
            textfont={"size": 12},
            zmin=0, zmax=1
        ))

        fig.update_layout(
            title="Cohen's Kappa (Pairwise Model Agreement)",
            xaxis_title="Evaluator 1",
            yaxis_title="Evaluator 2",
            paper_bgcolor=self.theme['bg'],
            plot_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            height=500,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig

    def _plot_distributions(self, df, models):
        # Stacked Percentage Bar Chart
        data = []
        for model in models:
            dist = df[model].value_counts(normalize=True) * 100
            for cat in self.categories:
                data.append({
                    'Model': model,
                    'Category': cat,
                    'Percentage': dist.get(cat, 0)
                })
        
        plot_df = pd.DataFrame(data)
        fig = go.Figure()
        
        colors = ['#0d7377', '#14a085', '#25a18e', '#7ae582', '#9fffcb', '#004e64']
        
        for i, cat in enumerate(self.categories):
            cat_data = plot_df[plot_df['Category'] == cat]
            fig.add_trace(go.Bar(
                name=cat,
                x=cat_data['Model'],
                y=cat_data['Percentage'],
                marker_color=colors[i % len(colors)]
            ))

        fig.update_layout(
            barmode='stack',
            title="Class Distribution by Model (%)",
            paper_bgcolor=self.theme['bg'],
            plot_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            yaxis={'title': 'Percentage (%)', 'gridcolor': self.theme['grid']},
            xaxis={'title': 'LLM Models', 'gridcolor': self.theme['grid']},
            height=500,
            legend_title="Smell Categories"
        )
        return fig

    def _plot_agreement_matrices(self, df, models):
        n = len(models)
        agreement_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    agreement_matrix[i, j] = 1.0
                else:
                    # Calculate strict agreement (overlap ratio / Jaccard-ish)
                    agreement_matrix[i, j] = (df[models[i]] == df[models[j]]).mean()

        # Formatar como porcentagem para evitar confusão com o Kappa
        text_matrix = np.round(agreement_matrix * 100, 1)

        fig = go.Figure(data=go.Heatmap(
            z=agreement_matrix,
            x=models,
            y=models,
            colorscale=self.theme['colorscale'],
            text=text_matrix,
            texttemplate="%{text}%",
            hoverinfo='z'
        ))

        fig.update_layout(
            title="Pairwise Agreement (Exact Overlap %)",
            paper_bgcolor=self.theme['bg'],
            plot_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            height=500,
            width=600,
            margin=dict(t=50, l=100, r=50, b=50)
        )
        return fig

    def _plot_ambiguity_analysis(self, df, models):
        # Calculate entropy per commit
        def calc_entropy(row):
            counts = Counter(row)
            probs = [c/len(row) for c in counts.values()]
            return entropy(probs, base=2)

        df['entropy'] = df[models].apply(calc_entropy, axis=1)
        
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Entropy Distribution (Uncertainty)", "Top 10 Most Ambigous Commits"))
        
        # Histogram
        fig.add_trace(
            go.Histogram(x=df['entropy'], nbinsx=10, marker_color=self.theme['accent'], name="Entropy"),
            row=1, col=1
        )
        
        # High Entropy Commits
        top_ambiguous = df.sort_values('entropy', ascending=False).head(10)
        fig.add_trace(
            go.Bar(x=top_ambiguous['commit_sha'].str[:8], y=top_ambiguous['entropy'], marker_color=self.theme['accent_light'], name="Max Entropy"),
            row=1, col=2
        )

        fig.update_layout(
            paper_bgcolor=self.theme['bg'],
            plot_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            height=500,
            showlegend=False
        )
        return fig

    def _plot_stability_radar(self, df, models):
        # Stability = % of agreement with majority/consensus
        def get_consensus(row):
            counts = Counter(row)
            most_common = counts.most_common(1)[0]
            return most_common[0] if most_common[1] >= (len(row)/2) else "No Consensus"

        df['consensus'] = df[models].apply(get_consensus, axis=1)
        
        stability_scores = []
        for model in models:
            valid_consensus = df[df['consensus'] != "No Consensus"]
            if len(valid_consensus) > 0:
                score = (valid_consensus[model] == valid_consensus['consensus']).mean()
            else:
                score = 0
            stability_scores.append(score)

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=stability_scores + [stability_scores[0]],
            theta=models + [models[0]],
            fill='toself',
            marker=dict(color=self.theme['accent']),
            name='Model Stability'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], gridcolor=self.theme['grid']),
                bgcolor=self.theme['card']
            ),
            title="Model Stability Radar (% Consensus Alignment)",
            paper_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            height=500
        )
        return fig

    def _plot_ensemble_consensus(self, df, models):
        def consensus_type(row):
            counts = Counter(row)
            max_votes = counts.most_common(1)[0][1]
            if max_votes == len(models): return "Unanimous"
            if max_votes > (len(models)/2): return "Majority"
            return "Divergent"

        types = df[models].apply(consensus_type, axis=1)
        dist = types.value_counts(normalize=True) * 100
        
        fig = go.Figure(data=[go.Pie(
            labels=dist.index, 
            values=dist.values,
            hole=0.4,
            marker=dict(colors=['#0d7377', '#14a085', '#dc3545'])
        )])

        fig.update_layout(
            title="Ensemble Consensus Breakdown (%)",
            paper_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            height=400
        )
        return fig

    def _plot_performance_metrics(self, df, models, gt_col):
        # Case when ground truth is provided
        data = []
        for model in models:
            f1 = f1_score(df[gt_col], df[model], average='macro', labels=self.categories)
            data.append({'Model': model, 'Macro-F1': f1})
        
        plot_df = pd.DataFrame(data)
        fig = go.Figure(go.Bar(
            x=plot_df['Model'],
            y=plot_df['Macro-F1'],
            marker_color=self.theme['accent']
        ))
        
        fig.update_layout(
            title="Macro-F1 Performance (vs Ground Truth)",
            paper_bgcolor=self.theme['bg'],
            plot_bgcolor=self.theme['bg'],
            font={'color': self.theme['text']},
            yaxis=dict(range=[0, 1], gridcolor=self.theme['grid']),
            height=500
        )
        return fig

    def _build_report_html(self, df, df_list, models, agreement_matrix, overlap_matrix, jaccard_matrix, kappa_matrix, df_allowed=None, df_no_none=None, binary_df=None):
                total_commits = len(df)

                # Success rate per model
                success_rate = {m: df[m].notna().mean() * 100 for m in models}

                # Unanimous agreement
                unanimous = sum(1 for idx in df.index if len(set(df.loc[idx, models].tolist())) == 1)
                unanimous_rate = (unanimous / total_commits * 100) if total_commits else 0

                # Mean statistics across provided matrices
                mean_kappa = sum(sum(row) for row in kappa_matrix) / (len(models) ** 2)
                mean_agreement = sum(sum(row) for row in agreement_matrix) / (len(models) ** 2)
                mean_overlap = sum(sum(row) for row in overlap_matrix) / (len(models) ** 2)
                mean_jaccard = sum(sum(row) for row in jaccard_matrix) / (len(models) ** 2)

                rows = "".join([f"<tr><td>{model}</td><td>{success_rate[model]:.2f}%</td></tr>" for model in models])

                html = f"""
                <section style="margin-top:40px; padding:24px; background:#f6f7fb; border-radius:12px; border:1px solid #e0e3ef;">
                    <h2 style="margin-top:0;">Summary Report</h2>
                    <p>This report summarizes classification robustness and agreement across the selected models.</p>
                    <p><strong>Total commits analyzed:</strong> {total_commits}</p>

                    <h3>Robustness (Success Rate)</h3>
                    <table style="border-collapse:collapse; width:100%;">
                        <thead>
                            <tr>
                                <th style="text-align:left; border-bottom:1px solid #ccc; padding:6px;">Model</th>
                                <th style="text-align:left; border-bottom:1px solid #ccc; padding:6px;">Success Rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>

                    <h3>Agreement Overview</h3>
                    <ul>
                        <li><strong>Total common commits:</strong> {total_commits}</li>
                        <li><strong>Unanimous agreement:</strong> {unanimous_rate:.2f}%</li>
                        <li><strong>Mean agreement (exact):</strong> {mean_agreement:.3f}</li>
                        <li><strong>Mean overlap agreement:</strong> {mean_overlap:.3f}</li>
                        <li><strong>Mean Jaccard similarity:</strong> {mean_jaccard:.3f}</li>
                        <li><strong>Mean Cohen's Kappa:</strong> {mean_kappa:.3f}</li>
                    </ul>

                    <h3>Filtered Subsets</h3>
                    <ul>
                        <li><strong>Allowed categories (incl. None):</strong> {len(df_allowed) if df_allowed is not None else 0}</li>
                        <li><strong>Without None:</strong> {len(df_no_none) if df_no_none is not None else 0}</li>
                        <li><strong>Binary (None vs Category):</strong> {len(binary_df) if binary_df is not None else 0}</li>
                    </ul>
                </section>
                """
                return html

    def _build_filtered_plots(self, df_subset, models, suffix=""):
        plots = {}
        if df_subset.empty:
            return plots

        pie_models = [m for m in models if m in df_subset.columns]
        if pie_models:
            cols, rows = self._pie_grid(len(pie_models))
            specs = [[{'type': 'domain'} for _ in range(cols)] for _ in range(rows)]
            fig_pies = make_subplots(rows=rows, cols=cols, specs=specs, subplot_titles=pie_models)
            for i, model in enumerate(pie_models):
                r = (i // cols) + 1
                c = (i % cols) + 1
                dist = Counter(df_subset[model])
                fig_pies.add_trace(
                    go.Pie(labels=list(dist.keys()), values=list(dist.values()), name=model, hole=0.35),
                    row=r,
                    col=c,
                )
            fig_pies.update_layout(
                title=f"Class Distribution ({suffix.replace('_', ' ').strip().title()})",
                legend_orientation="h",
                height=350 * rows + 120,
                margin=dict(t=80, b=40, l=40, r=40),
            )
            plots[f'pie_distributions{suffix}'] = fig_pies

        agreement_matrix = []
        for i in range(len(models)):
            row = []
            for j in range(len(models)):
                if i == j:
                    row.append(1.0)
                else:
                    m1, m2 = models[i], models[j]
                    if m1 in df_subset.columns and m2 in df_subset.columns:
                        agreement = (df_subset[m1] == df_subset[m2]).mean()
                        row.append(agreement)
                    else:
                        row.append(0.0)
            agreement_matrix.append(row)

        agree_text = [[f'{val:.3f}' for val in row] for row in agreement_matrix]
        fig_agree = go.Figure(data=go.Heatmap(
            z=agreement_matrix,
            x=models,
            y=models,
            colorscale='Blues',
            zmin=0,
            zmax=1,
            hoverinfo='text',
        ))
        fig_agree.update_traces(text=agree_text, texttemplate="%{text}", textfont={"size":12, "color": "black"})
        for i, row in enumerate(agree_text):
            for j, text in enumerate(row):
                fig_agree.add_annotation(x=models[j], y=models[i], text=text, showarrow=False, font=dict(size=12, color="black"))
        fig_agree.update_layout(
            title=f"Agreement Matrix ({suffix.replace('_', ' ').strip().title()})",
            xaxis_title="Models",
            yaxis_title="Models",
            height=500,
            width=700,
        )
        plots[f'agreement_matrix{suffix}'] = fig_agree

        return plots
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QPushButton,
    QComboBox, QLabel, QProgressBar, QGroupBox, QCheckBox, QSplitter,
    QStatusBar, QMenuBar, QMenu, QPlainTextEdit, QDialog, QSpinBox,
    QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction

from models import Paper, CATEGORIES, CATEGORY_CODES
from database import Database


class StatisticsDialog(QDialog):
    """Popup window showing paper statistics with text-based bar charts."""

    BAR_CHAR = "\u2588"  # Full block character

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Statistics Dashboard")
        self.setMinimumSize(700, 600)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("QDialog { background-color: #1e1e1e; }")

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet("QTextBrowser { background-color: #1e1e1e; color: #d4d4d4; border: none; }")
        browser.setHtml(self._render_html())
        layout.addWidget(browser)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("QPushButton { background-color: #333; color: #d4d4d4; padding: 6px 20px; border: 1px solid #555; }")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    # ------------------------------------------------------------------
    # HTML rendering
    # ------------------------------------------------------------------

    def _render_html(self) -> str:
        overview = self.db.get_stats_overview()
        by_category = self.db.get_stats_by_category()
        by_month = self.db.get_stats_by_month(limit=12)
        top_authors = self.db.get_stats_top_authors(limit=10)

        meta_pct = (
            f"{overview['meta_analyses'] / overview['total'] * 100:.1f}"
            if overview['total'] > 0 else "0"
        )

        html = f"""
        <style>
            body {{ font-family: Consolas, monospace; font-size: 13px; background: #1e1e1e; color: #d4d4d4; }}
            h2 {{ color: #569cd6; border-bottom: 1px solid #333; padding-bottom: 4px; }}
            .card-row {{ display: flex; gap: 12px; margin-bottom: 16px; }}
            .card {{
                background: #252526; border: 1px solid #333; border-radius: 6px;
                padding: 12px 18px; text-align: center; min-width: 120px;
            }}
            .card-value {{ font-size: 22px; font-weight: bold; color: #4ec9b0; }}
            .card-label {{ font-size: 11px; color: #888; margin-top: 4px; }}
            .bar {{ color: #4ec9b0; }}
            .bar-hf {{ color: #f0c674; }}
            .bar-meta {{ color: #c586c0; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
            td {{ padding: 3px 8px; vertical-align: middle; }}
            td.label {{ text-align: right; width: 100px; color: #9cdcfe; white-space: nowrap; }}
            td.count {{ text-align: right; width: 60px; color: #b5cea8; }}
            .author-rank {{ color: #569cd6; }}
            .author-name {{ color: #d4d4d4; }}
            .author-count {{ color: #b5cea8; }}
        </style>

        <h2>Overview</h2>
        <table><tr>
            <td class="card" style="text-align:center">
                <div class="card-value">{overview['total']:,}</div>
                <div class="card-label">Total Papers</div>
            </td>
            <td class="card" style="text-align:center">
                <div class="card-value" style="color:#4ec9b0">{overview['arxiv']:,}</div>
                <div class="card-label">arXiv</div>
            </td>
            <td class="card" style="text-align:center">
                <div class="card-value" style="color:#f0c674">{overview['hugging_face']:,}</div>
                <div class="card-label">Hugging Face</div>
            </td>
            <td class="card" style="text-align:center">
                <div class="card-value" style="color:#dcdcaa">{overview['favorites']:,}</div>
                <div class="card-label">Favorites</div>
            </td>
            <td class="card" style="text-align:center">
                <div class="card-value" style="color:#c586c0">{overview['meta_analyses']:,}</div>
                <div class="card-label">Meta-analyses ({meta_pct}%)</div>
            </td>
        </tr></table>
        """

        # -- By category --
        html += "<h2>Papers by Category</h2><table>"
        max_cat = by_category[0][1] if by_category else 1
        for cat_code, count in by_category:
            cat_name = CATEGORIES.get(cat_code, cat_code)
            bar_len = int(count / max_cat * 30) if max_cat > 0 else 0
            bar = self.BAR_CHAR * max(bar_len, 1)
            html += (
                f'<tr>'
                f'<td class="label">{cat_name}</td>'
                f'<td class="bar">{bar}</td>'
                f'<td class="count">{count:,}</td>'
                f'</tr>'
            )
        html += "</table>"

        # -- By month --
        html += "<h2>Papers by Month (last 12)</h2><table>"
        max_month = by_month[0][1] if by_month else 1
        for month_str, count in by_month:
            bar_len = int(count / max_month * 30) if max_month > 0 else 0
            bar = self.BAR_CHAR * max(bar_len, 1)
            html += (
                f'<tr>'
                f'<td class="label">{month_str}</td>'
                f'<td class="bar-hf">{bar}</td>'
                f'<td class="count">{count:,}</td>'
                f'</tr>'
            )
        html += "</table>"

        # -- Top authors --
        html += "<h2>Top 10 Authors</h2><table>"
        for rank, (author, count) in enumerate(top_authors, 1):
            html += (
                f'<tr>'
                f'<td class="author-rank" style="width:30px">{rank}.</td>'
                f'<td class="author-name">{author}</td>'
                f'<td class="author-count" style="text-align:right">{count:,} papers</td>'
                f'</tr>'
            )
        html += "</table>"

        return html


# ============================================================
# Ollama AI suggestion worker
# ============================================================

class OllamaWorker(QThread):
    """Background thread that queries Ollama in batches and emits suggestions."""

    progress = Signal(int, str)   # (pct, message)
    result   = Signal(dict)       # {"paper": Paper, "reason": str}
    finished = Signal(int)        # total suggestions found
    error    = Signal(str)
    log      = Signal(str)

    BATCH_SIZE = 20
    ABSTRACT_MAX = 200

    def __init__(self, context: str, model: str, db):
        super().__init__()
        self.context = context
        self.model = model
        self.db = db
        self.keywords: list = []

    def _extract_keywords(self) -> list:
        """Extract 5-10 search keywords from the user context using LLM."""
        import json
        import re
        from ollama_client import OllamaClient

        prompt = f"""Extract 5-10 search keywords from this context for a paper database search.
Return ONLY a JSON array of strings, nothing else. Use singular forms. Be specific.
Context: {self.context}
Keywords:"""

        self.log.emit("Extracting search keywords from context...")
        try:
            raw = OllamaClient.generate(self.model, prompt, timeout=60)
            self.log.emit(f"Keyword extraction raw (first 300): {raw[:300]}")

            # Strip <thinking> blocks that some models add
            clean_raw = re.sub(r'<thinking>.*?</thinking>', '', raw, flags=re.DOTALL)
            clean_raw = re.sub(r'<think>.*?</think>', '', clean_raw, flags=re.DOTALL)

            # Try to extract JSON array from response
            start = clean_raw.find('[')
            end = clean_raw.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = clean_raw[start:end+1]
                keywords = json.loads(json_str)
                if isinstance(keywords, list):
                    # Filter to strings and limit to 10
                    keywords = [str(k).lower().strip() for k in keywords if isinstance(k, str)]
                    keywords = keywords[:10]
                    if keywords:
                        self.log.emit(f"Extracted keywords: {', '.join(keywords)}")
                        return keywords

            # Fallback: extract words manually from raw response
            words = re.findall(r'"([^"]+)"', raw)
            if words:
                # Filter common non-keyword responses
                words = [w for w in words if len(w) > 2 and w.lower() not in 
                        ['context', 'keywords', 'extract', 'search', 'return', 'here', 'some', 'these']]
                if words:
                    self.log.emit(f"Extracted keywords (fallback): {', '.join(words[:10])}")
                    return [w.lower() for w in words[:10]]

            # Last resort: extract significant words from context
            context_words = re.findall(r'\b[a-z]{4,}\b', self.context.lower())
            # Filter common words
            stopwords = {'need', 'want', 'looking', 'searching', 'find', 'have', 'with', 'that', 'this', 'from', 'which', 'would', 'could', 'should', 'about', 'into', 'using', 'paper', 'papers', 'research'}
            context_words = [w for w in context_words if w not in stopwords]
            if context_words:
                unique_words = list(dict.fromkeys(context_words))[:10]
                self.log.emit(f"Extracted keywords (from context): {', '.join(unique_words)}")
                return unique_words

            self.log.emit("Warning: Could not extract keywords, using empty list")
            return []
        except Exception as e:
            self.log.emit(f"Keyword extraction failed: {e}")
            return []

    def _keyword_match_score(self, paper, keywords: list) -> int:
        """Calculate keyword match score (0-100%)."""
        if not keywords:
            return 0
        text = f"{paper.title or ''} {paper.abstract or ''}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return int((matches / len(keywords)) * 100)

    def run(self):
        import traceback
        from ollama_client import OllamaClient, OllamaNotAvailableError

        try:
            # Step 1: Extract keywords from context
            self.keywords = self._extract_keywords()
            if not self.keywords:
                self.log.emit("No keywords extracted. Using all papers.")
                papers = self.db.get_all_papers()
            else:
                # Step 2: Calculate keyword match scores for all papers
                self.log.emit("Calculating keyword match scores...")
                all_papers = self.db.get_all_papers()
                scored_papers = []
                for p in all_papers:
                    kw_score = self._keyword_match_score(p, self.keywords)
                    scored_papers.append((kw_score, p))
                
                # Sort by keyword score descending, then by date
                scored_papers.sort(key=lambda x: (-x[0], x[1].published or ""))
                
                # Take top 100 papers (only those with at least 1 keyword match)
                matching = [(s, p) for s, p in scored_papers if s > 0]
                papers = [p for _, p in matching[:100]]
                top_scores = [s for s, _ in scored_papers[:10]]
                self.log.emit(
                    f"Keyword match: {len(matching)} papers matched at least 1 keyword "
                    f"(top 10 scores: {top_scores})"
                )
                if not papers:
                    self.log.emit(
                        "No papers matched any keyword. "
                        "Keywords may not be in the database. "
                        "Using top 50 most recent papers instead."
                    )
                    papers = [p for _, p in scored_papers[:50]]

            if not papers:
                self.log.emit("No papers in database.")
                self.finished.emit(0)
                return

            total_papers = len(papers)
            batches = [
                papers[i:i + self.BATCH_SIZE]
                for i in range(0, total_papers, self.BATCH_SIZE)
            ]
            total_batches = len(batches)
            self.log.emit(
                f"Starting AI analysis: {total_papers} papers in "
                f"{total_batches} batch(es)..."
            )

            seen_ids: set = set()
            total_found = 0

            for batch_idx, batch in enumerate(batches):
                if self.isInterruptionRequested():
                    self.log.emit("Analysis stopped by user.")
                    break

                pct = int((batch_idx / total_batches) * 100) if total_batches > 0 else 100
                msg = f"Analysing batch {batch_idx + 1}/{total_batches}..."
                self.progress.emit(pct, msg)

                prompt = self._build_prompt(batch)

                try:
                    self.log.emit(f"Prompt length: {len(prompt)} chars")
                    raw = OllamaClient.generate(
                        self.model, prompt, timeout=180
                    )
                    self.log.emit(f"Raw LLM response (first 500): {raw[:500]}")
                    suggestions = OllamaClient.extract_json(raw)
                    self.log.emit(f"Parsed {len(suggestions)} suggestion(s) from batch {batch_idx + 1}")
                except OllamaNotAvailableError as e:
                    self.error.emit(str(e))
                    return
                except Exception as e:
                    self.log.emit(f"Batch {batch_idx + 1} error: {e}")
                    continue

                # Map arxiv_id -> Paper for this batch
                # Include both original and vX-stripped IDs for robust lookup
                import re as _re
                paper_map = {}
                for p in batch:
                    paper_map[p.arxiv_id] = p
                    clean = _re.sub(r'v\d+$', '', p.arxiv_id)
                    paper_map[clean] = p

                for item in suggestions:
                    arxiv_id = str(item.get("id", "")).strip()
                    reason = str(item.get("reason", "")).strip()
                    score = int(item.get("score", 5))  # default to 5 for backward compatibility

                    if score < 4:
                        continue
                    if not arxiv_id:
                        continue
                    # Normalize: try original ID, then strip vX suffix
                    paper = paper_map.get(arxiv_id)
                    if paper is None:
                        arxiv_id_clean = _re.sub(r'v\d+$', '', arxiv_id)
                        paper = paper_map.get(arxiv_id_clean)
                    if paper is None:
                        continue
                    # Use the paper's own arxiv_id for dedup tracking
                    if paper.arxiv_id in seen_ids:
                        continue
                    kw_score = self._keyword_match_score(paper, self.keywords)
                    seen_ids.add(paper.arxiv_id)
                    total_found += 1
                    self.result.emit({"paper": paper, "reason": reason, "score": score, "kw_score": kw_score})
                    self.log.emit(
                        f"Found [{kw_score}% | {score}/5]: {paper.title[:40]}..."
                    )

            self.progress.emit(100, "Analysis complete.")
            self.log.emit(
                f"AI analysis complete — {total_found} suggestions found."
            )
            self.finished.emit(total_found)

        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit(f"ERROR: {e}\n{tb}")
            self.error.emit(str(e))

    def _build_prompt(self, batch) -> str:
        lines = []
        for p in batch:
            abstract_snip = (p.abstract or "")[:self.ABSTRACT_MAX].replace(
                "\n", " "
            )
            title = (p.title or "").replace("\n", " ")
            kw_score = self._keyword_match_score(p, self.keywords)
            lines.append(f"{p.arxiv_id} | {title} | kw:{kw_score}% | {abstract_snip}")

        papers_block = "\n".join(lines)

        keywords_str = ", ".join(self.keywords) if self.keywords else "none"

        return f"""You are a strict research paper recommender.

CONTEXT:
{self.context}

KEYWORDS EXTRACTED: {keywords_str}
These keywords were extracted from the context above.

INSTRUCTIONS:
- Only suggest papers that DIRECTLY address the context
- Reject papers that only contain matching keywords but are NOT actually relevant
- Each paper must have a clear, substantive connection to the context
- If NO papers are relevant in this batch, return [] exactly
- Do NOT suggest papers just because they contain generic AI/ML keywords

PAPERS (one per line — format: ARXIV_ID | Title | kw:XX% | Abstract excerpt):
{papers_block}

The "kw:XX%" shows the keyword match percentage for each paper (0-100%).

Return ONLY a JSON array. Each element must have exactly three keys:
  "id": the ARXIV_ID string (copy exactly as shown)
  "reason": one sentence explaining WHY this paper is relevant to the context
  "score": integer 1-5 where 5 = highly relevant, 1 = marginally relevant

Only include papers with score >= 4. Lower scores will be filtered out.
Do not include any text, explanation, or markdown outside the JSON array.

JSON array:"""


# ============================================================
# AI Search Dialog
# ============================================================

class AISearchDialog(QDialog):
    """Popup for AI-powered paper suggestions using Ollama."""

    def __init__(self, db, main_window, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = main_window
        self.worker = None
        self._results: dict = {}   # arxiv_id -> Paper

        self.setWindowTitle("🤖 AI Paper Suggestions")
        self.setMinimumSize(750, 650)
        self.setStyleSheet("QDialog { background-color: #1e1e1e; color: #d4d4d4; }")

        self._build_ui()
        self._check_ollama()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # -- Context input --
        ctx_label = QLabel("Describe your professional context:")
        ctx_label.setStyleSheet("color: #9cdcfe; font-weight: bold;")
        layout.addWidget(ctx_label)

        self.context_edit = QPlainTextEdit()
        self.context_edit.setPlaceholderText(
            "e.g. I work at a financial company that is starting to agentize "
            "the development practices of an IT department..."
        )
        self.context_edit.setFixedHeight(110)
        self.context_edit.setStyleSheet(
            "QPlainTextEdit { background-color: #252526; color: #d4d4d4; "
            "border: 1px solid #444; padding: 4px; }"
        )
        layout.addWidget(self.context_edit)

        # -- Controls row --
        ctrl_row = QHBoxLayout()

        model_label = QLabel("Model:")
        model_label.setStyleSheet("color: #888;")
        ctrl_row.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(
            "QComboBox { background-color: #252526; color: #d4d4d4; "
            "border: 1px solid #444; padding: 3px 8px; }"
        )
        self.model_combo.setMinimumWidth(160)
        ctrl_row.addWidget(self.model_combo)

        ctrl_row.addSpacing(12)

        self.suggest_btn = QPushButton("🤖 Suggest")
        self.suggest_btn.setStyleSheet(
            "QPushButton { background-color: #0e639c; color: white; "
            "padding: 6px 16px; border: none; font-weight: bold; } "
            "QPushButton:hover { background-color: #1177bb; } "
            "QPushButton:disabled { background-color: #333; color: #666; }"
        )
        self.suggest_btn.clicked.connect(self._start_suggest)
        ctrl_row.addWidget(self.suggest_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #6b2121; color: #d4d4d4; "
            "padding: 6px 16px; border: none; } "
            "QPushButton:hover { background-color: #8b2e2e; } "
            "QPushButton:disabled { background-color: #333; color: #666; }"
        )
        self.stop_btn.clicked.connect(self._stop_suggest)
        ctrl_row.addWidget(self.stop_btn)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # -- Progress bar --
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #252526; border: 1px solid #444; "
            "color: #d4d4d4; text-align: center; } "
            "QProgressBar::chunk { background-color: #0e639c; }"
        )
        layout.addWidget(self.progress_bar)

        # -- Results browser --
        self.browser = QTextBrowser()
        self.browser.setStyleSheet(
            "QTextBrowser { background-color: #1e1e1e; color: #d4d4d4; border: none; }"
        )
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._on_paper_clicked)
        layout.addWidget(self.browser)

        # -- Close button --
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "QPushButton { background-color: #333; color: #d4d4d4; "
            "padding: 6px 20px; border: 1px solid #555; }"
        )
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    # ------------------------------------------------------------------
    # Ollama availability check
    # ------------------------------------------------------------------

    def _check_ollama(self):
        from ollama_client import OllamaClient, OllamaNotAvailableError
        try:
            models = OllamaClient.list_models()
            if not models:
                self._show_message(
                    "<b style='color:#f0c674'>No models found.</b><br>"
                    "Pull a model first:<br>"
                    "<code style='color:#4ec9b0'>ollama pull qwen3:8b</code>"
                )
                self.suggest_btn.setEnabled(False)
                return
            for m in models:
                self.model_combo.addItem(m)
            # Pre-select best reasoning model: deepseek-r1:8b > qwen3:8b
            for preferred in ["deepseek-r1:8b", "qwen3:8b", "llama3:8b", "mistral:7b"]:
                idx = self.model_combo.findText(preferred)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                    break
        except OllamaNotAvailableError as e:
            self._show_message(
                f"<b style='color:#f44747'>Ollama not available</b><br><br>"
                f"{e}<br><br>"
                f"<b>Install Ollama:</b> "
                f"<a href='https://ollama.com' style='color:#569cd6'>https://ollama.com</a><br>"
                f"<b>Then pull a model:</b><br>"
                f"<code style='color:#4ec9b0'>ollama pull qwen3:8b</code>"
            )
            self.suggest_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Suggest / Stop
    # ------------------------------------------------------------------

    def _start_suggest(self):
        context = self.context_edit.toPlainText().strip()
        if not context:
            self._show_message(
                "<span style='color:#f0c674'>Please describe your context first.</span>"
            )
            return

        model = self.model_combo.currentText()
        if not model:
            return

        # Reset state
        self._results.clear()
        self.browser.setHtml(
            "<p style='color:#888'>Analysing papers... results will appear here as they are found.</p>"
        )
        self._result_html_parts = []
        self._found_count = 0

        self.suggest_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = OllamaWorker(context=context, model=model, db=self.db)
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_result)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.log.connect(lambda msg: self.main_window.log(msg))
        self.worker.start()

    def _stop_suggest(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.stop_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Worker signal handlers
    # ------------------------------------------------------------------

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{msg} ({pct}%)")

    def _on_result(self, item: dict):
        paper = item["paper"]
        reason = item["reason"]
        llm_score = item.get("score", 5)
        kw_score = item.get("kw_score", 0)

        self._results[paper.arxiv_id] = paper
        self._found_count += 1

        # Color based on LLM score
        if llm_score >= 5:
            score_color = "#4ec9b0"  # green/teal for highly relevant
        elif llm_score >= 4:
            score_color = "#dcdcaa"  # yellow for relevant
        else:
            score_color = "#888888"  # gray fallback

        # Keyword score color
        if kw_score >= 80:
            kw_color = "#4ec9b0"
        elif kw_score >= 50:
            kw_color = "#dcdcaa"
        else:
            kw_color = "#888888"

        date = paper.published[:10] if paper.published else ""
        cats = paper.categories[:40] if paper.categories else ""

        block = (
            f'<div style="border-bottom:1px solid #333; padding:10px 0;">'
            f'<a href="{paper.arxiv_id}" style="color:#569cd6; font-weight:bold; '
            f'font-size:13px; text-decoration:none;">'
            f'{self._found_count}. {paper.title}</a>'
            f' <span style="color:{kw_color}; font-size:11px;">'
            f'[{kw_score}%]</span>'
            f' <span style="color:{score_color}; font-size:11px; font-weight:bold;">'
            f'[{llm_score}/5]</span><br>'
            f'<span style="color:#888; font-size:11px">'
            f'{paper.source} &nbsp;·&nbsp; {date} &nbsp;·&nbsp; {cats}</span><br>'
            f'<span style="color:#4ec9b0; font-size:12px">&#9654; {reason}</span>'
            f'</div>'
        )
        self._result_html_parts.append(block)
        self._refresh_browser()

    def _on_finished(self, total: int):
        self.suggest_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if total == 0:
            self._show_message(
                "<span style='color:#f0c674'>No relevant papers found.<br>"
                "Try rephrasing your context or use a different model.</span>"
            )
        else:
            # Prepend summary header to results
            header = (
                f"<h3 style='color:#569cd6'>"
                f"Found {total} relevant paper{'s' if total != 1 else ''}</h3>"
                f"<p style='color:#888; font-size:11px'>"
                f"Click a paper title to open it in the main window.</p>"
            )
            self._result_html_parts.insert(0, header)
            self._refresh_browser()

    def _on_error(self, msg: str):
        self.suggest_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self._show_message(
            f"<b style='color:#f44747'>Error:</b><br>{msg}"
        )

    # ------------------------------------------------------------------
    # Paper click — open in main window
    # ------------------------------------------------------------------

    def _on_paper_clicked(self, url):
        from PySide6.QtCore import QUrl
        arxiv_id = url.toString() if hasattr(url, 'toString') else str(url)
        paper = self._results.get(arxiv_id)
        if paper is None:
            return

        # Put the title in the search box and trigger search
        search_title = paper.title[:80]
        self.main_window.search_box.setText(search_title)
        self.main_window.on_search()

        # Select the first matching item in the list
        paper_list = self.main_window.paper_list
        if paper_list.count() > 0:
            first_item = paper_list.item(0)
            if first_item:
                paper_list.setCurrentItem(first_item)
                self.main_window.on_paper_selected(first_item)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_message(self, html: str):
        self.browser.setHtml(
            f"<div style='font-family:Consolas,monospace; "
            f"color:#d4d4d4; padding:16px;'>{html}</div>"
        )

    def _refresh_browser(self):
        full_html = (
            "<html><body style='font-family:Consolas,monospace; "
            "background:#1e1e1e; color:#d4d4d4; padding:8px;'>"
            + "".join(self._result_html_parts)
            + "</body></html>"
        )
        self.browser.setHtml(full_html)

    def closeEvent(self, event):
        """Stop worker if running when dialog is closed."""
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(2000)
        super().closeEvent(event)


class AutoRefreshWorker(QThread):
    def __init__(self, main_window, interval_hours=1):
        super().__init__()
        self.main_window = main_window
        self.interval_seconds = interval_hours * 3600
        self.running = True
    
    def run(self):
        import time
        while self.running:
            time.sleep(self.interval_seconds)
            if self.running:
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self.main_window,
                    'start_fetch',
                    Qt.QueuedConnection
                )
    
    def stop(self):
        self.running = False


class FetchWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, days_back: int = 7, start_date: str = None, end_date: str = None):
        super().__init__()
        self.days_back = days_back
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        import traceback
        from datetime import datetime
        
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log.emit(f"Starting fetch from arXiv...")
            
            from fetcher import fetch_all_recent_papers
            
            def progress_callback(pct, message):
                self.progress.emit(pct, message)
            
            def log_callback(message):
                self.log.emit(message)
            
            all_papers = []
            
            self.progress.emit(0, "Fetching from arXiv...")
            self.log.emit("Fetching from arXiv...")
            
            papers_arxiv = fetch_all_recent_papers(self.days_back, progress_callback=progress_callback, start_date=self.start_date, end_date=self.end_date, log_callback=log_callback)
            all_papers.extend(papers_arxiv)
            
            self.progress.emit(50, "Fetching from Hugging Face...")
            self.log.emit("Fetching from Hugging Face...")
            
            try:
                from huggingface_fetcher import fetch_all_papers_huggingface
                papers_hf = fetch_all_papers_huggingface(progress_callback=progress_callback, start_date=self.start_date, end_date=self.end_date, log_callback=log_callback)
                all_papers.extend(papers_hf)
            except Exception as hf_err:
                self.log.emit(f"WARNING: Hugging Face unavailable: {hf_err}")
            
            db = Database()
            existing_count = db.get_paper_count()
            db.add_papers(all_papers)
            new_count = db.get_paper_count()
            
            self.log.emit(f"Fetch complete! {new_count} new papers added.")
            self.finished.emit(new_count - existing_count)
        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit(f"ERROR: {e}\n{tb}")
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.fetch_worker = None
        self.papers = []
        self.is_fetching = False
        
        self.init_ui()
        self.load_papers()
        self.update_status()

    def init_ui(self):
        self.setWindowTitle("AI Paper Tracker")
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        toolbar = self.create_toolbar()
        main_layout.addLayout(toolbar)
        
        splitter = QSplitter(Qt.Horizontal)
        
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)
        
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)
        
        splitter.setSizes([500, 900])
        
        self.log_panel = QPlainTextEdit()
        self.log_panel.setMaximumHeight(150)
        self.log_panel.setReadOnly(True)
        self.log_panel.setPlaceholderText("Logs will appear here...")
        
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.log_panel)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        self.log("Application started")

    def create_toolbar(self):
        toolbar = QHBoxLayout()
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search papers...")
        self.search_box.textChanged.connect(self.on_search)
        toolbar.addWidget(QLabel("Search:"))
        toolbar.addWidget(self.search_box)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", None)
        for code, name in CATEGORIES.items():
            self.category_combo.addItem(f"{name} ({code})", code)
        self.category_combo.currentIndexChanged.connect(self.on_search)
        toolbar.addWidget(QLabel("Category:"))
        toolbar.addWidget(self.category_combo)
        
        self.source_combo = QComboBox()
        self.source_combo.addItem("All Sources", None)
        self.source_combo.addItem("arXiv", "arXiv")
        self.source_combo.addItem("Hugging Face", "Hugging Face")
        self.source_combo.currentIndexChanged.connect(self.on_search)
        toolbar.addWidget(QLabel("Source:"))
        toolbar.addWidget(self.source_combo)
        
        self.meta_checkbox = QCheckBox("Meta-analyses only")
        self.meta_checkbox.stateChanged.connect(self.on_search)
        toolbar.addWidget(self.meta_checkbox)
        
        self.favorites_checkbox = QCheckBox("⭐ Favorites only")
        self.favorites_checkbox.stateChanged.connect(self.on_search)
        toolbar.addWidget(self.favorites_checkbox)
        
        toolbar.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.start_fetch)
        toolbar.addWidget(self.refresh_btn)
        
        self.fetch_month_btn = QPushButton("📅 Fetch by month")
        self.fetch_month_btn.clicked.connect(self.show_fetch_month_dialog)
        toolbar.addWidget(self.fetch_month_btn)
        
        self.stats_btn = QPushButton("📊 Statistics")
        self.stats_btn.clicked.connect(self.show_statistics)
        toolbar.addWidget(self.stats_btn)

        self.ai_suggest_btn = QPushButton("🤖 AI Suggest")
        self.ai_suggest_btn.clicked.connect(self.show_ai_search)
        toolbar.addWidget(self.ai_suggest_btn)
        
        self.auto_refresh_checkbox = QCheckBox("Auto-refresh hourly")
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        toolbar.addWidget(self.auto_refresh_checkbox)
        
        return toolbar

    def create_left_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.on_paper_selected)
        layout.addWidget(self.paper_list)
        
        return widget

    def create_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.fav_btn = QPushButton("☆ Add to Favorites")
        self.fav_btn.clicked.connect(self.toggle_favorite)
        layout.addWidget(self.fav_btn)
        
        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(True)
        layout.addWidget(self.detail_browser)
        
        return widget

    def load_papers(self):
        self.papers = self.db.get_all_papers()
        self.populate_list(self.papers)

    def populate_list(self, papers: list):
        self.paper_list.clear()
        
        for paper in papers:
            title = paper.title
            if paper.is_meta_analysis:
                title = f"📊 {title}"
            if paper.is_favorite:
                title = f"⭐ {title}"
            
            date = paper.published[:10] if hasattr(paper, 'published') else ''
            display_text = f"{date} - {title[:80]}{'...' if len(title) > 80 else ''}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, paper)
            self.paper_list.addItem(item)

    def on_paper_selected(self, item: QListWidgetItem):
        paper: Paper = item.data(Qt.UserRole)
        self.current_paper = paper
        
        if paper.is_favorite:
            self.fav_btn.setText("⭐ Remove from Favorites")
        else:
            self.fav_btn.setText("☆ Add to Favorites")
        
        html = f"""
        <h2>{paper.title}</h2>
        <p><b>Authors:</b> {paper.authors}</p>
        <p><b>Published:</b> {paper.published}</p>
        <p><b>Categories:</b> {paper.categories}</p>
        <p><b>Source:</b> {paper.source}</p>
        <p><b>arXiv ID:</b> <a href="https://arxiv.org/abs/{paper.arxiv_id}">{paper.arxiv_id}</a></p>
        <p><b>PDF:</b> <a href="{paper.pdf_url}">Download PDF</a></p>
        """
        
        if paper.is_meta_analysis:
            html += '<p><b style="color: #ff6600;">📊 Meta-Analysis / Survey</b></p>'
        
        html += f"""
        <hr>
        <h3>Abstract</h3>
        <p>{paper.abstract}</p>
        """
        
        self.detail_browser.setHtml(html)

    def on_search(self):
        query = self.search_box.text()
        category = self.category_combo.currentData()
        source = self.source_combo.currentData()
        meta_only = self.meta_checkbox.isChecked()
        favorites_only = self.favorites_checkbox.isChecked()
        
        if query or category or source or meta_only or favorites_only:
            self.papers = self.db.search_papers(query, category, meta_only, source, favorites_only)
        else:
            self.papers = self.db.get_all_papers()
        
        self.populate_list(self.papers)

    def toggle_favorite(self):
        if hasattr(self, 'current_paper') and self.current_paper:
            arxiv_id = self.current_paper.arxiv_id
            new_state = self.db.toggle_favorite(arxiv_id)
            self.current_paper.is_favorite = new_state
            
            if new_state:
                self.fav_btn.setText("⭐ Remove from Favorites")
                self.log(f"Added to favorites: {arxiv_id}")
            else:
                self.fav_btn.setText("☆ Add to Favorites")
                self.log(f"Removed from favorites: {arxiv_id}")
            
            self.populate_list(self.papers)

    def start_fetch(self):
        if self.is_fetching:
            return
        
        try:
            self.is_fetching = True
            self.refresh_btn.setEnabled(False)
            self.fetch_month_btn.setEnabled(False)
            self.refresh_btn.setText("Fetching...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_bar.showMessage("Fetching papers from arXiv...")
            
            most_recent = self.db.get_most_recent_date()
            self.log(f"Refresh: most_recent date = {most_recent}")
            
            self.fetch_worker = FetchWorker(days_back=7, start_date=most_recent)
            self.fetch_worker.progress.connect(self.on_fetch_progress)
            self.fetch_worker.finished.connect(self.on_fetch_finished)
            self.fetch_worker.error.connect(self.on_fetch_error)
            self.fetch_worker.log.connect(self.log)
            self.fetch_worker.start()
        except Exception as e:
            self.is_fetching = False
            self.refresh_btn.setEnabled(True)
            self.fetch_month_btn.setEnabled(True)
            self.refresh_btn.setText("🔄 Refresh")
            self.progress_bar.setVisible(False)
            self.log(f"ERROR starting fetch: {e}")
            self.status_bar.showMessage(f"Error: {e}")

    def show_fetch_month_dialog(self):
        from datetime import datetime
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Fetch by Month")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        month_label = QLabel("Select Month:")
        layout.addWidget(month_label)
        
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        month_combo = QComboBox()
        month_combo.addItems(months)
        
        current_month = datetime.now().month - 1
        month_combo.setCurrentIndex(current_month)
        layout.addWidget(month_combo)
        
        year_label = QLabel("Select Year:")
        layout.addWidget(year_label)
        
        year_spin = QSpinBox()
        year_spin.setMinimum(2021)
        year_spin.setMaximum(2027)
        year_spin.setValue(datetime.now().year)
        layout.addWidget(year_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec():
            selected_month = month_combo.currentIndex() + 1
            selected_year = year_spin.value()
            self.fetch_by_month(selected_year, selected_month)

    def fetch_by_month(self, year: int, month: int):
        if self.is_fetching:
            return
        
        import calendar
        from datetime import datetime
        
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        
        month_name = calendar.month_name[month]
        
        self.is_fetching = True
        self.refresh_btn.setEnabled(False)
        self.fetch_month_btn.setEnabled(False)
        self.fetch_month_btn.setText(f"Fetching {month_name} {year}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage(f"Fetching papers from {month_name} {year}...")
        
        self.fetch_worker = FetchWorker(start_date=start_date, end_date=end_date)
        self.fetch_worker.progress.connect(self.on_fetch_progress)
        self.fetch_worker.finished.connect(self.on_fetch_month_finished)
        self.fetch_worker.error.connect(self.on_fetch_error)
        self.fetch_worker.log.connect(self.log)
        self.fetch_worker.start()

    def on_fetch_month_finished(self, new_count: int):
        self.is_fetching = False
        self.fetch_month_btn.setEnabled(True)
        self.fetch_month_btn.setText("📅 Fetch by month")
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.load_papers()
        self.update_status()
        
        count = self.db.get_paper_count()
        self.log(f"Fetch complete! {new_count} new papers added. Total: {count}")
        self.status_bar.showMessage(f"Fetch complete! {new_count} new papers added. Total: {count}")

    def on_fetch_progress(self, pct: int, message: str):
        self.progress_bar.setValue(pct)
        self.status_bar.showMessage(message)

    def on_fetch_finished(self, new_count: int):
        self.is_fetching = False
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Refresh")
        self.fetch_month_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.load_papers()
        self.update_status()
        
        count = self.db.get_paper_count()
        self.log(f"Fetch complete! {new_count} new papers added. Total: {count}")
        self.status_bar.showMessage(f"Fetch complete! {new_count} new papers added. Total: {count}")

    def on_fetch_error(self, error: str):
        self.is_fetching = False
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Refresh")
        self.fetch_month_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.log(f"ERROR: {error}")
        self.status_bar.showMessage(f"Error: {error}")

    def toggle_auto_refresh(self, state: int):
        from datetime import datetime
        is_checked = bool(state)
        
        self.log(f"Auto-refresh toggle: state={state}, is_checked={is_checked}")
        
        if is_checked:
            self.auto_refresh_worker = AutoRefreshWorker(
                main_window=self,
                interval_hours=1
            )
            self.auto_refresh_worker.start()
            self.log(f"Auto-refresh enabled - will run every hour")
            self.status_bar.showMessage("Auto-refresh enabled (every hour)")
        else:
            if hasattr(self, 'auto_refresh_worker'):
                self.auto_refresh_worker.stop()
                self.auto_refresh_worker = None
            self.status_bar.showMessage("Auto-refresh disabled")

    def show_statistics(self):
        dialog = StatisticsDialog(self.db, parent=self)
        dialog.exec()

    def show_ai_search(self):
        if not hasattr(self, '_ai_dialog') or not self._ai_dialog.isVisible():
            self._ai_dialog = AISearchDialog(self.db, main_window=self, parent=self)
        self._ai_dialog.show()
        self._ai_dialog.raise_()
        self._ai_dialog.activateWindow()

    def log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        if hasattr(self, 'log_panel'):
            self.log_panel.appendPlainText(formatted)

    def update_status(self):
        count = self.db.get_paper_count()
        last_fetch = self.db.get_last_fetch()
        
        if count == 0:
            self.status_bar.showMessage("Welcome! Click 'Refresh' to fetch papers from arXiv.")
        else:
            status = f"Total papers: {count}"
            if last_fetch:
                status += f" | Last fetch: {last_fetch[:16]}"
            self.status_bar.showMessage(status)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

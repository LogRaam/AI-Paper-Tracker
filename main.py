import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QPushButton,
    QComboBox, QLabel, QProgressBar, QGroupBox, QCheckBox, QSplitter,
    QStatusBar, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction

from models import Paper, CATEGORIES, CATEGORY_CODES
from database import Database


class AutoRefreshWorker(QThread):
    def __init__(self, refresh_callback, interval_hours=1):
        super().__init__()
        self.refresh_callback = refresh_callback
        self.interval_seconds = interval_hours * 3600
        self.running = True
    
    def run(self):
        import time
        while self.running:
            time.sleep(self.interval_seconds)
            if self.running:
                self.refresh_callback()
    
    def stop(self):
        self.running = False


class FetchWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, days_back: int = 7, start_date: str = None):
        super().__init__()
        self.days_back = days_back
        self.start_date = start_date

    def run(self):
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            from fetcher import fetch_all_recent_papers
            
            def progress_callback(pct, message):
                self.progress.emit(pct, message)
            
            all_papers = []
            
            self.progress.emit(0, "Fetching from arXiv...")
            print(f"[{current_time}] Fetching from arXiv...", flush=True)
            papers_arxiv = fetch_all_recent_papers(self.days_back, progress_callback=progress_callback, start_date=self.start_date)
            all_papers.extend(papers_arxiv)
            
            self.progress.emit(50, "Fetching from Hugging Face...")
            print(f"[{current_time}] Fetching from Hugging Face...", flush=True)
            try:
                from huggingface_fetcher import fetch_all_papers_huggingface
                papers_hf = fetch_all_papers_huggingface(progress_callback=progress_callback, start_date=self.start_date)
                all_papers.extend(papers_hf)
            except Exception as hf_err:
                print(f"[{current_time}] WARNING: Hugging Face unavailable: {hf_err}", flush=True)
            
            db = Database()
            existing_count = db.get_paper_count()
            db.add_papers(all_papers)
            new_count = db.get_paper_count()
            
            self.finished.emit(new_count - existing_count)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.fetch_worker = None
        self.papers = []
        
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
        main_layout.addWidget(splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

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
        
        toolbar.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.start_fetch)
        toolbar.addWidget(self.refresh_btn)
        
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
        
        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(True)
        layout.addWidget(self.detail_browser)
        
        return widget

    def load_papers(self):
        self.papers = self.db.get_all_papers(limit=1000)
        self.populate_list(self.papers)

    def populate_list(self, papers: list):
        self.paper_list.clear()
        
        for paper in papers:
            title = paper.title
            if paper.is_meta_analysis:
                title = f"📊 {title}"
            
            date = paper.published[:10] if hasattr(paper, 'published') else ''
            display_text = f"{date} - {title[:80]}{'...' if len(title) > 80 else ''}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, paper)
            self.paper_list.addItem(item)

    def on_paper_selected(self, item: QListWidgetItem):
        paper: Paper = item.data(Qt.UserRole)
        
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
        
        if query or category or source or meta_only:
            self.papers = self.db.search_papers(query, category, meta_only, source)
        else:
            self.papers = self.db.get_all_papers(limit=1000)
        
        self.populate_list(self.papers)

    def start_fetch(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Fetching...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Fetching papers from arXiv...")
        
        most_recent = self.db.get_most_recent_date()
        
        self.fetch_worker = FetchWorker(days_back=7, start_date=most_recent)
        self.fetch_worker.progress.connect(self.on_fetch_progress)
        self.fetch_worker.finished.connect(self.on_fetch_finished)
        self.fetch_worker.error.connect(self.on_fetch_error)
        self.fetch_worker.start()

    def on_fetch_progress(self, pct: int, message: str):
        self.progress_bar.setValue(pct)
        self.status_bar.showMessage(message)

    def on_fetch_finished(self, new_count: int):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Refresh")
        self.progress_bar.setVisible(False)
        
        self.load_papers()
        self.update_status()
        
        msg = f"Fetch complete! {new_count} new papers added."
        print(msg, flush=True)
        self.status_bar.showMessage(msg)

    def on_fetch_error(self, error: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Refresh")
        self.progress_bar.setVisible(False)
        
        print(f"ERROR: {error}", flush=True)
        self.status_bar.showMessage(f"Error: {error}")

    def toggle_auto_refresh(self, state: int):
        from datetime import datetime
        if state == Qt.Checked:
            self.auto_refresh_worker = AutoRefreshWorker(
                refresh_callback=self.start_fetch,
                interval_hours=1
            )
            self.auto_refresh_worker.start()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time}] Auto-refresh enabled - will run every hour", flush=True)
            self.status_bar.showMessage("Auto-refresh enabled (every hour)")
        else:
            if hasattr(self, 'auto_refresh_worker'):
                self.auto_refresh_worker.stop()
                self.auto_refresh_worker = None
            self.status_bar.showMessage("Auto-refresh disabled")

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

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

from models import Database, Paper, CATEGORIES, CATEGORY_CODES


class FetchWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, days_back: int = 7):
        super().__init__()
        self.days_back = days_back

    def run(self):
        try:
            from fetcher import fetch_all_recent_papers
            
            def progress_callback(pct, message):
                self.progress.emit(pct, message)
            
            papers = fetch_all_recent_papers(self.days_back, progress_callback=progress_callback)
            
            db = Database()
            existing_count = db.get_paper_count()
            db.add_papers(papers)
            new_count = db.get_paper_count()
            
            self.finished.emit(new_count - existing_count)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.fetch_worker = None
        
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
        meta_only = self.meta_checkbox.isChecked()
        
        if query or category or meta_only:
            self.papers = self.db.search_papers(query, category, meta_only)
        else:
            self.papers = self.db.get_all_papers(limit=1000)
        
        self.populate_list(self.papers)

    def start_fetch(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Fetching...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Fetching papers from arXiv...")
        
        self.fetch_worker = FetchWorker(days_back=7)
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
        
        self.status_bar.showMessage(f"Fetch complete! {new_count} new papers added.")

    def on_fetch_error(self, error: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Refresh")
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Error: {error}")

    def toggle_auto_refresh(self, state: int):
        if state == Qt.Checked:
            self.auto_timer = QTimer()
            self.auto_timer.timeout.connect(self.start_fetch)
            self.auto_timer.start(3600000)
            self.status_bar.showMessage("Auto-refresh enabled (every hour)")
        else:
            if hasattr(self, 'auto_timer'):
                self.auto_timer.stop()
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

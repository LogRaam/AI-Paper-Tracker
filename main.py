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
        self.papers = self.db.get_all_papers(limit=1000)
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
            self.papers = self.db.get_all_papers(limit=1000)
        
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
        
        self.is_fetching = True
        self.refresh_btn.setEnabled(False)
        self.fetch_month_btn.setEnabled(False)
        self.refresh_btn.setText("Fetching...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Fetching papers from arXiv...")
        
        most_recent = self.db.get_most_recent_date()
        
        self.fetch_worker = FetchWorker(days_back=7, start_date=most_recent)
        self.fetch_worker.progress.connect(self.on_fetch_progress)
        self.fetch_worker.finished.connect(self.on_fetch_finished)
        self.fetch_worker.error.connect(self.on_fetch_error)
        self.fetch_worker.log.connect(self.log)
        self.fetch_worker.start()

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

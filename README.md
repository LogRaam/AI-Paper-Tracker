# AI Paper Tracker

Desktop application for tracking AI research papers from arXiv and Papers with Code. Stay up-to-date with the latest developments in artificial intelligence, machine learning, NLP, computer vision, and more.

## Features

- **Automatic Synchronization**: Fetches new papers hourly or on-demand from arXiv and Papers with Code
- **Multi-Source Support**: 
  - arXiv - Preprints in Machine Learning, NLP, Computer Vision, etc.
  - Papers with Code - Papers with available implementation code
- **Multi-Category Tracking**: Monitors 7 AI-related categories
  - Machine Learning (cs.LG)
  - Natural Language Processing (cs.CL)
  - Computer Vision (cs.CV)
  - Neural & Evolutionary Computing (cs.NE)
  - Artificial Intelligence (cs.AI)
  - Robotics (cs.RO)
  - Statistical Machine Learning (stat.ML)
- **Meta-Analysis Detection**: Automatically identifies and marks surveys, systematic reviews, and meta-analyses
- **Powerful Search & Filters**: 
  - Filter by keywords in title or abstract
  - Filter by category (AI subfield)
  - Filter by source (arXiv / Papers with Code)
  - Filter to show only meta-analyses
- **Direct Access**: One-click links to PDF and arXiv pages
- **Local Storage**: SQLite database - your data stays on your machine

## Screenshots

The application features:
- Left panel: Scrollable list of papers with dates and titles
- Right panel: Detailed view with abstract, authors, and links
- Toolbar: Search, category filter, source filter, meta-analysis toggle, and refresh button
- Progress bar: Shows fetching progress
- Status bar: Displays current status and paper count

## Installation

```bash
cd AI-Paper-Tracker
pip install -r requirements.txt
```

## Usage

### Quick Start

```bash
python main.py
```

Or double-click `run.bat` on Windows.

### First Run

1. Launch the application
2. Click **"🔄 Refresh"** to fetch papers from arXiv and Papers with Code
3. Wait for the initial sync (5-10 minutes for ~500-1000 papers)
4. Enable **"Auto-refresh hourly"** for automatic updates

### Features Guide

| Feature | How to Use |
|---------|------------|
| **Search** | Type in the search box to filter by title/abstract |
| **Categories** | Select from dropdown to filter by AI subfield |
| **Sources** | Select to show papers from arXiv, Papers with Code, or All |
| **Meta-analyses** | Check the box to see only surveys/reviews |
| **Paper Details** | Click any paper to see abstract and links |
| **PDF Download** | Click the PDF link to download |

### Smart Fetch

- **First run**: Fetches papers from the last 7 days
- **Subsequent runs**: Fetches only new papers since the last fetch (based on the most recent date in database)
- This significantly reduces fetch time on subsequent runs

## Project Structure

```
AI-Paper-Tracker/
├── main.py                    # PySide6 GUI application
├── fetcher.py                # arXiv API integration
├── paperswithcode_fetcher.py # Papers with Code API integration
├── database.py               # SQLite database management
├── models.py                 # Data models (Paper, Category)
├── requirements.txt          # Python dependencies
├── run.bat                   # Windows launcher script
├── README.md                 # This file
└── papers.db                 # Local database (created on first run)
```

## Requirements

- Python 3.8+
- arxiv - arXiv API wrapper
- PySide6 - Cross-platform GUI framework (LGPL licensed)
- paperswithcode-client - Papers with Code API (for papers with code)
- tea-client==0.0.8 - Required for paperswithcode-client

## How It Works

1. **Data Sources**: 
   - Uses arXiv API to fetch papers from 7 AI-related categories
   - Uses Papers with Code API to fetch papers with available code
2. **Smart Fetching**: 
   - First run: fetches last 7 days
   - Subsequent runs: fetches only new papers since last fetch
3. **Deduplication**: Uses arXiv ID to avoid duplicates
4. **Meta-Analysis Detection**: Scans titles and abstracts for keywords like "meta-analysis", "systematic review", "survey", etc.
5. **Storage**: All data stored locally in SQLite (papers.db)
6. **Auto-refresh**: Uses QTimer for hourly updates

## Filtering Examples

- **Show only arXiv papers**: Select "arXiv" in Source dropdown
- **Show only papers with code**: Select "Papers with Code" in Source dropdown
- **Show all ML surveys**: Select "MachineLearning" category + check "Meta-analyses only"
- **Find papers about transformers**: Type "transformer" in search box

## For Developers

### Running in Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

### Adding New Categories

Edit `models.py` to add or remove categories:

```python
CATEGORIES = {
    'cs.LG': 'MachineLearning',
    'cs.CL': 'NLP',
    # Add more categories here...
}
```

### Architecture

- **models.py**: Contains Paper class and Category definitions
- **database.py**: SQLite operations (CRUD for papers)
- **fetcher.py**: arXiv API integration
- **paperswithcode_fetcher.py**: Papers with Code API integration
- **main.py**: PySide6 GUI application

## License

MIT License - Feel free to use and modify for personal or commercial projects.

## Author

Developed with Python and PySide6

# AI Paper Tracker

Desktop application for tracking AI research papers from arXiv. Stay up-to-date with the latest developments in artificial intelligence, machine learning, NLP, computer vision, and more.

## Features

- **Automatic Synchronization**: Fetches new papers hourly or on-demand from arXiv
- **Multi-Category Tracking**: Monitors 7 AI-related categories
  - Machine Learning (cs.LG)
  - Natural Language Processing (cs.CL)
  - Computer Vision (cs.CV)
  - Neural & Evolutionary Computing (cs.NE)
  - Artificial Intelligence (cs.AI)
  - Robotics (cs.RO)
  - Statistical Machine Learning (stat.ML)
- **Meta-Analysis Detection**: Automatically identifies and marks surveys, systematic reviews, and meta-analyses
- **Powerful Search**: Filter papers by keywords in title or abstract
- **Category Filtering**: Browse papers by specific AI subfield
- **Direct Access**: One-click links to PDF and arXiv pages
- **Local Storage**: SQLite database - your data stays on your machine

## Screenshots

The application features:
- Left panel: Scrollable list of papers with dates and titles
- Right panel: Detailed view with abstract, authors, and links
- Toolbar: Search, category filter, meta-analysis toggle, and refresh button

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
2. Click **"🔄 Refresh"** to fetch papers from arXiv
3. Wait for the initial sync (5-10 minutes for ~500-1000 papers)
4. Enable **"Auto-refresh hourly"** for automatic updates

### Features Guide

| Feature | How to Use |
|---------|------------|
| **Search** | Type in the search box to filter by title/abstract |
| **Categories** | Select from dropdown to filter by AI subfield |
| **Meta-analyses** | Check the box to see only surveys/reviews |
| **Paper Details** | Click any paper to see abstract and links |
| **PDF Download** | Click the PDF link to download |

## Project Structure

```
AI-Paper-Tracker/
├── main.py           # PySide6 GUI application
├── fetcher.py        # arXiv API integration
├── database.py       # SQLite database management
├── models.py         # Data models (Paper, Category)
├── requirements.txt  # Python dependencies
├── run.bat          # Windows launcher script
├── README.md        # This file
└── papers.db       # Local database (created on first run)
```

## Requirements

- Python 3.8+
- arxiv - arXiv API wrapper
- PySide6 - Cross-platform GUI framework (LGPL licensed)
- APScheduler - Task scheduling

## How It Works

1. **Data Source**: Uses the public arXiv API to fetch papers from AI-related categories
2. **Deduplication**: Only adds new papers not already in the database
3. **Meta-Analysis Detection**: Scans titles and abstracts for keywords like "meta-analysis", "systematic review", "survey", etc.
4. **Storage**: All data stored locally in SQLite (papers.db)
5. **Updates**: Configurable auto-refresh (default: hourly)

## For Developers

### Running in Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

### Modifying Categories

Edit `models.py` to add or remove categories:

```python
CATEGORIES = {
    'cs.LG': 'MachineLearning',
    'cs.CL': 'NLP',
    # Add more categories here...
}
```

## License

MIT License - Feel free to use and modify for personal or commercial projects.

## Author

Developed with ❤️ using Python and PySide6

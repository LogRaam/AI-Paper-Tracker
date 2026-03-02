import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Paper:
    """Represents a research paper from arXiv or Hugging Face."""

    def __init__(
        self,
        arxiv_id: str,
        title: str,
        abstract: str,
        authors: str,
        published: str,
        updated: str,
        categories: str,
        pdf_url: str,
        is_meta_analysis: bool = False,
        source: str = "arXiv",
        is_favorite: bool = False
    ) -> None:
        self.arxiv_id: str = arxiv_id
        self.title: str = title
        self.abstract: str = abstract
        self.authors: str = authors
        self.published: str = published
        self.updated: str = updated
        self.categories: str = categories
        self.pdf_url: str = pdf_url
        self.is_meta_analysis: bool = is_meta_analysis
        self.source: str = source
        self.is_favorite: bool = is_favorite

    def to_dict(self) -> Dict[str, Any]:
        return {
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': self.authors,
            'published': self.published,
            'updated': self.updated,
            'categories': self.categories,
            'pdf_url': self.pdf_url,
            'is_meta_analysis': int(self.is_meta_analysis),
            'source': self.source,
            'is_favorite': int(self.is_favorite)
        }


CATEGORIES = {
    'cs.LG': 'MachineLearning',
    'cs.CL': 'NLP',
    'cs.CV': 'ComputerVision',
    'cs.NE': 'NeuralEvolution',
    'cs.AI': 'ArtificialIntelligence',
    'cs.RO': 'Robotics',
    'stat.ML': 'StatisticalML',
    'cs.CY': 'ComputersAndSociety',
    'cs.SE': 'SoftwareEngineering'
}

CATEGORY_CODES = list(CATEGORIES.keys())


class Database:
    def __init__(self, db_path: str = 'papers.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,
                published TEXT,
                updated TEXT,
                categories TEXT,
                pdf_url TEXT,
                is_meta_analysis INTEGER DEFAULT 0,
                source TEXT DEFAULT 'arXiv',
                is_favorite INTEGER DEFAULT 0,
                fetched_at TEXT
            )
        ''')
        try:
            cursor.execute('ALTER TABLE papers ADD COLUMN source TEXT DEFAULT "arXiv"')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE papers ADD COLUMN is_favorite INTEGER DEFAULT 0')
        except:
            pass
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_published ON papers(published)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories ON papers(categories)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON papers(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorite ON papers(is_favorite)')
        conn.commit()
        conn.close()

    def paper_exists(self, arxiv_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM papers WHERE arxiv_id = ?', (arxiv_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def add_paper(self, paper: Paper):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        data = paper.to_dict()
        data['fetched_at'] = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR IGNORE INTO papers 
            (arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['arxiv_id'], data['title'], data['abstract'], data['authors'],
            data['published'], data['updated'], data['categories'], data['pdf_url'],
            data['is_meta_analysis'], data['source'], data['is_favorite'], data['fetched_at']
        ))
        conn.commit()
        conn.close()

    def add_papers(self, papers: List):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        for paper in papers:
            data = paper.to_dict()
            data['fetched_at'] = now
            cursor.execute('''
                INSERT OR IGNORE INTO papers 
                (arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['arxiv_id'], data['title'], data['abstract'], data['authors'],
                data['published'], data['updated'], data['categories'], data['pdf_url'],
                data['is_meta_analysis'], data['source'], data['is_favorite'], now
            ))
        conn.commit()
        conn.close()

    def get_all_papers(self) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite
            FROM papers 
            ORDER BY published DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def search_papers(self, query: str = "", category: Optional[str] = None, meta_only: bool = False, source: Optional[str] = None, favorites_only: bool = False) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = 'SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite FROM papers WHERE 1=1'
        params = []
        
        if query:
            sql += ' AND (title LIKE ? OR abstract LIKE ?)'
            params.extend([f'%{query}%', f'%{query}%'])
        
        if category and category != 'All':
            sql += ' AND categories LIKE ?'
            params.append(f'%{category}%')
        
        if source and source != 'All':
            sql += ' AND source = ?'
            params.append(source)
        
        if meta_only:
            sql += ' AND is_meta_analysis = 1'
        
        if favorites_only:
            sql += ' AND is_favorite = 1'
        
        sql += ' ORDER BY published DESC'
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_papers_by_category(self, category: str) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite
            FROM papers 
            WHERE categories LIKE ?
            ORDER BY published DESC
        ''', (f'%{category}%',))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_meta_analyses(self) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite
            FROM papers 
            WHERE is_meta_analysis = 1
            ORDER BY published DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_paper_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM papers')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_last_fetch(self) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT fetched_at FROM papers ORDER BY fetched_at DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_most_recent_date(self) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(updated) FROM papers')
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else None

    def toggle_favorite(self, arxiv_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT is_favorite FROM papers WHERE arxiv_id = ?', (arxiv_id,))
        row = cursor.fetchone()
        if row:
            new_value = 1 if row[0] == 0 else 0
            cursor.execute('UPDATE papers SET is_favorite = ? WHERE arxiv_id = ?', (new_value, arxiv_id))
            conn.commit()
            conn.close()
            return bool(new_value)
        conn.close()
        return False

    def _row_to_paper(self, row) -> 'Paper':
        return Paper(
            arxiv_id=row[0],
            title=row[1],
            abstract=row[2],
            authors=row[3],
            published=row[4],
            updated=row[5],
            categories=row[6],
            pdf_url=row[7],
            is_meta_analysis=bool(row[8]) if len(row) > 8 else False,
            source=row[9] if len(row) > 9 else 'arXiv',
            is_favorite=bool(row[10]) if len(row) > 10 else False
        )

    # ------------------------------------------------------------------
    # Statistics queries
    # ------------------------------------------------------------------

    def get_stats_overview(self) -> Dict[str, int]:
        """Return total, per-source counts, favorites, and meta-analyses."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM papers')
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM papers WHERE source = 'arXiv'")
        arxiv_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM papers WHERE source = 'Hugging Face'")
        hf_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM papers WHERE is_favorite = 1')
        fav_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM papers WHERE is_meta_analysis = 1')
        meta_count = cursor.fetchone()[0]

        conn.close()
        return {
            'total': total,
            'arxiv': arxiv_count,
            'hugging_face': hf_count,
            'favorites': fav_count,
            'meta_analyses': meta_count,
        }

    def get_stats_by_category(self) -> List[Tuple[str, int]]:
        """Return paper count per category code, sorted descending."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT categories FROM papers')
        rows = cursor.fetchall()
        conn.close()

        from collections import Counter
        counter: Counter = Counter()
        for (cats_str,) in rows:
            if cats_str:
                for cat in cats_str.split():
                    if cat in CATEGORIES:
                        counter[cat] += 1
        return counter.most_common()

    def get_stats_by_month(self, limit: int = 12) -> List[Tuple[str, int]]:
        """Return paper count per month (YYYY-MM), most recent first."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUBSTR(published, 1, 7) AS month, COUNT(*) AS cnt
            FROM papers
            WHERE published IS NOT NULL AND LENGTH(published) >= 7
            GROUP BY month
            ORDER BY month DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_stats_top_authors(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Return top authors by paper count."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT authors FROM papers')
        rows = cursor.fetchall()
        conn.close()

        from collections import Counter
        counter: Counter = Counter()
        for (authors_str,) in rows:
            if authors_str:
                for author in authors_str.split(', '):
                    name = author.strip()
                    if name:
                        counter[name] += 1
        return counter.most_common(limit)

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class Paper:
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
    ):
        self.arxiv_id = arxiv_id
        self.title = title
        self.abstract = abstract
        self.authors = authors
        self.published = published
        self.updated = updated
        self.categories = categories
        self.pdf_url = pdf_url
        self.is_meta_analysis = is_meta_analysis
        self.source = source
        self.is_favorite = is_favorite

    def to_dict(self):
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

    def get_all_papers(self, limit: int = 500) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite
            FROM papers 
            ORDER BY published DESC
            LIMIT ?
        ''', (limit,))
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
        
        sql += ' ORDER BY published DESC LIMIT 500'
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_papers_by_category(self, category: str, limit: int = 500) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite
            FROM papers 
            WHERE categories LIKE ?
            ORDER BY published DESC
            LIMIT ?
        ''', (f'%{category}%', limit))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_meta_analyses(self, limit: int = 500) -> List:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, source, is_favorite
            FROM papers 
            WHERE is_meta_analysis = 1
            ORDER BY published DESC
            LIMIT ?
        ''', (limit,))
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

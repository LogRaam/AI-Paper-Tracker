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
        is_meta_analysis: bool = False
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
            'is_meta_analysis': int(self.is_meta_analysis)
        }


CATEGORIES = {
    'cs.LG': 'MachineLearning',
    'cs.CL': 'NLP',
    'cs.CV': 'ComputerVision',
    'cs.NE': 'NeuralEvolution',
    'cs.AI': 'ArtificialIntelligence',
    'cs.RO': 'Robotics',
    'stat.ML': 'StatisticalML'
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
                fetched_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_published ON papers(published)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_categories ON papers(categories)
        ''')
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
            (arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['arxiv_id'], data['title'], data['abstract'], data['authors'],
            data['published'], data['updated'], data['categories'], data['pdf_url'],
            data['is_meta_analysis'], data['fetched_at']
        ))
        conn.commit()
        conn.close()

    def add_papers(self, papers: List[Paper]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        for paper in papers:
            data = paper.to_dict()
            data['fetched_at'] = now
            cursor.execute('''
                INSERT OR IGNORE INTO papers 
                (arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['arxiv_id'], data['title'], data['abstract'], data['authors'],
                data['published'], data['updated'], data['categories'], data['pdf_url'],
                data['is_meta_analysis'], now
            ))
        conn.commit()
        conn.close()

    def get_all_papers(self, limit: int = 500) -> List[Paper]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis
            FROM papers 
            ORDER BY published DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def search_papers(self, query: str, category: Optional[str] = None, meta_only: bool = False) -> List[Paper]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = '''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis
            FROM papers 
            WHERE (title LIKE ? OR abstract LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%']
        
        if category and category != 'All':
            sql += ' AND categories LIKE ?'
            params.append(f'%{category}%')
        
        if meta_only:
            sql += ' AND is_meta_analysis = 1'
        
        sql += ' ORDER BY published DESC LIMIT 500'
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_papers_by_category(self, category: str, limit: int = 500) -> List[Paper]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis
            FROM papers 
            WHERE categories LIKE ?
            ORDER BY published DESC
            LIMIT ?
        ''', (f'%{category}%', limit))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_paper(row) for row in rows]

    def get_meta_analyses(self, limit: int = 500) -> List[Paper]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published, updated, categories, pdf_url, is_meta_analysis
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

    def _row_to_paper(self, row) -> Paper:
        return Paper(
            arxiv_id=row[0],
            title=row[1],
            abstract=row[2],
            authors=row[3],
            published=row[4],
            updated=row[5],
            categories=row[6],
            pdf_url=row[7],
            is_meta_analysis=bool(row[8])
        )

import arxiv
from datetime import datetime, timedelta, timezone
from typing import List
import re

from models import Paper, CATEGORIES, CATEGORY_CODES


META_ANALYSIS_KEYWORDS = [
    'meta-analysis',
    'meta analysis',
    'systematic review',
    'survey',
    'review of',
    'overview of',
    'state of the art',
    'state-of-the-art',
    'comprehensive survey',
    'systematic literature',
]


def is_meta_analysis(title: str, abstract: str) -> bool:
    text = f"{title} {abstract}".lower()
    for keyword in META_ANALYSIS_KEYWORDS:
        if keyword in text:
            return True
    return False


def get_category_display(categories_str: str) -> str:
    cats = categories_str.split()
    display = []
    for cat in cats:
        if cat in CATEGORIES:
            display.append(CATEGORIES[cat])
        else:
            display.append(cat)
    return ', '.join(display)


def fetch_papers(days_back: int = 7, max_results: int = 3000, progress_callback=None) -> List[Paper]:
    papers = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    client = arxiv.Client()
    total_cats = len(CATEGORY_CODES)
    
    for idx, cat_code in enumerate(CATEGORY_CODES):
        cat_name = CATEGORIES.get(cat_code, cat_code)
        progress_pct = int((idx / total_cats) * 100)
        
        if progress_callback:
            progress_callback(progress_pct, cat_name)
        else:
            print(f"[{progress_pct}%] Fetching category: {cat_code} ({cat_name})")
        
        search = arxiv.Search(
            query=f"cat:{cat_code}",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        try:
            results = client.results(search)
            
            for result in results:
                try:
                    published_dt = result.published
                    if published_dt.tzinfo is not None:
                        published_dt = published_dt.replace(tzinfo=None)
                    
                    if published_dt < cutoff_date.replace(tzinfo=None):
                        continue
                    
                    arxiv_id = result.entry_id.split('/')[-1]
                    
                    title = result.title.replace('\n', ' ').strip()
                    abstract = result.summary.replace('\n', ' ').strip()
                    authors = ', '.join([author.name for author in result.authors])
                    published = result.published.strftime('%Y-%m-%d')
                    updated = result.updated.strftime('%Y-%m-%d') if result.updated else published
                    categories = ' '.join(result.categories)
                    pdf_url = result.pdf_url
                    
                    meta = is_meta_analysis(title, abstract)
                    
                    paper = Paper(
                        arxiv_id=arxiv_id,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        published=published,
                        updated=updated,
                        categories=categories,
                        pdf_url=pdf_url,
                        is_meta_analysis=meta
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error fetching category {cat_code}: {e}")
            continue
    
    if progress_callback:
        progress_callback(100, "Complete")
    
    return papers


def fetch_all_recent_papers(days_back: int = 7, progress_callback=None) -> List[Paper]:
    if progress_callback:
        progress_callback(0, "Starting...")
    
    papers = fetch_papers(days_back=days_back, progress_callback=progress_callback)
    return papers

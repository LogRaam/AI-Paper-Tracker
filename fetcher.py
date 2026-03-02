import arxiv
from datetime import datetime, timedelta, timezone
from typing import List, Callable
import sys
import re
import time

from models import Paper, CATEGORIES, CATEGORY_CODES


def retry_request(func, max_retries=3, initial_delay=5, log_callback=None):
    """Execute a function with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            delay = initial_delay * (2 ** attempt)
            msg = f"Retry {attempt + 1}/{max_retries} after error: {e}. Waiting {delay}s..."
            if log_callback:
                log_callback(msg)
            else:
                print(msg, flush=True)
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise


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


def fetch_papers(days_back: int = 7, max_results: int = 10000, progress_callback: Callable = None, start_date: str = None, end_date: str = None, log_callback: Callable = None) -> List[Paper]:
    papers = []
    if start_date:
        cutoff_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_dt = None
    
    # Parse start_date once before the loop
    cutoff_start = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    
    client = arxiv.Client()
    total_cats = len(CATEGORY_CODES)
    
    for idx, cat_code in enumerate(CATEGORY_CODES):
        cat_name = CATEGORIES.get(cat_code, cat_code)
        progress_pct = int((idx / total_cats) * 100)
        
        msg = f"Fetching: {cat_name}"
        
        if log_callback:
            log_callback(msg)
        else:
            print(msg, flush=True)
        
        if progress_callback:
            progress_callback(progress_pct, msg)
        
        search = arxiv.Search(
            query=f"cat:{cat_code}",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.LastUpdatedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        try:
            results = retry_request(
                lambda: client.results(search),
                max_retries=3,
                initial_delay=5,
                log_callback=log_callback
            )
            
            for result in results:
                try:
                    updated_dt = result.updated
                    if updated_dt and updated_dt.tzinfo is not None:
                        updated_dt = updated_dt.replace(tzinfo=None)
                    elif updated_dt is None:
                        updated_dt = result.published
                        if updated_dt and updated_dt.tzinfo is not None:
                            updated_dt = updated_dt.replace(tzinfo=None)
                    
                    published_dt = result.published
                    if published_dt.tzinfo is not None:
                        published_dt = published_dt.replace(tzinfo=None)
                    
                    # Use cutoff_start parsed outside the loop
                    if cutoff_start:
                        if updated_dt < cutoff_start:
                            break  # Stop iteration when papers become too old
                    else:
                        if updated_dt < cutoff_date.replace(tzinfo=None):
                            break  # Stop iteration when papers become too old
                    
                    if end_dt and updated_dt > end_dt:
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
                        is_meta_analysis=meta,
                        source="arXiv"
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            err_msg = f"Error fetching category {cat_code}: {e}"
            if log_callback:
                log_callback(err_msg)
            else:
                print(err_msg, flush=True)
            continue
        
        time.sleep(3)
    
    complete_msg = f"Complete! Found {len(papers)} papers"
    if log_callback:
        log_callback(complete_msg)
    else:
        print(complete_msg, flush=True)
    
    if progress_callback:
        progress_callback(100, "Complete")
    
    return papers


def fetch_all_recent_papers(days_back: int = 7, progress_callback: Callable = None, start_date: str = None, end_date: str = None, log_callback: Callable = None) -> List[Paper]:
    from datetime import datetime
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if start_date and end_date:
        msg = f"[{current_time}] Starting fetch from {start_date} to {end_date}..."
    elif start_date:
        msg = f"[{current_time}] Starting fetch from {start_date} to today..."
    else:
        msg = f"[{current_time}] Starting fetch for last {days_back} days..."
    
    if log_callback:
        log_callback(msg)
    else:
        print(msg, flush=True)
    
    papers = fetch_papers(days_back=days_back, progress_callback=progress_callback, start_date=start_date, end_date=end_date, log_callback=log_callback)
    return papers

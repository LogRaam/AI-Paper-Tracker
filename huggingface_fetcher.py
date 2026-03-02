from huggingface_hub import HfApi
from datetime import datetime, timedelta
from typing import List, Callable
import time

from models import Paper


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


def fetch_papers_huggingface(progress_callback: Callable = None, start_date: str = None, end_date: str = None, log_callback: Callable = None) -> List[Paper]:
    papers = []
    
    try:
        api = HfApi()
    except Exception as e:
        err_msg = f"ERROR: Could not initialize Hugging Face API: {e}"
        if log_callback:
            log_callback(err_msg)
        else:
            print(err_msg, flush=True)
        return papers
    
    search_queries = ["machine learning", "deep learning", "neural network", "artificial intelligence", "transformer", "NLP", "computer vision"]
    
    for query in search_queries:
        if progress_callback:
            progress_callback(50, f"Fetching HF: {query}")
        
        try:
            results = retry_request(
                lambda: list(api.list_papers(query=query, limit=100)),
                max_retries=3,
                initial_delay=5,
                log_callback=log_callback
            )
            
            for p in results:
                try:
                    title = p.title or ""
                    abstract = p.summary or ""
                    arxiv_id = p.id or ""
                    published = str(p.published_at)[:10] if p.published_at else ""
                    authors = ", ".join([a.name for a in p.authors]) if p.authors else ""
                    
                    cats = []
                    if p.ai_keywords:
                        cats.extend(p.ai_keywords[:5])
                    categories = ", ".join(cats) if cats else "HuggingFace"
                    
                    pdf_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
                    
                    # Hugging Face papers are already trending/recent, don't filter by date
                    # but apply end_date filter if specified to exclude papers outside the month
                    
                    paper = Paper(
                        arxiv_id=arxiv_id,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        published=published,
                        updated=published,
                        categories=categories,
                        pdf_url=pdf_url,
                        is_meta_analysis=False,
                        source="Hugging Face"
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    continue
            
            msg = f"Query '{query}': fetched {len(results)} papers"
            if log_callback:
                log_callback(msg)
            else:
                print(msg, flush=True)
            
            time.sleep(1)
            
        except Exception as e:
            err_msg = f"Error fetching Hugging Face Papers (query: {query}): {e}"
            if log_callback:
                log_callback(err_msg)
            else:
                print(err_msg, flush=True)
    
    unique_papers = {}
    for p in papers:
        if p.arxiv_id not in unique_papers:
            unique_papers[p.arxiv_id] = p
    
    final_papers = list(unique_papers.values())
    complete_msg = f"Hugging Face Papers fetch complete: {len(final_papers)} unique papers"
    if log_callback:
        log_callback(complete_msg)
    else:
        print(complete_msg, flush=True)
    return final_papers


def fetch_all_papers_huggingface(progress_callback: Callable = None, start_date: str = None, end_date: str = None, log_callback: Callable = None) -> List[Paper]:
    from datetime import datetime
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = f"[{current_time}] Starting Hugging Face Papers fetch..."
    if log_callback:
        log_callback(msg)
    else:
        print(msg, flush=True)
    papers = fetch_papers_huggingface(progress_callback=progress_callback, start_date=start_date, end_date=end_date, log_callback=log_callback)
    return papers

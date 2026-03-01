from paperswithcode import PapersWithCodeClient
from datetime import datetime, timedelta
from typing import List, Callable
import time
import logging

from models import Paper


def fetch_papers_with_code(progress_callback: Callable = None, start_date: str = None) -> List[Paper]:
    papers = []
    
    try:
        client = PapersWithCodeClient()
    except Exception as e:
        print(f"ERROR: Could not initialize PapersWithCode client: {e}", flush=True)
        return papers
    
    page = 1
    total_fetched = 0
    
    while True:
        if progress_callback:
            progress_callback(int((page % 10) * 10), f"Page {page}")
        
        try:
            result = client.paper_list(page=page, items_per_page=50)
            
            if not result.results:
                break
            
            for p in result.results:
                try:
                    if start_date:
                        if p.published and str(p.published) <= start_date:
                            continue
                    elif p.published:
                        cutoff = datetime.now().date() - timedelta(days=7)
                        if p.published < cutoff:
                            continue
                    
                    if not p.arxiv_id:
                        continue
                    
                    title = p.title or ""
                    abstract = p.abstract or ""
                    authors = ", ".join(p.authors) if p.authors else ""
                    published = str(p.published) if p.published else ""
                    updated = published
                    
                    cats = []
                    if p.task:
                        cats.append(p.task)
                    if p.conference:
                        cats.append(str(p.conference))
                    categories = ", ".join(cats) if cats else "PapersWithCode"
                    
                    pdf_url = p.url_pdf or p.url_abs or ""
                    
                    paper = Paper(
                        arxiv_id=p.arxiv_id,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        published=published,
                        updated=updated,
                        categories=categories,
                        pdf_url=pdf_url,
                        is_meta_analysis=False
                    )
                    
                    papers.append(paper)
                    total_fetched += 1
                    
                except Exception as e:
                    continue
            
            if not result.next_page:
                break
                
            page += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"Error fetching Papers with Code: {e}", flush=True)
            break
    
    return papers


def fetch_all_papers_with_code(progress_callback: Callable = None, start_date: str = None) -> List[Paper]:
    print("Fetching papers from Papers with Code...", flush=True)
    papers = fetch_papers_with_code(progress_callback=progress_callback, start_date=start_date)
    print(f"Papers with Code: Found {len(papers)} papers", flush=True)
    return papers

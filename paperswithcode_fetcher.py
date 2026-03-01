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
    max_pages = 20
    max_retries = 3
    
    for retry in range(max_retries):
        try:
            while page <= max_pages:
                if progress_callback:
                    progress_callback(int((page % 10) * 10), f"Fetching Papers with Code (page {page})")
                
                try:
                    result = client.paper_list(page=page, items_per_page=50)
                    
                    if not result.results:
                        print(f"No more results at page {page}", flush=True)
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
                                is_meta_analysis=False,
                                source="Papers with Code"
                            )
                            
                            papers.append(paper)
                            total_fetched += 1
                            
                        except Exception as e:
                            continue
                    
                    print(f"Page {page}: fetched {len(result.results)} papers, total: {total_fetched}", flush=True)
                    
                    if not result.next_page:
                        break
                    
                    page += 1
                    time.sleep(2)
                
                except Exception as e:
                    error_str = str(e)
                    if "JSONDecodeError" in error_str or "HttpClientError" in error_str:
                        if retry < max_retries - 1:
                            print(f"Rate limited, retrying in {5 * (retry + 1)} seconds...", flush=True)
                            time.sleep(5 * (retry + 1))
                            continue
                    print(f"Error fetching Papers with Code (page {page}): {e}", flush=True)
                    break
            
            break
            
        except Exception as e:
            if retry < max_retries - 1:
                print(f"Connection error, retry {retry + 1}/{max_retries}: {e}", flush=True)
                time.sleep(5)
                continue
            print(f"Failed after {max_retries} retries: {e}", flush=True)
    
    print(f"Papers with Code fetch complete: {total_fetched} papers", flush=True)
    return papers


def fetch_all_papers_with_code(progress_callback: Callable = None, start_date: str = None) -> List[Paper]:
    print("Starting Papers with Code fetch...", flush=True)
    papers = fetch_papers_with_code(progress_callback=progress_callback, start_date=start_date)
    return papers

from huggingface_hub import HfApi
from datetime import datetime, timedelta
from typing import List, Callable
import time

from models import Paper


def fetch_papers_huggingface(progress_callback: Callable = None, start_date: str = None) -> List[Paper]:
    papers = []
    
    try:
        api = HfApi()
    except Exception as e:
        print(f"ERROR: Could not initialize Hugging Face API: {e}", flush=True)
        return papers
    
    search_queries = ["machine learning", "deep learning", "neural network", "artificial intelligence", "transformer", "NLP", "computer vision"]
    
    for query in search_queries:
        if progress_callback:
            progress_callback(50, f"Fetching HF: {query}")
        
        try:
            results = list(api.list_papers(
                query=query,
                limit=100
            ))
            
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
            
            print(f"Query '{query}': fetched {len(results)} papers", flush=True)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error fetching Hugging Face Papers (query: {query}): {e}", flush=True)
    
    unique_papers = {}
    for p in papers:
        if p.arxiv_id not in unique_papers:
            unique_papers[p.arxiv_id] = p
    
    final_papers = list(unique_papers.values())
    print(f"Hugging Face Papers fetch complete: {len(final_papers)} unique papers", flush=True)
    return final_papers


def fetch_all_papers_huggingface(progress_callback: Callable = None, start_date: str = None) -> List[Paper]:
    print("Starting Hugging Face Papers fetch...", flush=True)
    papers = fetch_papers_huggingface(progress_callback=progress_callback, start_date=start_date)
    return papers

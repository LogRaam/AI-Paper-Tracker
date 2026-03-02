"""Shared fixtures for AI Paper Tracker tests."""

import os
import sys
import pytest

# Add project root to sys.path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import Paper, Database


def make_paper(
    arxiv_id: str = "2501.00001",
    title: str = "Test Paper Title",
    abstract: str = "This is a test abstract.",
    authors: str = "Alice, Bob",
    published: str = "2025-01-15",
    updated: str = "2025-01-20",
    categories: str = "cs.LG cs.AI",
    pdf_url: str = "https://arxiv.org/pdf/2501.00001",
    is_meta_analysis: bool = False,
    source: str = "arXiv",
    is_favorite: bool = False,
) -> Paper:
    """Create a Paper with sensible defaults. Override any field as needed."""
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=authors,
        published=published,
        updated=updated,
        categories=categories,
        pdf_url=pdf_url,
        is_meta_analysis=is_meta_analysis,
        source=source,
        is_favorite=is_favorite,
    )


@pytest.fixture
def sample_paper():
    """A single default Paper instance."""
    return make_paper()


@pytest.fixture
def sample_papers():
    """A list of 5 distinct Paper instances for batch tests."""
    return [
        make_paper(arxiv_id="2501.00001", title="Paper Alpha", published="2025-01-10", updated="2025-01-15"),
        make_paper(arxiv_id="2501.00002", title="Paper Beta", published="2025-01-12", updated="2025-01-18", categories="cs.CV"),
        make_paper(arxiv_id="2501.00003", title="A Comprehensive Survey of Deep Learning", published="2025-01-14", updated="2025-01-20", is_meta_analysis=True),
        make_paper(arxiv_id="2501.00004", title="Paper Delta", published="2025-01-16", updated="2025-01-22", source="Hugging Face"),
        make_paper(arxiv_id="2501.00005", title="Paper Epsilon", published="2025-01-18", updated="2025-01-25", is_favorite=True),
    ]


@pytest.fixture
def db(tmp_path):
    """A fresh Database backed by a temporary file."""
    db_path = str(tmp_path / "test_papers.db")
    return Database(db_path=db_path)


@pytest.fixture
def populated_db(db, sample_papers):
    """A Database pre-loaded with sample_papers."""
    db.add_papers(sample_papers)
    return db

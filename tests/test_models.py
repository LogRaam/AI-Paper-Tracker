"""Tests for models.py — Paper class and Database class."""

import os
import sys
import sqlite3
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import Paper, Database, CATEGORIES, CATEGORY_CODES


def make_paper(
    arxiv_id="2501.00001",
    title="Test Paper Title",
    abstract="This is a test abstract.",
    authors="Alice, Bob",
    published="2025-01-15",
    updated="2025-01-20",
    categories="cs.LG cs.AI",
    pdf_url="https://arxiv.org/pdf/2501.00001",
    is_meta_analysis=False,
    source="arXiv",
    is_favorite=False,
):
    return Paper(
        arxiv_id=arxiv_id, title=title, abstract=abstract, authors=authors,
        published=published, updated=updated, categories=categories,
        pdf_url=pdf_url, is_meta_analysis=is_meta_analysis, source=source,
        is_favorite=is_favorite,
    )


# ============================================================
# Paper.__init__
# ============================================================

class TestPaperInit:
    def test_required_fields(self):
        p = Paper(
            arxiv_id="2501.99999",
            title="My Title",
            abstract="My Abstract",
            authors="Alice",
            published="2025-01-01",
            updated="2025-01-05",
            categories="cs.LG",
            pdf_url="https://arxiv.org/pdf/2501.99999",
        )
        assert p.arxiv_id == "2501.99999"
        assert p.title == "My Title"
        assert p.abstract == "My Abstract"
        assert p.authors == "Alice"
        assert p.published == "2025-01-01"
        assert p.updated == "2025-01-05"
        assert p.categories == "cs.LG"
        assert p.pdf_url == "https://arxiv.org/pdf/2501.99999"

    def test_default_values(self):
        p = make_paper()
        assert p.is_meta_analysis is False
        assert p.source == "arXiv"
        assert p.is_favorite is False

    def test_custom_optional_fields(self):
        p = make_paper(is_meta_analysis=True, source="Hugging Face", is_favorite=True)
        assert p.is_meta_analysis is True
        assert p.source == "Hugging Face"
        assert p.is_favorite is True

    def test_empty_strings(self):
        p = make_paper(arxiv_id="", title="", abstract="", authors="")
        assert p.arxiv_id == ""
        assert p.title == ""

    def test_unicode_fields(self):
        p = make_paper(
            title="Apprentissage par renforcement: une etude approfondie",
            authors="Jean-Pierre Dupont, Marie-Claire Lefevre"
        )
        assert "etude" in p.title
        assert "Dupont" in p.authors


# ============================================================
# Paper.to_dict
# ============================================================

class TestPaperToDict:
    def test_all_keys_present(self, sample_paper):
        d = sample_paper.to_dict()
        expected_keys = {
            'arxiv_id', 'title', 'abstract', 'authors', 'published',
            'updated', 'categories', 'pdf_url', 'is_meta_analysis',
            'source', 'is_favorite'
        }
        assert set(d.keys()) == expected_keys

    def test_bool_to_int_conversion(self):
        p = make_paper(is_meta_analysis=True, is_favorite=True)
        d = p.to_dict()
        assert d['is_meta_analysis'] == 1
        assert isinstance(d['is_meta_analysis'], int)
        assert d['is_favorite'] == 1
        assert isinstance(d['is_favorite'], int)

    def test_bool_false_to_int_zero(self):
        p = make_paper(is_meta_analysis=False, is_favorite=False)
        d = p.to_dict()
        assert d['is_meta_analysis'] == 0
        assert d['is_favorite'] == 0

    def test_values_match_attributes(self, sample_paper):
        d = sample_paper.to_dict()
        assert d['arxiv_id'] == sample_paper.arxiv_id
        assert d['title'] == sample_paper.title
        assert d['source'] == sample_paper.source


# ============================================================
# Database.__init__ / _init_db
# ============================================================

class TestDatabaseInit:
    def test_creates_db_file(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        Database(db_path=db_path)
        assert (tmp_path / "new.db").exists()

    def test_creates_papers_table(self, db):
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_indices(self, db):
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indices = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert 'idx_published' in indices
        assert 'idx_categories' in indices
        assert 'idx_source' in indices
        assert 'idx_favorite' in indices

    def test_idempotent_init(self, tmp_path):
        db_path = str(tmp_path / "idem.db")
        db1 = Database(db_path=db_path)
        db1.add_paper(make_paper())
        # Re-init same DB — should not lose data
        db2 = Database(db_path=db_path)
        assert db2.get_paper_count() == 1

    def test_table_columns(self, db):
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(papers)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {
            'arxiv_id', 'title', 'abstract', 'authors', 'published',
            'updated', 'categories', 'pdf_url', 'is_meta_analysis',
            'source', 'is_favorite', 'fetched_at'
        }
        assert expected.issubset(columns)


# ============================================================
# Database.paper_exists
# ============================================================

class TestPaperExists:
    def test_returns_false_empty_db(self, db):
        assert db.paper_exists("nonexistent") is False

    def test_returns_true_after_add(self, db, sample_paper):
        db.add_paper(sample_paper)
        assert db.paper_exists(sample_paper.arxiv_id) is True

    def test_returns_false_wrong_id(self, db, sample_paper):
        db.add_paper(sample_paper)
        assert db.paper_exists("9999.99999") is False


# ============================================================
# Database.add_paper / add_papers
# ============================================================

class TestAddPaper:
    def test_add_single_paper(self, db, sample_paper):
        db.add_paper(sample_paper)
        assert db.get_paper_count() == 1

    def test_insert_or_ignore_duplicate(self, db, sample_paper):
        db.add_paper(sample_paper)
        db.add_paper(sample_paper)  # same arxiv_id
        assert db.get_paper_count() == 1

    def test_fetched_at_is_set(self, db, sample_paper):
        db.add_paper(sample_paper)
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT fetched_at FROM papers WHERE arxiv_id = ?", (sample_paper.arxiv_id,))
        fetched_at = cursor.fetchone()[0]
        conn.close()
        assert fetched_at is not None
        assert "T" in fetched_at  # ISO format


class TestAddPapers:
    def test_add_batch(self, db, sample_papers):
        db.add_papers(sample_papers)
        assert db.get_paper_count() == 5

    def test_add_empty_list(self, db):
        db.add_papers([])
        assert db.get_paper_count() == 0

    def test_duplicates_in_batch_ignored(self, db):
        p1 = make_paper(arxiv_id="same.id", title="First")
        p2 = make_paper(arxiv_id="same.id", title="Second")
        db.add_papers([p1, p2])
        assert db.get_paper_count() == 1

    def test_mix_new_and_existing(self, db, sample_paper):
        db.add_paper(sample_paper)
        new_paper = make_paper(arxiv_id="2501.99999", title="New Paper")
        db.add_papers([sample_paper, new_paper])
        assert db.get_paper_count() == 2


# ============================================================
# Database.get_all_papers
# ============================================================

class TestGetAllPapers:
    def test_empty_db(self, db):
        assert db.get_all_papers() == []

    def test_returns_all(self, populated_db):
        papers = populated_db.get_all_papers()
        assert len(papers) == 5

    def test_ordered_by_published_desc(self, populated_db):
        papers = populated_db.get_all_papers()
        dates = [p.published for p in papers]
        assert dates == sorted(dates, reverse=True)

    def test_returns_paper_instances(self, populated_db):
        papers = populated_db.get_all_papers()
        for p in papers:
            assert isinstance(p, Paper)


# ============================================================
# Database.search_papers
# ============================================================

class TestSearchPapers:
    def test_search_by_title(self, populated_db):
        results = populated_db.search_papers(query="Alpha")
        assert len(results) == 1
        assert results[0].title == "Paper Alpha"

    def test_search_by_abstract(self, populated_db):
        # All sample papers have "test abstract"
        results = populated_db.search_papers(query="test abstract")
        assert len(results) == 5

    def test_search_case_insensitive(self, populated_db):
        results = populated_db.search_papers(query="alpha")
        assert len(results) == 1

    def test_filter_by_category(self, populated_db):
        results = populated_db.search_papers(category="cs.CV")
        assert len(results) == 1
        assert "cs.CV" in results[0].categories

    def test_category_all_returns_all(self, populated_db):
        results = populated_db.search_papers(category="All")
        assert len(results) == 5

    def test_filter_by_source(self, populated_db):
        results = populated_db.search_papers(source="Hugging Face")
        assert len(results) == 1
        assert results[0].source == "Hugging Face"

    def test_source_all_returns_all(self, populated_db):
        results = populated_db.search_papers(source="All")
        assert len(results) == 5

    def test_filter_meta_only(self, populated_db):
        results = populated_db.search_papers(meta_only=True)
        assert len(results) == 1
        assert results[0].is_meta_analysis is True

    def test_filter_favorites_only(self, populated_db):
        results = populated_db.search_papers(favorites_only=True)
        assert len(results) == 1
        assert results[0].is_favorite is True

    def test_combined_filters(self, populated_db):
        # Query + category: only Paper Alpha is in cs.LG (default) with "Alpha" in title
        results = populated_db.search_papers(query="Alpha", category="cs.LG")
        assert len(results) == 1

    def test_no_match(self, populated_db):
        results = populated_db.search_papers(query="nonexistent_xyz_123")
        assert len(results) == 0

    def test_empty_query_no_filters_returns_all(self, populated_db):
        results = populated_db.search_papers()
        assert len(results) == 5


# ============================================================
# Database.get_papers_by_category
# ============================================================

class TestGetPapersByCategory:
    def test_known_category(self, populated_db):
        results = populated_db.get_papers_by_category("cs.CV")
        assert len(results) == 1

    def test_broad_category_match(self, populated_db):
        # cs.LG is the default — 4 papers have it (all except Paper Beta which is cs.CV)
        results = populated_db.get_papers_by_category("cs.LG")
        assert len(results) == 4

    def test_no_match(self, populated_db):
        results = populated_db.get_papers_by_category("cs.XX")
        assert len(results) == 0

    def test_returns_paper_instances(self, populated_db):
        results = populated_db.get_papers_by_category("cs.LG")
        for p in results:
            assert isinstance(p, Paper)


# ============================================================
# Database.get_meta_analyses
# ============================================================

class TestGetMetaAnalyses:
    def test_returns_meta_only(self, populated_db):
        results = populated_db.get_meta_analyses()
        assert len(results) == 1
        assert results[0].is_meta_analysis is True

    def test_empty_when_no_meta(self, db):
        db.add_paper(make_paper(is_meta_analysis=False))
        assert db.get_meta_analyses() == []


# ============================================================
# Database.get_paper_count
# ============================================================

class TestGetPaperCount:
    def test_empty(self, db):
        assert db.get_paper_count() == 0

    def test_after_insert(self, populated_db):
        assert populated_db.get_paper_count() == 5

    def test_no_increase_on_duplicate(self, db, sample_paper):
        db.add_paper(sample_paper)
        db.add_paper(sample_paper)
        assert db.get_paper_count() == 1


# ============================================================
# Database.get_last_fetch
# ============================================================

class TestGetLastFetch:
    def test_none_on_empty_db(self, db):
        assert db.get_last_fetch() is None

    def test_returns_string_after_insert(self, db, sample_paper):
        db.add_paper(sample_paper)
        last = db.get_last_fetch()
        assert last is not None
        assert isinstance(last, str)


# ============================================================
# Database.get_most_recent_date
# ============================================================

class TestGetMostRecentDate:
    def test_none_on_empty_db(self, db):
        assert db.get_most_recent_date() is None

    def test_returns_latest_updated(self, populated_db):
        most_recent = populated_db.get_most_recent_date()
        assert most_recent == "2025-01-25"  # Paper Epsilon has latest updated


# ============================================================
# Database.toggle_favorite
# ============================================================

class TestToggleFavorite:
    def test_toggle_on(self, db, sample_paper):
        db.add_paper(sample_paper)
        result = db.toggle_favorite(sample_paper.arxiv_id)
        assert result is True

    def test_toggle_off(self, db, sample_paper):
        db.add_paper(sample_paper)
        db.toggle_favorite(sample_paper.arxiv_id)  # on
        result = db.toggle_favorite(sample_paper.arxiv_id)  # off
        assert result is False

    def test_toggle_nonexistent_id(self, db):
        result = db.toggle_favorite("nonexistent.id")
        assert result is False

    def test_toggle_persists_in_db(self, db, sample_paper):
        db.add_paper(sample_paper)
        db.toggle_favorite(sample_paper.arxiv_id)
        # Re-read from DB
        papers = db.get_all_papers()
        assert papers[0].is_favorite is True


# ============================================================
# Database._row_to_paper
# ============================================================

class TestRowToPaper:
    def test_full_row(self, db):
        row = ("id1", "Title", "Abstract", "Authors", "2025-01-01", "2025-01-05",
               "cs.LG", "http://pdf", 1, "arXiv", 1)
        p = db._row_to_paper(row)
        assert p.arxiv_id == "id1"
        assert p.is_meta_analysis is True
        assert p.is_favorite is True

    def test_9_element_row_defaults(self, db):
        row = ("id2", "Title", "Abstract", "Authors", "2025-01-01", "2025-01-05",
               "cs.LG", "http://pdf", 0)
        p = db._row_to_paper(row)
        assert p.source == "arXiv"
        assert p.is_favorite is False

    def test_10_element_row_defaults(self, db):
        row = ("id3", "Title", "Abstract", "Authors", "2025-01-01", "2025-01-05",
               "cs.LG", "http://pdf", 0, "Hugging Face")
        p = db._row_to_paper(row)
        assert p.source == "Hugging Face"
        assert p.is_favorite is False

    def test_bool_conversion(self, db):
        row = ("id4", "Title", "Abstract", "Authors", "2025-01-01", "2025-01-05",
               "cs.LG", "http://pdf", 0, "arXiv", 0)
        p = db._row_to_paper(row)
        assert p.is_meta_analysis is False
        assert p.is_favorite is False


# ============================================================
# CATEGORIES / CATEGORY_CODES constants
# ============================================================

class TestConstants:
    def test_categories_has_9_entries(self):
        assert len(CATEGORIES) == 9

    def test_category_codes_matches_keys(self):
        assert CATEGORY_CODES == list(CATEGORIES.keys())

    def test_known_categories_present(self):
        assert 'cs.LG' in CATEGORIES
        assert 'cs.CL' in CATEGORIES
        assert 'cs.CV' in CATEGORIES
        assert 'stat.ML' in CATEGORIES

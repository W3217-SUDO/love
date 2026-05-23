from app.modules.daily_log.catalog import (
    CATEGORIES,
    TAG_BY_KEY,
    TAGS,
    TAGS_BY_CATEGORY,
    category_of,
    is_valid_category,
    is_valid_tag,
)


def test_all_categories_have_unique_keys():
    keys = [c.key for c in CATEGORIES]
    assert len(keys) == len(set(keys)), f"duplicate category keys: {keys}"


def test_all_tags_have_unique_keys():
    keys = [t.key for t in TAGS]
    assert len(keys) == len(set(keys)), "duplicate tag keys"


def test_every_tag_belongs_to_known_category():
    cat_keys = {c.key for c in CATEGORIES}
    for tag in TAGS:
        assert tag.category in cat_keys, f"tag {tag.key} -> unknown category {tag.category}"


def test_tag_by_key_lookup_matches_iteration():
    for tag in TAGS:
        assert TAG_BY_KEY[tag.key] is tag


def test_tags_by_category_complete():
    """Sum of grouped lists == TAGS"""
    grouped_total = sum(len(v) for v in TAGS_BY_CATEGORY.values())
    assert grouped_total == len(TAGS)


def test_is_valid_tag_known():
    assert is_valid_tag("mood_happy") is True


def test_is_valid_tag_unknown():
    assert is_valid_tag("nonexistent_tag") is False


def test_is_valid_category():
    assert is_valid_category("mood") is True
    assert is_valid_category("zzz") is False


def test_category_of():
    assert category_of("mood_happy") == "mood"
    assert category_of("sym_cramps") == "symptoms"


def test_minimum_coverage_per_category():
    """Each category must have at least 2 tags (otherwise it's not worth being a category)."""
    for cat in CATEGORIES:
        assert len(TAGS_BY_CATEGORY[cat.key]) >= 2, f"category {cat.key} has too few tags"

"""Tests for entity resolution (no API calls — tests phonetic/spelling only)."""

from ontograph.resolve import phonetic_similarity, spelling_similarity


def test_phonetic_exact_match():
    assert phonetic_similarity("Reed", "Reed") == 1.0


def test_phonetic_similar_names():
    # Niko and Nila should have some phonetic overlap
    score = phonetic_similarity("Niko", "Nila")
    assert score > 0.0


def test_phonetic_dissimilar():
    score = phonetic_similarity("Lena", "Dev")
    assert score < 0.5


def test_spelling_exact():
    assert spelling_similarity("Reed", "Reed") == 1.0


def test_spelling_typo():
    score = spelling_similarity("Dael", "Dale")
    assert score > 0.5  # Jaro-Winkler should catch this


def test_spelling_dissimilar():
    score = spelling_similarity("Nara", "Flux")
    assert score < 0.6


def test_spelling_case_insensitive():
    assert spelling_similarity("reed", "Reed") == 1.0

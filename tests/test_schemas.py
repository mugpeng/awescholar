"""Tests for schemas.py — Pydantic model validation."""

from awescholar.schemas import PaperAnnotation, AnnotationResult, FilteredPaper, FilterResult


def test_paper_annotation_roundtrip():
    data = {"doi": "10.1234/test", "domain": "AI", "category": "Models"}
    model = PaperAnnotation(**data)
    assert model.doi == "10.1234/test"
    assert model.model_dump() == data


def test_annotation_result():
    result = AnnotationResult(
        paper_list=[
            PaperAnnotation(doi="10.1/a", domain="Bio", category="Genomics"),
            PaperAnnotation(doi="10.1/b", domain="Chem", category="Drug"),
        ],
        category_list=["Genomics", "Drug"],
    )
    assert len(result.paper_list) == 2
    assert result.category_list == ["Genomics", "Drug"]


def test_filtered_paper_with_reason():
    paper = FilteredPaper(doi="10.1/a", title="Test", reason="Top venue")
    assert paper.reason == "Top venue"
    assert paper.venue == ""


def test_filter_result_structure():
    result = FilterResult(papers={
        "Genomics": [FilteredPaper(doi="10.1/a", title="A", reason="Relevant")],
        "Drug": [FilteredPaper(doi="10.1/b", title="B", reason="High quality")],
    })
    assert len(result.papers) == 2
    assert result.papers["Genomics"][0].doi == "10.1/a"


def test_annotation_result_from_json():
    json_str = '{"paper_list": [{"doi": "10.1/x", "domain": "ML", "category": "Models"}], "category_list": ["Models"]}'
    result = AnnotationResult.model_validate_json(json_str)
    assert result.paper_list[0].doi == "10.1/x"

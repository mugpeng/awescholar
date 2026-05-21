"""Pydantic schemas for structured LLM output."""

from pydantic import BaseModel, Field


class PaperAnnotation(BaseModel):
    doi: str = Field(description="The paper DOI")
    domain: str = Field(description="Research domain inferred from title and abstract")
    category: str = Field(description="Category from predefined list or inferred")


class AnnotationResult(BaseModel):
    paper_list: list[PaperAnnotation] = Field(description="Annotated papers")
    category_list: list[str] = Field(description="All categories found")


class FilteredPaper(BaseModel):
    doi: str
    title: str
    venue: str = ""
    affiliation: str = ""
    reason: str = Field(description="Why this paper was selected")


class FilterResult(BaseModel):
    papers: dict[str, list[FilteredPaper]] = Field(
        description="Filtered papers grouped by category, each with inclusion reason"
    )

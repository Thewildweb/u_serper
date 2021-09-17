from typing import Optional

from pydantic import BaseModel


class SiteLink(BaseModel):
    title: str
    link: str
    snippet: Optional[str]


class Question(BaseModel):
    question: str
    answer: str


class OrganicResult(BaseModel):
    position: int
    title: str
    link: str
    displayed_link: str
    snippet: str
    sitelinks_search_box: bool = False
    sitelinks: Optional[list[SiteLink]]
    questions: Optional[list[Question]]


class SERP(BaseModel):
    organic_results: list[OrganicResult]
    # TODO: Create more data objects


class SEResult(BaseModel):
    query: str
    nr_pages: int
    pages: list[SERP]

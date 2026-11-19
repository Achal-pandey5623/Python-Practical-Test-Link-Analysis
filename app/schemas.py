from typing import Literal
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class LinkAnalysisRequest(BaseModel):
    url: AnyHttpUrl


class Competitor(BaseModel):
    name: str
    overview: str
    strengths: list[str]
    weaknesses_or_gaps: list[str]
    evidence_status: Literal["suggested", "verified"] = "suggested"


class CompetitorAnalysis(BaseModel):
    brand_overview: str
    competitors: list[Competitor]
    strengths: list[str]
    opportunities: list[str]


class Brand(BaseModel):
    name: str
    category: str
    summary: str


class SearchQuery(BaseModel):
    query: str
    platforms: list[Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]]
    intent: str
    business_relevance: str
    target_audience: str


class SEOImprovements(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str]
    long_tail_keywords: list[str]
    business_keywords: list[str]
    recommended_title: str
    title_keyword: str
    title_structure: str
    meta_description: str
    supporting_content: list[str]


class Service(BaseModel):
    service_name: str
    description: str
    target_industry: str
    target_customer: str
    main_benefit: str
    evidence_status: Literal["website", "inferred"]


class AudienceProfile(BaseModel):
    audience: str
    business_type: str
    requirement: str
    customer_profile: str


class TargetAudience(BaseModel):
    primary_audience: list[AudienceProfile]
    secondary_audience: list[AudienceProfile]
    industries: list[str]
    business_types: list[str]
    geographic_focus: str
    customer_needs: list[str]
    interests: list[str]
    recommended_segments: list[str]


class Analysis(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SEOImprovements
    top_services: list[Service] = Field(min_length=5, max_length=5)
    target_audience: TargetAudience


class LinkAnalysisResponse(BaseModel):
    success: bool = True
    website: str
    brand: Brand
    analysis: Analysis
    model_config = ConfigDict(extra="forbid")

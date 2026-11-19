import json
from openai import AsyncOpenAI

from app.config import Settings
from app.schemas import LinkAnalysisResponse


SYSTEM_PROMPT = """Analyze the supplied business website evidence. Use evidence for brand facts; never invent search volume, rankings, or verified competitor research. Mark competitors suggested unless independently verified. Mark each service website or inferred. If evidence is missing, say so. Return concise JSON with these keys: success, website, brand{name,category,summary}, analysis{competitor_analysis{brand_overview,competitors[{name,overview,strengths,weaknesses_or_gaps,evidence_status}],strengths,opportunities},target_search_queries[exactly 5 items with query,platforms,intent,business_relevance,target_audience],seo_improvements{primary_keyword,secondary_keywords,long_tail_keywords,business_keywords,recommended_title,title_keyword,title_structure,meta_description,supporting_content},top_services[exactly 5 items with service_name,description,target_industry,target_customer,main_benefit,evidence_status],target_audience{primary_audience,secondary_audience,industries,business_types,geographic_focus,customer_needs,interests,recommended_segments}}. Keep descriptions and list items short. Platform names must be Google, Facebook, Instagram, LinkedIn, or X."""


async def analyze_page(url: str, page: dict, settings: Settings) -> LinkAnalysisResponse:
    if not settings.llm_api_key:
        raise RuntimeError("LLM is not configured. Set LLM_API_KEY in your environment.")
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    try:
        completion = await client.beta.chat.completions.parse(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"website": url, "page_evidence": page}, ensure_ascii=False)},
            ],
            response_format=LinkAnalysisResponse,
            reasoning_effort="low",
            max_tokens=4096,
            temperature=0.2,
        )
        message = completion.choices[0].message
        if message.parsed is None:
            reason = "model refused the request" if message.refusal else "model returned no structured response"
            raise RuntimeError(f"LLM analysis failed: {reason}.")
        return message.parsed.model_copy(update={"website": url, "success": True})
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"LLM analysis failed ({type(exc).__name__}).") from None
    finally:
        await client.close()

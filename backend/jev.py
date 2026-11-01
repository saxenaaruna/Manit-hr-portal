import os
import logging
from datetime import datetime
from functools import lru_cache

from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, Choice, Noul, Score

load_dotenv()
logger = logging.getLogger("jev")


@lru_cache(maxsize=1)
def get_jev_client() -> AsyncTypeSafeClient:
    proxy = (os.getenv("INTEGRATION_PROXY_URL") or "https://integrations.emergentagent.com").rstrip("/")
    return AsyncTypeSafeClient(api_key=os.environ["EMERGENT_LLM_KEY"], base_url=f"{proxy}/llm/typesafe",
                               retry=RetryPolicy(max_retries=2, respect_retry_after=False))


async def classify_interest(messages):
    """Returns (label, confidence) or (None, 0) if Jev is unavailable."""
    try:
        r = await get_jev_client().system_one(model="jev-latest", state={"hr_messages": messages[-6:]}, questions={
            "interest": Choice(
                instructions="Based on these messages from a company HR representative to a university placement cell, has the company explicitly confirmed it wants to recruit students / hold a campus drive / internship recruitment / receive the recruitment invitation and JNF?",
                criteria={"explicit_interest": "Clearly states their organisation wants to hire, recruit, participate in placements, or asks for the recruitment invitation/JNF",
                          "ambiguous": "Shows some curiosity or is considering, but has not clearly confirmed intent to recruit",
                          "no_interest": "Only general questions about the institute, courses or contacts, with no recruitment intent"})})
        c = r.choices["interest"]
        return c.choice, c.confidence
    except Exception as e:
        logger.warning("Jev interest failed: %s", e)
        return None, 0.0


async def suggest_status(lead):
    try:
        r = await get_jev_client().system_one(model="jev-latest", state={
            "remarks": lead.get("remarks") or "", "recruitment_request": lead.get("recruitment_request") or "",
            "jnf_status": lead.get("jnf_status")}, questions={
            "status": Choice(instructions="Classify this company lead for a campus recruitment CRM.",
                             criteria={"Hot": "Has explicitly expressed interest in recruiting or conducting a campus drive",
                                       "Warm": "Has shown interest, requested information or is considering recruitment without confirming",
                                       "Cold": "No active recruitment interest, declined, or unresponsive"})})
        c = r.choices["status"]
        return {"status": c.choice, "confidence": round(c.confidence, 2), "at": datetime.utcnow().isoformat() + "Z", "ai_classified": True}
    except Exception as e:
        logger.warning("Jev status failed: %s", e)
        return {"status": None, "confidence": 0, "ai_classified": False, "error": "Decision service unavailable"}


async def screen_request(req, kind, days_until):
    try:
        state = {"type": "campus visit" if kind == "visits" else "call with Head of Training & Placement",
                 "company_name": req.get("company_name"), "hr_name": req.get("hr_name"), "designation": req.get("designation"),
                 "work_email_domain": (req.get("work_email") or "").split("@")[-1],
                 "purpose": req.get("visit_purpose") or req.get("discussion_purpose"), "remarks": req.get("remarks"),
                 "days_until_requested_date": days_until}
        r = await get_jev_client().system_one(model="jev-latest", state=state, questions={
            "junk": Noul(instructions="Is this a junk, spam, joke or obviously fake submission rather than a genuine company recruitment-related request?"),
            "urgency": Score(instructions="How urgently should the placement cell review this request? Consider how soon the requested date is and the importance of the purpose.",
                             criteria=["low", "medium", "high", "critical"])})
        u = r.scores["urgency"]
        level = max(u.probabilities, key=u.probabilities.get)
        return {"junk_probability": round(r.nouls["junk"].noul, 2), "urgency_score": round(u.score, 2),
                "urgency_label": ["low", "medium", "high", "critical"][int(level)], "ai_classified": True}
    except Exception as e:
        logger.warning("Jev screen failed: %s", e)
        return {"ai_classified": False}

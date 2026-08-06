"""
aura/memory/extractor.py
------------------------
Background long-term memory extraction node using OpenRouter API.
"""

import json
import logging
import litellm
from aura.config import settings
from aura.memory.store import add_user_fact

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are an intelligent memory extraction system.
Analyze the following conversation turn between a user and an AI assistant.

Task:
Identify any meaningful, long-term personal facts, user preferences, career goals, technical skills, location details, or writing style preferences disclosed by the USER.

Rules:
1. Ignore temporary small talk, greetings ("hi", "hello"), single-turn test questions, or transient queries ("what is 2+2?").
2. Only extract enduring facts about the user (e.g. "User lives in Nellore", "User's favorite language is Python", "User prefers concise code explanations").
3. Return a JSON array of objects, where each object has:
   - "fact": A clean, concise third-person statement about the user.
   - "category": One of ["preference", "identity", "skill", "goal", "location", "other"]

If no relevant long-term facts are found, return an empty array: []

Output ONLY valid JSON. No markdown codeblocks, no surrounding text.
"""


async def extract_and_store_user_memories(user_id: str, user_message: str, assistant_message: str) -> None:
    """Analyze a single conversation turn and persist extracted facts asynchronously."""
    if not user_message or len(user_message.strip()) < 5:
        return

    prompt = f"User Message: {user_message}\nAssistant Message: {assistant_message}"

    try:
        model = f"openrouter/{settings.PRIMARY_MODEL}" if not settings.PRIMARY_MODEL.startswith("openrouter/") else settings.PRIMARY_MODEL
        resp = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            api_key=settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY,
            api_base=settings.OPENROUTER_BASE_URL,
        )

        content = resp.choices[0].message.content.strip()
        
        # Clean JSON formatting if codeblocks were included
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        facts = json.loads(content)
        if isinstance(facts, list):
            for item in facts:
                fact_str = item.get("fact")
                category = item.get("category", "preference")
                if fact_str:
                    await add_user_fact(user_id=user_id, fact=fact_str, category=category)
    except Exception as e:
        logger.warning("Memory extraction encountered an issue: %s", e)

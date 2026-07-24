# backend/shared/llm_client.py
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

EXTRACTION_PROMPT = """You are extracting skills from a {doc_type}.
Map every requirement/skill mentioned onto these categories:
DSA, COD, OOD, APTI, COMM, AI, CLOUD, SQL, SWE, SYSD, NETW, OS, OTHER

For each skill found, give: skill_name, category_code, a short evidence quote
from the text, and your confidence (high/medium/low).

Document text:
{text}
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "category_code": {
                        "type": "string",
                        "enum": ["DSA","COD","OOD","APTI","COMM","AI","CLOUD","SQL","SWE","SYSD","NETW","OS","OTHER"]
                    },
                    "evidence": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["skill_name", "category_code", "evidence", "confidence"]
            }
        }
    },
    "required": ["skills"]
}

def extract_skills(text: str, doc_type: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(doc_type=doc_type, text=text)
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=RESPONSE_SCHEMA,
            temperature=0
        )
    )
    return json.loads(response.text)
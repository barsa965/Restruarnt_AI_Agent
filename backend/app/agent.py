import re
from app.config import settings

KNOWN = {"pizza": "Pizza", "pizzas": "Pizza", "burger": "Burger", "burgers": "Burger",
         "pasta": "Pasta", "biryani": "Biryani", "biriyani": "Biryani"}

def fallback_extract(message: str):
    text = message.lower()
    items = []
    for alias, canonical in KNOWN.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            match = re.search(rf"\b(\d{{1,2}})\s+(?:pieces?\s+of\s+)?{re.escape(alias)}\b", text)
            if canonical not in [x["dish_name"] for x in items]:
                items.append({"dish_name": canonical, "quantity": int(match.group(1)) if match else 1})
    food_intent = bool(items) or any(w in text for w in ("food", "order", "menu", "hungry", "eat"))
    return {"is_food_order": food_intent, "items": items,
            "reply": "Please tell me the dish and quantity." if food_intent and not items else
                     "I am Bloom Kitchen's food-ordering assistant."}

def extract_order(message: str):
    if not settings.GROQ_API_KEY:
        return fallback_extract(message)
    try:
        from pydantic import BaseModel, Field
        from langchain_groq import ChatGroq

        class Item(BaseModel):
            dish_name: str
            quantity: int = Field(ge=1, le=100)

        class Extraction(BaseModel):
            is_food_order: bool
            items: list[Item] = []
            reply: str = ""

        llm = ChatGroq(model=settings.GROQ_MODEL, temperature=0,
                       api_key=settings.GROQ_API_KEY).with_structured_output(Extraction)
        prompt = (
            "Extract only explicitly requested menu dishes and quantities. "
            "Supported dishes: Pizza, Burger, Pasta, Biryani. Default quantity is 1. "
            "Do not invent dishes. For unrelated input set is_food_order=false. "
            "For menu/availability questions without a dish, return an empty items list. "
            f"Customer message: {message}"
        )
        return llm.invoke(prompt).model_dump()
    except Exception:
        return fallback_extract(message)

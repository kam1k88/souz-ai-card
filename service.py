"""Основной сценарий: вход -> проверка -> LLM -> проверка ответа -> карточка."""
from dataclasses import asdict

import llm
from prompts import SYSTEM_PROMPT, build_user_prompt
from schema import NO_DATA
from validate import card_problems, check_input, parse_card, unverified_numbers

MAX_ATTEMPTS = 3


def build_characteristics(product: dict) -> list[dict]:
    """Характеристики берём из входа напрямую, без участия модели."""
    rows = [{"name": k, "value": v or NO_DATA} for k, v in product["specs"].items()]
    rows.insert(0, {"name": "производитель", "value": product["manufacturer"] or NO_DATA})
    return rows


def generate_card(raw_product: dict) -> dict:
    product, missing = check_input(raw_product)       # InputError до вызова API
    provider, model = llm.get_settings()

    feedback: list[str] | None = None
    card, problems, attempts = None, [], 0
    for attempts in range(1, MAX_ATTEMPTS + 1):
        raw = llm.generate(SYSTEM_PROMPT, build_user_prompt(product, feedback), provider, model)
        try:
            card = parse_card(raw)
        except ValueError as e:
            card, problems = None, [str(e)]
        else:
            problems = card_problems(card)
        if card is not None and not problems:
            break
        feedback = problems

    if card is None:
        raise llm.LLMError("Модель не вернула валидный JSON: " + "; ".join(problems))

    warnings = list(problems)  # если после всех попыток что-то осталось, не скрываем
    bad_numbers = unverified_numbers(card, product)
    if bad_numbers:
        warnings.append("Числа в тексте, которых нет во входных данных (проверьте): "
                        + ", ".join(bad_numbers))

    return {
        "product": {"name": product["name"], "manufacturer": product["manufacturer"] or NO_DATA},
        "seo_title": card.seo_title,
        "seo_description": card.seo_description,
        "characteristics": build_characteristics(product),
        "search_queries": card.search_queries,
        "commercial_block": asdict(card.commercial_block),
        "missing_data": missing + [m for m in card.missing_data if m not in missing],
        "warnings": warnings,
        "meta": {"provider": provider, "model": model, "attempts": attempts,
                 "title_len": len(card.seo_title), "description_len": len(card.seo_description)},
    }

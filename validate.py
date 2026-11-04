"""Проверки без участия LLM: вход, формат ответа, длины, подозрительные числа."""
import json
import re

from schema import (DESC_MAX, DESC_MIN, CommercialBlock, LLMCard, QUERIES_MAX,
                    QUERIES_MIN, TITLE_MAX)


class InputError(ValueError):
    """Вход непригоден для генерации. LLM в этом случае не вызывается."""


def _blank(v) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and not v) or \
        (isinstance(v, str) and not v.strip())


def load_input(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputError(f"Некорректный JSON: {e}") from e
    if not isinstance(data, dict):
        raise InputError("Ожидался JSON-объект с полями name, manufacturer, specs, description.")
    return data


def check_input(product: dict) -> tuple[dict, list[str]]:
    """Нормализует вход. Возвращает (товар, список отсутствующих полей)."""
    name = product.get("name")
    if not isinstance(name, str) or not name.strip():
        raise InputError("Поле 'name' отсутствует или пустое.")

    specs = product.get("specs")
    if specs is not None and not isinstance(specs, dict):
        raise InputError("Поле 'specs' должно быть объектом {характеристика: значение}.")
    specs = {str(k).strip(): v for k, v in (specs or {}).items() if str(k).strip()}

    clean = {
        "name": name.strip(),
        "manufacturer": (product.get("manufacturer") or "").strip()
        if isinstance(product.get("manufacturer"), (str, type(None))) else str(product["manufacturer"]),
        "specs": {k: ("" if v is None else str(v).strip()) for k, v in specs.items()},
        "description": (product.get("description") or "").strip()
        if isinstance(product.get("description"), (str, type(None))) else str(product["description"]),
    }

    missing = []
    if not clean["manufacturer"]:
        missing.append("manufacturer (производитель): данных нет")
    if not clean["specs"]:
        missing.append("specs (характеристики): данных нет")
    else:
        for k, v in clean["specs"].items():
            if not v:
                missing.append(f"specs.{k}: данных нет")
    if not clean["description"]:
        missing.append("description (описание/паспорт): данных нет")

    if not clean["specs"] and not clean["description"]:
        raise InputError("Нет ни характеристик, ни описания: генерировать карточку не из чего.")
    return clean, missing


def _str_list(value, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"Поле '{name}' должно быть списком строк.")
    return [x.strip() for x in value if x.strip()]


def parse_card(raw: str) -> LLMCard:
    """Достаёт JSON из ответа модели и валидирует структуру."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("В ответе нет JSON-объекта.")
    try:
        d = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Невалидный JSON в ответе: {e}") from e
    if not isinstance(d, dict):
        raise ValueError("Ответ должен быть JSON-объектом.")
    for key in ("seo_title", "seo_description"):
        if not isinstance(d.get(key), str):
            raise ValueError(f"Поле '{key}' отсутствует или не строка.")
    cb = d.get("commercial_block")
    if not isinstance(cb, dict):
        raise ValueError("Поле 'commercial_block' отсутствует или не объект.")
    return LLMCard(
        seo_title=d["seo_title"].strip(),
        seo_description=d["seo_description"].strip(),
        search_queries=_str_list(d.get("search_queries"), "search_queries"),
        commercial_block=CommercialBlock(
            suitable_for=_str_list(cb.get("suitable_for"), "suitable_for"),
            tasks=_str_list(cb.get("tasks"), "tasks")),
        missing_data=_str_list(d.get("missing_data"), "missing_data"),
    )


def card_problems(card: LLMCard) -> list[str]:
    """Нарушения жёстких требований ТЗ. Пустой список значит, что всё в порядке."""
    p = []
    if not card.seo_title.strip():
        p.append("seo_title пустой")
    elif len(card.seo_title) > TITLE_MAX:
        p.append(f"seo_title длиннее {TITLE_MAX} символов (сейчас {len(card.seo_title)})")
    n = len(card.seo_description)
    if not DESC_MIN <= n <= DESC_MAX:
        p.append(f"seo_description должен быть {DESC_MIN}–{DESC_MAX} символов (сейчас {n})")
    if not QUERIES_MIN <= len(card.search_queries) <= QUERIES_MAX:
        p.append(f"search_queries: нужно {QUERIES_MIN}–{QUERIES_MAX} запросов (сейчас {len(card.search_queries)})")
    return p


_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> set[str]:
    return {m.replace(",", ".") for m in _NUM.findall(text)}


def unverified_numbers(card: LLMCard, product: dict) -> list[str]:
    """Числа в текстах модели, которых нет во входных данных (возможная галлюцинация)."""
    source = _numbers(json.dumps(product, ensure_ascii=False))
    generated = " ".join([
        card.seo_title, card.seo_description, *card.search_queries,
        *card.commercial_block.suitable_for, *card.commercial_block.tasks,
    ])
    return sorted(_numbers(generated) - source)

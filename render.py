"""Вывод карточки в Markdown: удобно копировать контент-менеджеру."""


def to_markdown(card: dict) -> str:
    cb = card["commercial_block"]
    out = [f"# {card['seo_title']}", "",
           f"_Товар: {card['product']['name']} · {card['product']['manufacturer']}_", "",
           "## SEO-описание", "", card["seo_description"], "",
           "## Характеристики", "", "| Параметр | Значение |", "|---|---|"]
    out += [f"| {r['name']} | {r['value']} |" for r in card["characteristics"]]
    out += ["", "## Поисковые запросы", ""] + [f"- {q}" for q in card["search_queries"]]
    out += ["", "## Для менеджера", "", "**Кому подходит:**"]
    out += [f"- {x}" for x in cb["suitable_for"]] or ["- данных нет"]
    out += ["", "**Какие задачи решает:**"]
    out += [f"- {x}" for x in cb["tasks"]] or ["- данных нет"]
    if card["missing_data"]:
        out += ["", "## Требует уточнения (данных нет)", ""] + [f"- {m}" for m in card["missing_data"]]
    if card["warnings"]:
        out += ["", "## ⚠ Предупреждения проверки", ""] + [f"- {w}" for w in card["warnings"]]
    m = card["meta"]
    out += ["", "---", f"_Заголовок: {m['title_len']} симв., описание: {m['description_len']} симв. "
            f"· {m['provider']}/{m['model']} · попыток: {m['attempts']}_"]
    return "\n".join(out) + "\n"

"""Схемы данных: что просим у модели и ограничения из ТЗ."""
from dataclasses import dataclass, field


@dataclass
class CommercialBlock:
    suitable_for: list[str] = field(default_factory=list)  # кому подходит
    tasks: list[str] = field(default_factory=list)         # какие задачи решает


@dataclass
class LLMCard:
    """Только тексты. Таблицу характеристик собирает код, а не модель."""
    seo_title: str
    seo_description: str
    search_queries: list[str]
    commercial_block: CommercialBlock
    missing_data: list[str] = field(default_factory=list)


# Ограничения из ТЗ
TITLE_MAX = 70
DESC_MIN, DESC_MAX = 800, 1200
QUERIES_MIN, QUERIES_MAX = 3, 5
NO_DATA = "данных нет"

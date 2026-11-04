import json
import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import feed
import llm
from render import to_markdown
from service import generate_card

PRODUCT = json.loads((Path(__file__).parent.parent / "examples" / "demo_input.json").read_text(encoding="utf-8"))


def fake_answer(desc_len=900):
    return json.dumps({
        "seo_title": "Манометр показывающий DM 02 0–1,6 МПа",
        "seo_description": "а" * desc_len,
        "search_queries": ["манометр DM 02", "манометр 0-1,6 МПа", "манометр G1/2"],
        "commercial_block": {"suitable_for": ["Промышленные предприятия"], "tasks": ["Контроль давления"]},
        "missing_data": ["питание: данных нет"],
    }, ensure_ascii=False)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        os.environ["LLM_PROVIDER"] = "anthropic"

    def test_retry_then_success(self):
        answers = ["не json", fake_answer(100), fake_answer(900)]
        with mock.patch.object(llm, "generate", side_effect=answers) as g:
            card = generate_card(PRODUCT)
        self.assertEqual(g.call_count, 3)
        self.assertEqual(card["meta"]["attempts"], 3)
        self.assertEqual(card["warnings"], [])
        # feedback о нарушении попал в третий промпт
        self.assertIn("800", g.call_args_list[2].args[1])

    def test_gives_up_with_warning_when_length_never_fixed(self):
        with mock.patch.object(llm, "generate", return_value=fake_answer(100)):
            card = generate_card(PRODUCT)
        self.assertTrue(any("seo_description" in w for w in card["warnings"]))

    def test_llm_never_returns_json(self):
        with mock.patch.object(llm, "generate", return_value="sorry"):
            with self.assertRaises(llm.LLMError):
                generate_card(PRODUCT)

    def test_markdown_contains_all_blocks(self):
        with mock.patch.object(llm, "generate", return_value=fake_answer()):
            md = to_markdown(generate_card(PRODUCT))
        for part in ["SEO-описание", "Характеристики", "Поисковые запросы", "Для менеджера", "0–1,6 МПа"]:
            self.assertIn(part, md)


class FeedTests(unittest.TestCase):
    XML = """<yml_catalog><shop><offers>
    <offer id="7"><name>Манометр &amp; Ко</name><vendor>Завод</vendor>
    <description><![CDATA[<p>Для <b>давления</b></p>]]></description>
    <param name="Класс точности">1,5</param><param name="Диапазон" unit="МПа">0-1,6</param><param name="Пусто"></param>
    </offer></offers></shop></yml_catalog>"""

    def test_offer_conversion(self):
        p = feed.get_offer(ET.fromstring(self.XML), "7")
        self.assertEqual(p["manufacturer"], "Завод")
        self.assertEqual(p["description"], "Для давления")
        self.assertEqual(p["specs"], {"Класс точности": "1,5", "Диапазон": "0-1,6 МПа"})

    def test_unknown_offer(self):
        with self.assertRaises(KeyError):
            feed.get_offer(ET.fromstring(self.XML), "999")


if __name__ == "__main__":
    unittest.main()

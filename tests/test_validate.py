import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schema import CommercialBlock, LLMCard
from service import build_characteristics
from validate import (InputError, card_problems, check_input, load_input,
                      parse_card, unverified_numbers)

PRODUCT = {"name": "Манометр DM 02", "manufacturer": "Манотомь",
           "specs": {"диапазон измерений": "0–1,6 МПа", "класс точности": "1,5"},
           "description": "Для измерения давления."}


class ValidateTests(unittest.TestCase):
    def test_bad_json(self):
        with self.assertRaises(InputError):
            load_input("{not json")

    def test_not_object(self):
        with self.assertRaises(InputError):
            load_input("[1,2]")

    def test_no_name(self):
        with self.assertRaises(InputError):
            check_input({"specs": {"a": "1"}})

    def test_nothing_to_generate_from(self):
        with self.assertRaises(InputError):
            check_input({"name": "X", "specs": {}, "description": " "})

    def test_missing_fields_reported(self):
        _, missing = check_input({"name": "X", "specs": {"a": ""}, "description": "d"})
        self.assertTrue(any("manufacturer" in m for m in missing))
        self.assertTrue(any("specs.a" in m for m in missing))

    def test_characteristics_use_no_data_marker(self):
        p, _ = check_input({"name": "X", "specs": {"класс точности": ""}, "description": "d"})
        self.assertIn({"name": "класс точности", "value": "данных нет"}, build_characteristics(p))

    def test_parse_card_with_noise(self):
        data = {"seo_title": "t", "seo_description": "d", "search_queries": ["a", "b", "c"],
                "commercial_block": {"suitable_for": ["x"], "tasks": ["y"]}, "missing_data": []}
        self.assertEqual(parse_card("```json\n" + json.dumps(data) + "\n```").seo_title, "t")

    def test_parse_card_garbage(self):
        with self.assertRaises(ValueError):
            parse_card("извините, не могу")

    def test_parse_card_wrong_schema(self):
        with self.assertRaises(ValueError):
            parse_card('{"seo_title": 5}')

    def test_length_rules(self):
        card = LLMCard("т" * 71, "короткое", ["a"], CommercialBlock())
        self.assertEqual(len(card_problems(card)), 3)

    def test_unverified_numbers_detects_invented_value(self):
        card = LLMCard("Манометр 0–1,6 МПа", "Класс точности 1,5, до 250 °C.",
                       ["a", "b", "c"], CommercialBlock())
        self.assertEqual(unverified_numbers(card, PRODUCT), ["250"])


if __name__ == "__main__":
    unittest.main()

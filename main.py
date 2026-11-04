"""CLI: генерация черновика карточки товара.

Примеры:
  python main.py examples/demo_input.json
  python main.py --feed https://www.souz-pribor.ru/yml/any/feed.xml --list
  python main.py --feed feed.xml --offer-id 12345 --save-input examples/product_1.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

import feed
import llm
from render import to_markdown
from service import generate_card
from validate import InputError, load_input


def slug(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text.lower(), flags=re.UNICODE).strip("_")[:50] or "product"


def load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser(description="AI-помощник для карточек товаров")
    ap.add_argument("input", nargs="?", help="JSON-файл с товаром (или - для stdin)")
    ap.add_argument("--feed", help="URL или путь к YML-фиду")
    ap.add_argument("--list", action="store_true", help="показать первые товары фида")
    ap.add_argument("--offer-id", help="id товара в фиде")
    ap.add_argument("--save-input", help="сохранить товар из фида в JSON и выйти")
    ap.add_argument("--out", default="out", help="папка для результатов (по умолчанию out/)")
    args = ap.parse_args()

    try:
        if args.feed:
            root = feed.load_feed(args.feed)
            if args.list:
                for oid, name, n_params, desc_len in feed.list_offers(root):
                    print(f"{oid}\tпараметров: {n_params}\tописание: {desc_len} симв.\t{name}")
                return 0
            if not args.offer_id:
                ap.error("с --feed нужен --list или --offer-id")
            product = feed.get_offer(root, args.offer_id)
            if args.save_input:
                Path(args.save_input).write_text(
                    json.dumps(product, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Сохранено: {args.save_input}")
                return 0
        elif args.input:
            raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
            product = load_input(raw)
        else:
            ap.error("укажите JSON-файл или --feed")

        card = generate_card(product)
    except (InputError, KeyError) as e:
        print(f"Ошибка входных данных: {e}", file=sys.stderr)
        return 2
    except llm.LLMError as e:
        print(f"Ошибка LLM: {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"Ошибка чтения/сети: {e}", file=sys.stderr)
        return 4

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = slug(card["product"]["name"])
    (out / f"{base}.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(card)
    (out / f"{base}.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"[сохранено: {out / (base + '.json')}, {out / (base + '.md')}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

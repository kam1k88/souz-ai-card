"""Достаёт товары из YML-фида (Яндекс.Маркет формат) и приводит к входному JSON."""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET


def load_feed(source: str) -> ET.Element:
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    else:
        with open(source, "rb") as f:
            data = f.read()
    return ET.fromstring(data)


def _clean(text: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def offer_to_product(offer: ET.Element) -> dict:
    specs = {}
    for p in offer.findall("param"):
        key, val = (p.get("name") or "").strip(), _clean(p.text)
        if key and val:
            specs[key] = f"{val} {p.get('unit')}".strip() if p.get("unit") else val
    name = _clean(offer.findtext("name")) or " ".join(
        filter(None, [_clean(offer.findtext("typePrefix")), _clean(offer.findtext("model"))]))
    return {
        "name": name,
        "manufacturer": _clean(offer.findtext("vendor")),
        "specs": specs,
        "description": _clean(offer.findtext("description")),
    }


def list_offers(root: ET.Element, limit: int = 30):
    for i, o in enumerate(root.iter("offer")):
        if i >= limit:
            break
        yield o.get("id"), _clean(o.findtext("name")), len(o.findall("param")), len(_clean(o.findtext("description")))


def get_offer(root: ET.Element, offer_id: str) -> dict:
    for o in root.iter("offer"):
        if o.get("id") == str(offer_id):
            return offer_to_product(o)
    raise KeyError(f"Товар с id={offer_id} не найден в фиде.")

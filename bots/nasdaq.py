import io
from pathlib import Path
from typing import Optional, Sequence, List, Dict

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    from iris.decorators import *  # type: ignore
    from iris import ChatContext
except ModuleNotFoundError:  # pragma: no cover
    ChatContext = None  # type: ignore[misc,assignment]


CHART_URL = "https://ssl.pstatic.net/imgfinance/chart/mobile/world/mini/.IXIC_naverpc_l.png"
INFO_URL = "https://api.nasdaq.com/api/quote/COMP/info?assetclass=index"
SUMMARY_URL = "https://api.nasdaq.com/api/quote/COMP/summary?assetclass=index"
CHART_DATA_URL = "https://api.nasdaq.com/api/quote/COMP/chart?assetclass=index"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
}

FONT_PATH = Path("res") / "GmarketSansMedium.otf"
BACKGROUND_COLOR = "white"
POSITIVE_COLOR = (204, 24, 24)
NEGATIVE_COLOR = (24, 80, 196)
NEUTRAL_COLOR = (0, 0, 0)
INFO_HEIGHT = 190


def _load_font(size: int) -> ImageFont.ImageFont:
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


FONTS = {
    "title": _load_font(34),
    "subtitle": _load_font(30),
    "price": _load_font(26),
    "body": _load_font(22),
    "small": _load_font(18),
    "caption": _load_font(14),
    "fx_title": _load_font(26),
    "fx_currency": _load_font(18),
    "fx_price": _load_font(26),
}

DEFAULT_WIDTH = 480
FX_INFO_HEIGHT = 120
FX_CHART_URL = "https://ssl.pstatic.net/imgfinance/chart/mobile/marketindex/month3/FX_USDKRW_naverpc_l.png"


def _text_size(font: ImageFont.ImageFont, text: str) -> tuple[int, int]:
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    return font.getsize(text)


def _text_width(font: ImageFont.ImageFont, text: str) -> int:
    return _text_size(font, text)[0]


def _fetch_chart_image() -> Image.Image:
    response = requests.get(CHART_URL, timeout=5)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _fetch_json(url: str) -> dict:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=5)
    response.raise_for_status()
    payload = response.json()
    status = payload.get("status", {})
    if status.get("rCode") not in (None, 200):
        raise ValueError(f"Unexpected response code from {url}: {status}")
    return payload.get("data", {})


def _parse_float(text: str) -> float:
    cleaned = text.replace(",", "").replace("%", "").strip()
    if cleaned in {"", "--"}:
        raise ValueError(f"Cannot parse float from value '{text}'")
    return float(cleaned)


def _determine_color(indicator: str) -> tuple[int, int, int]:
    if indicator.lower() == "up":
        return POSITIVE_COLOR
    if indicator.lower() == "down":
        return NEGATIVE_COLOR
    return NEUTRAL_COLOR


def _fetch_market_data() -> dict:
    info = _fetch_json(INFO_URL)
    summary = _fetch_json(SUMMARY_URL)
    chart_payload = _fetch_json(CHART_DATA_URL)
    chart_points: Sequence[dict] = chart_payload.get("chart", [])

    if not info:
        raise ValueError("Missing info payload from Nasdaq API")
    if not summary:
        raise ValueError("Missing summary payload from Nasdaq API")

    primary = info.get("primaryData") or {}
    summary_data = summary.get("summaryData") or {}

    name = "NASDAQ"
    last_price_text = primary.get("lastSalePrice", "0")
    last_price = _parse_float(last_price_text)

    change_text = primary.get("netChange", "0")
    change_rate_text = primary.get("percentageChange", "0")
    indicator = primary.get("deltaIndicator", "")

    previous_close_text = summary_data.get("PreviousClose", {}).get("value", "0")
    high_text = summary_data.get("TodaysHigh", {}).get("value", "0")
    low_text = summary_data.get("TodaysLow", {}).get("value", "0")

    open_price: Optional[float] = None
    if chart_points:
        first_point = chart_points[0]
        open_price = float(first_point.get("y", 0.0))

    if open_price is None:
        # Fallback: use previous close as a best-effort approximation
        open_price = _parse_float(previous_close_text)

    return {
        "name": name,
        "price": last_price,
        "change_text": change_text,
        "change_rate_text": change_rate_text,
        "indicator": indicator,
        "previous_close": _parse_float(previous_close_text),
        "open": open_price,
        "high": _parse_float(high_text),
        "low": _parse_float(low_text),
    }


def _format_price(value: float) -> str:
    return f"{value:,.2f}"


def _fetch_usdkrw_chart() -> Image.Image:
    response = requests.get(FX_CHART_URL, timeout=5)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _fetch_usdkrw_data() -> Dict[str, float]:
    url = "https://api.stock.naver.com/marketindex/exchange?code=FX_USDKRW"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    payload = response.json()

    candidates: List[dict] = payload.get("normalList") or []
    for item in candidates:
        if item.get("exchangeCode") == "USD":
            price = _parse_float(item.get("closePrice", "0"))
            change = _parse_float(item.get("fluctuations", "0"))
            ratio = _parse_float(item.get("fluctuationsRatio", "0"))
            indicator = (item.get("fluctuationsType") or {}).get("code", "")
            return {
                "price": price,
                "change": change,
                "ratio": ratio,
                "indicator": indicator,
            }
    raise ValueError("USD/KRW data not found in response")


def _create_panel(chart_image: Image.Image, market: dict) -> Image.Image:
    title_x = 20
    title_y = 18
    padding_right = 20
    col_spacing = 12
    line_spacing = 28

    title_text = market["name"]

    price_text = _format_price(market["price"])
    change_text = f"{market['change_text']} ({market['change_rate_text']})"
    change_color = _determine_color(market["indicator"])

    info_rows = [
        ("시가", _format_price(market["open"])),
        ("고가", _format_price(market["high"])),
        ("저가", _format_price(market["low"])),
    ]

    label_width = max(_text_width(FONTS["small"], label) for label, _ in info_rows)
    value_width = max(_text_width(FONTS["small"], value) for _, value in info_rows)

    title_width, title_height = _text_size(FONTS["title"], title_text)
    price_width, price_height = _text_size(FONTS["price"], price_text)
    change_width, change_height = _text_size(FONTS["body"], change_text)

    label_x = title_x
    value_x = label_x + label_width + col_spacing
    change_x = title_x + price_width + 12

    content_right = max(
        title_x + title_width,
        title_x + price_width,
        change_x + change_width,
        value_x + value_width,
    )

    panel_width = max(
        title_x + chart_image.width + padding_right,
        content_right + padding_right,
    )
    panel_height = INFO_HEIGHT + chart_image.height
    panel = Image.new("RGB", (panel_width, panel_height), BACKGROUND_COLOR)
    chart_x = title_x
    panel.paste(chart_image, (chart_x, INFO_HEIGHT))

    draw = ImageDraw.Draw(panel)

    draw.text((title_x, title_y), title_text, font=FONTS["title"], fill=NEUTRAL_COLOR)

    price_y = title_y + title_height + 8
    draw.text((title_x, price_y), price_text, font=FONTS["price"], fill=change_color)

    change_y = price_y + price_height - change_height
    draw.text((change_x, change_y), change_text, font=FONTS["body"], fill=change_color)

    info_y_start = price_y + price_height + 12
    for idx, (label, value) in enumerate(info_rows):
        line_y = info_y_start + idx * line_spacing
        draw.text((label_x, line_y), label, font=FONTS["small"], fill=NEUTRAL_COLOR)
        draw.text((value_x, line_y), value, font=FONTS["small"], fill=NEUTRAL_COLOR)

    return panel


def _create_fx_panel(chart_image: Image.Image, fx: Dict[str, float]) -> Image.Image:
    title_x = 20
    title_y = 18
    padding_right = 20

    title_text = "환율"
    currency_text = "USD"
    price_text = f"{fx['price']:,.2f} KRW"
    change_text = f"{fx['change']:+,.2f} ({fx['ratio']:+.2f}%)"

    change_color = NEUTRAL_COLOR
    if fx["change"] > 0:
        change_color = POSITIVE_COLOR
    elif fx["change"] < 0:
        change_color = NEGATIVE_COLOR
    elif fx.get("indicator") == "2":
        change_color = POSITIVE_COLOR
    elif fx.get("indicator") == "5":
        change_color = NEGATIVE_COLOR

    title_width, title_height = _text_size(FONTS["fx_title"], title_text)
    currency_width, currency_height = _text_size(FONTS["fx_currency"], currency_text)
    price_width, price_height = _text_size(FONTS["fx_price"], price_text)
    change_width, change_height = _text_size(FONTS["body"], change_text)

    currency_x = title_x + title_width + 6
    content_right = max(
        currency_x + currency_width,
        title_x + price_width,
        title_x + change_width,
        title_x + chart_image.width,
    )

    panel_width = max(
        title_x + chart_image.width + padding_right,
        content_right + padding_right,
    )
    panel_height = FX_INFO_HEIGHT + chart_image.height + 36
    panel = Image.new("RGB", (panel_width, panel_height), BACKGROUND_COLOR)
    chart_x = title_x
    panel.paste(chart_image, (chart_x, FX_INFO_HEIGHT))

    draw = ImageDraw.Draw(panel)
    draw.text((title_x, title_y), title_text, font=FONTS["fx_title"], fill=NEUTRAL_COLOR)
    currency_y = title_y + max(0, title_height - currency_height)
    draw.text((currency_x, currency_y), currency_text, font=FONTS["fx_currency"], fill=NEUTRAL_COLOR)

    price_y = title_y + title_height + 8
    draw.text((title_x, price_y), price_text, font=FONTS["fx_price"], fill=NEUTRAL_COLOR)

    change_y = price_y + price_height + 6
    draw.text((title_x, change_y), change_text, font=FONTS["body"], fill=change_color)

    chart_label = "3개월 차트"
    label_x = title_x
    label_y = FX_INFO_HEIGHT + chart_image.height + 12
    draw.text((label_x, label_y), chart_label, font=FONTS["caption"], fill=NEUTRAL_COLOR)

    return panel


def _expand_panel(panel: Image.Image, width: int) -> Image.Image:
    if panel.width >= width:
        return panel
    expanded = Image.new("RGB", (width, panel.height), BACKGROUND_COLOR)
    expanded.paste(panel, (0, 0))
    return expanded


def _create_nasdaq_image() -> Image.Image:
    chart_image = _fetch_chart_image()
    market_data = _fetch_market_data()
    panels: List[Image.Image] = [_create_panel(chart_image, market_data)]

    try:
        fx = _fetch_usdkrw_data()
        fx_chart = _fetch_usdkrw_chart()
        panels.append(_create_fx_panel(fx_chart, fx))
    except Exception as exc:
        print(f"Failed to append USD/KRW panel: {exc}")

    width = max(panel.width for panel in panels)
    expanded = [_expand_panel(panel, width) for panel in panels]
    height = sum(panel.height for panel in expanded)

    combined = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    offset = 0
    for panel in expanded:
        combined.paste(panel, (0, offset))
        offset += panel.height
    return combined


def nasdaq(chat: Optional[ChatContext] = None):
    try:
        image = _create_nasdaq_image()
    except Exception as exc:
        print(f"Failed to create NASDAQ image: {exc}")
        return None

    if ChatContext is None or chat is None:
        return image

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return chat.reply_media([buffer])


if __name__ == "__main__":
    try:
        output_image = _create_nasdaq_image()
    except Exception as exc:
        print(f"Test run failed: {exc}")
    else:
        output_path = Path(__file__).with_name("nasdaq_preview.png")
        output_image.save(output_path, format="PNG")
        print(f"Preview image saved to: {output_path}")

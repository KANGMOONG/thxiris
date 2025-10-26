import io
from pathlib import Path
from typing import Optional, Sequence

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    from iris.decorators import *  # type: ignore
    from iris import ChatContext
except ModuleNotFoundError:  # pragma: no cover
    ChatContext = None  # type: ignore[misc,assignment]


INDEX_CODES: Sequence[str] = ("KOSPI", "KOSDAQ")
INDEX_LABELS = {
    "KOSPI": "코스피",
    "KOSDAQ": "코스닥",
}
CHART_URL = "https://ssl.pstatic.net/imgfinance/chart/mobile/mini/{code}_naverpc_l.png"
REALTIME_URL = "https://polling.finance.naver.com/api/realtime?query=SERVICE_INDEX:{code}"
FONT_PATH = Path("res") / "GmarketSansMedium.otf"

POSITIVE_COLOR = (204, 24, 24)
NEGATIVE_COLOR = (24, 80, 196)
NEUTRAL_COLOR = (0, 0, 0)
BACKGROUND_COLOR = "white"
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
    "price": _load_font(30),
    "code": _load_font(18),
    "body": _load_font(22),
    "small": _load_font(18),
}


def _text_size(font: ImageFont.ImageFont, text: str) -> tuple[int, int]:
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    return font.getsize(text)


def _text_width(font: ImageFont.ImageFont, text: str) -> int:
    return _text_size(font, text)[0]


def _fetch_chart_image(index_code: str) -> Image.Image:
    response = requests.get(CHART_URL.format(code=index_code), timeout=5)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _fetch_realtime_data(index_code: str) -> dict:
    response = requests.get(REALTIME_URL.format(code=index_code), timeout=5)
    response.raise_for_status()
    payload = response.json()
    areas = payload.get("result", {}).get("areas", [])
    datas = areas[0].get("datas") if areas else None
    if not datas:
        raise ValueError(f"No realtime data returned for {index_code}")
    return datas[0]


def _format_price(value: float) -> str:
    return f"{value:,.2f}"


def _format_amount(amount: int) -> str:
    return f"{amount / 1_000_000:,.2f}억"


def _create_index_panel(index_code: str, chart_image: Image.Image, stock_data: dict) -> Image.Image:
    title_x = 20
    title_y = 18
    padding_right = 24
    col_gap = 40
    col_spacing = 12
    line_spacing = 28

    title_text = INDEX_LABELS.get(index_code, index_code)
    code_text = stock_data.get("cd", index_code)

    price_value = stock_data.get("nv", 0) / 100
    change_value = stock_data.get("cv", 0) / 100
    change_rate = stock_data.get("cr", 0.0)
    change_flag = str(stock_data.get("rf", "0"))

    if change_flag == "2":
        change_symbol = "▲"
        change_color = POSITIVE_COLOR
    elif change_flag == "5":
        change_symbol = "▼"
        change_color = NEGATIVE_COLOR
    else:
        change_symbol = ""
        change_color = NEUTRAL_COLOR

    price_text = _format_price(price_value)
    if change_symbol:
        change_text = f"{change_symbol} {change_value:+,.2f} ({change_rate:+.2f}%)"
    else:
        change_text = f"{change_value:+,.2f} ({change_rate:+.2f}%)"

    info_rows = [
        (("시가", _format_price(stock_data.get("ov", 0) / 100)), ("거래량", f"{stock_data.get('aq', 0):,}천주")),
        (("고가", _format_price(stock_data.get("hv", 0) / 100)), ("거래대금", _format_amount(stock_data.get("aa", 0)))),
        (("저가", _format_price(stock_data.get("lv", 0) / 100)), None),
    ]

    label_col1_width = max(_text_width(FONTS["small"], row[0][0]) for row in info_rows)
    value_col1_width = max(_text_width(FONTS["small"], row[0][1]) for row in info_rows)
    label_col2_width = max((_text_width(FONTS["small"], row[1][0]) for row in info_rows if row[1]), default=0)
    value_col2_width = max((_text_width(FONTS["small"], row[1][1]) for row in info_rows if row[1]), default=0)

    title_width, title_height = _text_size(FONTS["title"], title_text)
    code_width, code_height = _text_size(FONTS["code"], code_text)
    price_width, price_height = _text_size(FONTS["price"], price_text)
    change_width, change_height = _text_size(FONTS["body"], change_text)

    label_col1_x = title_x
    value_col1_x = label_col1_x + label_col1_width + col_spacing
    if label_col2_width:
        label_col2_x = value_col1_x + value_col1_width + col_gap
        value_col2_x = label_col2_x + label_col2_width + col_spacing
    else:
        label_col2_x = 0
        value_col2_x = 0

    change_x = title_x + price_width + col_gap

    content_right = max(
        title_x + title_width + col_spacing + code_width,
        title_x + price_width,
        change_x + change_width,
        value_col1_x + value_col1_width,
        value_col2_x + value_col2_width if label_col2_width else value_col1_x + value_col1_width,
    )

    panel_width = max(chart_image.width, content_right + padding_right)
    panel_height = INFO_HEIGHT + chart_image.height
    panel = Image.new("RGB", (panel_width, panel_height), BACKGROUND_COLOR)
    chart_x = max((panel_width - chart_image.width) // 2, 0)
    panel.paste(chart_image, (chart_x, INFO_HEIGHT))

    draw = ImageDraw.Draw(panel)

    draw.text((title_x, title_y), title_text, font=FONTS["title"], fill=NEUTRAL_COLOR)
    code_x = title_x + title_width + col_spacing
    code_y = title_y + title_height - code_height
    draw.text((code_x, code_y), code_text, font=FONTS["code"], fill=NEUTRAL_COLOR)

    price_y = title_y + title_height + 8
    draw.text(
        (title_x, price_y),
        price_text,
        font=FONTS["price"],
        fill=change_color if change_symbol else NEUTRAL_COLOR,
    )

    change_y = price_y + price_height - change_height
    draw.text((change_x, change_y), change_text, font=FONTS["body"], fill=change_color)

    info_y_start = price_y + price_height + 12
    for idx, row in enumerate(info_rows):
        line_y = info_y_start + idx * line_spacing
        label1, value1 = row[0]
        draw.text((label_col1_x, line_y), label1, font=FONTS["small"], fill=NEUTRAL_COLOR)
        draw.text((value_col1_x, line_y), value1, font=FONTS["small"], fill=NEUTRAL_COLOR)
        if row[1]:
            label2, value2 = row[1]
            draw.text((label_col2_x, line_y), label2, font=FONTS["small"], fill=NEUTRAL_COLOR)
            draw.text((value_col2_x, line_y), value2, font=FONTS["small"], fill=NEUTRAL_COLOR)

    return panel


def _create_combined_image(index_codes: Sequence[str] = INDEX_CODES) -> Image.Image:
    panels = []
    for code in index_codes:
        chart_image = _fetch_chart_image(code)
        stock_data = _fetch_realtime_data(code)
        panels.append(_create_index_panel(code, chart_image, stock_data))

    width = max(panel.width for panel in panels)
    height = sum(panel.height for panel in panels)

    combined = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    offset = 0
    for panel in panels:
        x_offset = max((width - panel.width) // 2, 0)
        combined.paste(panel, (x_offset, offset))
        offset += panel.height
    return combined


def _normalize_indices(indices: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_code in indices:
        code = raw_code.upper()
        if code in INDEX_CODES and code not in seen:
            normalized.append(code)
            seen.add(code)
    return normalized


def kospidaq(chat: Optional[ChatContext], *indices: str):
    selected_indices = _normalize_indices(indices) if indices else list(INDEX_CODES)
    if not selected_indices:
        selected_indices = list(INDEX_CODES)
    try:
        combined_image = _create_combined_image(selected_indices)
    except Exception as exc:
        print(f"Failed to create KOSPI/KOSDAQ image: {exc}")
        return None

    if ChatContext is None or chat is None:
        return combined_image

    buffer = io.BytesIO()
    combined_image.save(buffer, format="PNG")
    buffer.seek(0)
    return chat.reply_media([buffer])


if __name__ == "__main__":
    try:
        output_image = _create_combined_image()
    except Exception as exc:
        print(f"Test run failed: {exc}")
    else:
        output_path = Path(__file__).with_name("kospidaq_preview.png")
        output_image.save(output_path, format="PNG")
        print(f"Preview image saved to: {output_path}")

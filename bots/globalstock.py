import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

def save_tsla_candle_chart_3mo(filename="tsla_3mo_chart.png"):
    # 폰트 경로 (상위 폴더 res 내 GmarketSansMedium.otf)
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'res', 'GmarketSansMedium.otf'))
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")

    font_prop = fm.FontProperties(fname=font_path)
    font_name = font_prop.get_name()

    plt.rcParams['font.family'] = font_name
    plt.rcParams['font.sans-serif'] = [font_name]
    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

    tsla = yf.Ticker("TSLA")
    data = tsla.history(period="3mo", interval="1d")
    if data.empty:
        raise ValueError("TSLA 데이터를 가져오지 못했습니다.")

    info = tsla.info
    exchange_raw = info.get('exchange', 'Unknown')
    exchange_map = {
        "NMS": "NASDAQ",
        "NYQ": "NYSE",
        "OTC": "OTC",
        "PNK": "OTC-PINK"
    }
    exchange_display = exchange_map.get(exchange_raw, exchange_raw)

    latest_close = data['Close'].iloc[-1]
    previous_close = data['Close'].iloc[-2]
    change = latest_close - previous_close
    change_pct = (change / previous_close) * 100

    stock_text = f"TSLA  |  {exchange_display}"
    price_label = "현재가: "
    price_value = f"${latest_close:.2f}"
    change_value = f"{abs(change):.2f} ({abs(change_pct):.2f}%)"

    price_color = 'red' if change >= 0 else 'blue'
    arrow = ' ▲' if change >= 0 else ' ▼'
    arrow_color = price_color

    mc = mpf.make_marketcolors(up='red', down='blue', edge='inherit', wick='inherit', volume='gray')
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='',
        facecolor='white',
        edgecolor='white'
    )

    fig, axes = mpf.plot(
        data,
        type='candle',
        style=style,
        ylabel='가격 ($)',
        volume=False,
        returnfig=True,
        figsize=(10, 4),
        title=''
    )

    # 차트 위치 약간 아래로 내리면서 왼쪽으로 더 붙이기 (x0값 줄임)
    for ax in fig.axes:
        pos = ax.get_position()
        ax.set_position([pos.x0 - 0.08, pos.y0 - 0.1, pos.width, pos.height])

    ax = axes[0]
    ax.set_ylabel("가격 ($)", fontproperties=font_prop)

    # 텍스트 위치 설정
    x_start = 0.01
    y_pos_first_line = 0.97
    y_pos_second_line = 0.82
    fontsize_first_line = 22
    fontsize_second_line = 20

    # 첫 줄: 종목명 + 거래소 (검정)
    fig.text(x_start, y_pos_first_line, stock_text, fontsize=fontsize_first_line,
             ha='left', va='top', color='black', fontproperties=font_prop)

    # 두 번째 줄: 현재가, 등락 수치 및 화살표
    fig.text(x_start, y_pos_second_line, price_label, fontsize=fontsize_second_line,
             ha='left', va='top', color='black', fontproperties=font_prop)

    x_price = x_start + 0.13
    fig.text(x_price, y_pos_second_line, price_value, fontsize=fontsize_second_line,
             ha='left', va='top', color=price_color, fontproperties=font_prop)

    x_arrow = x_price + 0.12
    fig.text(x_arrow, y_pos_second_line, arrow, fontsize=fontsize_second_line + 4,
             ha='left', va='top', color=arrow_color, fontproperties=font_prop)

    x_change_value = x_arrow + 0.04
    fig.text(x_change_value, y_pos_second_line, change_value, fontsize=fontsize_second_line,
             ha='left', va='top', color=price_color, fontproperties=font_prop)

    fig.savefig(filename, bbox_inches='tight', pad_inches=0.5)
    plt.close(fig)

    print(f"✅ TSLA 3개월 캔들 차트 '{filename}' 저장 완료!")

if __name__ == "__main__":
    save_tsla_candle_chart_3mo()

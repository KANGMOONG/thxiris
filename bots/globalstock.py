import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
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
    
    stock_text = "TSLA"
    exchange_text = f"  |  {exchange_display}"
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
        ylabel='($)',
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
    
    # y축을 오른쪽으로 이동
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_ylabel("($)", fontproperties=font_prop)
    
    # x축 라벨 삭제
    ax.set_xticklabels([])
    ax.set_xlabel('')
    
    # 텍스트 위치 설정
    x_start = 0.02
    y_pos_first_line = 0.90
    y_pos_second_line = 0.7  # 간격 줄임
    fontsize_ticker = 45  # TSLA 폰트 크기 (3포인트 증가)
    fontsize_exchange = 30  # 거래소 폰트 크기 (3포인트 증가)
    fontsize_second_line = 42
    fontsize_arrow_change = 33  # 화살표 및 등락수치 폰트 크기 (거래소와 동일)
    
    # 첫 줄: 종목명 (크게) + 거래소 (작게)
    fig.text(x_start, y_pos_first_line, stock_text, fontsize=fontsize_ticker,
             ha='left', va='bottom', color='black', fontproperties=font_prop)
    
    # 거래소명은 종목명 바로 옆에 작은 폰트로
    x_exchange = x_start + 0.17
    fig.text(x_exchange, y_pos_first_line, exchange_text, fontsize=fontsize_exchange,
             ha='left', va='bottom', color='black', fontproperties=font_prop)
    
    # 두 번째 줄: 현재가, 등락 수치 및 화살표
    fig.text(x_start, y_pos_second_line, price_value, fontsize=fontsize_second_line,
             ha='left', va='bottom', color=price_color, fontproperties=font_prop)
    
    x_arrow = x_start + 0.23
    fig.text(x_arrow, y_pos_second_line, arrow, fontsize=fontsize_arrow_change,
             ha='left', va='bottom', color=arrow_color, fontproperties=font_prop)
    
    x_change_value = x_arrow + 0.065
    fig.text(x_change_value, y_pos_second_line, change_value, fontsize=fontsize_arrow_change,
             ha='left', va='bottom', color=price_color, fontproperties=font_prop)
    
    fig.savefig(filename, bbox_inches='tight', pad_inches=0.2)
    plt.close(fig)
    print(f"✅ TSLA 3개월 캔들 차트 '{filename}' 저장 완료!")

if __name__ == "__main__":
    save_tsla_candle_chart_3mo()

import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm

def save_tsla_candle_chart_3mo(filename="tsla_3mo_chart.png"):
    # 한글 폰트 설정 (윈도우 예시)
    font_path = "C:/Windows/Fonts/malgun.ttf"  # 윈도우용, 환경에 맞게 변경하세요
    font_prop = fm.FontProperties(fname=font_path).get_name()
    plt.rcParams['font.family'] = font_prop

    # 데이터 가져오기
    tsla = yf.Ticker("TSLA")
    data = tsla.history(period="3mo", interval="1d")
    if data.empty:
        raise ValueError("데이터를 가져오지 못했습니다.")

    # 스타일 설정
    mc = mpf.make_marketcolors(up='red', down='blue', edge='inherit', wick='inherit', volume='gray')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='', facecolor='white', edgecolor='white')

    # 차트 생성
    fig, axes = mpf.plot(data, type='candle', style=style, title='TSLA 3-Month Candlestick Chart',
                         ylabel='Price ($)', volume=False, returnfig=True, figsize=(10,4))

    # 차트 아래로 내리기
    for ax in fig.axes:
        pos = ax.get_position()
        ax.set_position([pos.x0, pos.y0 - 0.1, pos.width, pos.height])

    ax = axes[0]  # 캔들 차트 x축

    # X축 틱 설정 - 매월 1일만
    month_start_locator = mdates.MonthLocator(bymonthday=1)
    ax.xaxis.set_major_locator(month_start_locator)

    # 한글 월일 포맷터
    def korean_date_formatter(x, pos=None):
        dt = mdates.num2date(x)
        return f"{dt.month}월{dt.day}일"

    ax.xaxis.set_major_formatter(plt.FuncFormatter(korean_date_formatter))

    # 틱 레이블 45도 회전
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    # 저장
    fig.savefig(filename, bbox_inches='tight', pad_inches=0.5)
    plt.close(fig)

    print(f"✅ TSLA 3개월 캔들 차트 '{filename}' 저장 완료!")

if __name__ == "__main__":
    save_tsla_candle_chart_3mo()

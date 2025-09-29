import yfinance as yf
import mplfinance as mpf

def save_tsla_candle_chart_3mo(filename="tsla_3mo_chart.png"):
    # 데이터 가져오기 (3개월치, 일봉)
    tsla = yf.Ticker("TSLA")
    data = tsla.history(period="3mo", interval="1d")
    
    if data.empty:
        raise ValueError("데이터를 가져오지 못했습니다.")
    
    # 차트 스타일 설정 (상승 빨강, 하락 파랑)
    mc = mpf.make_marketcolors(up='red', down='blue', edge='i', wick='i', volume='gray')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='-', gridcolor='lightgray')
    
    # 캔들 차트 생성 (거래량 없음)
    mpf.plot(
        data,
        type='candle',
        style=style,
        title='TSLA 3-Month Candlestick Chart',
        ylabel='Price ($)',
        volume=False,        # 거래량 표시 안함
        savefig=filename
    )
    
    print(f"TSLA 3개월 캔들 차트 '{filename}' 저장 완료!")

# 실행
if __name__ == "__main__":
    save_tsla_candle_chart_3mo()

import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from datetime import datetime
import mplfinance as mpf
import numpy as np

# 바이낸스 API에서 데이터 가져오기
def get_binance_data(symbol='WLDUSDT', interval='15m', limit=100):
    """
    바이낸스 API에서 캔들스틱 데이터 가져오기
    interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    """
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # 데이터프레임 생성
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # 데이터 타입 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    df.set_index('timestamp', inplace=True)
    
    return df

# 바이낸스 모바일 스타일 차트 생성
def create_binance_mobile_chart(df, symbol='WLDUSDT', save_path='binance_mobile_chart.png'):
    """
    바이낸스 모바일 스타일의 차트 생성 및 저장
    """
    # 바이낸스 모바일 컬러 스타일
    binance_colors = {
        'bg': '#1e2329',  # 배경색
        'bg_header': '#2b3139',  # 헤더 배경
        'candle_up': '#0ecb81',  # 상승 캔들
        'candle_down': '#f6465d',  # 하락 캔들
        'volume_up': '#0ecb8166',  # 상승 거래량 (투명도)
        'volume_down': '#f6465d66',  # 하락 거래량 (투명도)
        'ma7': '#f0b90b',  # MA7 (노랑)
        'ma25': '#e056fd',  # MA25 (핑크)
        'ma99': '#6761ea',  # MA99 (보라)
        'grid': '#2b313980',  # 그리드 (투명)
        'text': '#848e9c',  # 회색 텍스트
        'text_light': '#b7bdc6',  # 밝은 회색
        'text_white': '#eaecef',  # 흰색
    }
    
    # MA 계산
    df['MA7'] = df['close'].rolling(window=7).mean()
    df['MA25'] = df['close'].rolling(window=25).mean()
    df['MA99'] = df['close'].rolling(window=99).mean()
    
    # 가격 정보 계산
    current_price = df['close'].iloc[-1]
    open_price = df['open'].iloc[0]
    price_change = current_price - open_price
    price_change_pct = (price_change / open_price) * 100
    
    high_24h = df['high'].max()
    low_24h = df['low'].min()
    volume_wld = df['volume'].sum()
    volume_usdt = (df['volume'] * df['close']).sum()
    
    # 가격 변동에 따른 색상
    price_color = binance_colors['candle_up'] if price_change >= 0 else binance_colors['candle_down']
    
    # 스타일 설정
    mc = mpf.make_marketcolors(
        up=binance_colors['candle_up'],
        down=binance_colors['candle_down'],
        edge='inherit',
        wick={'up': binance_colors['candle_up'], 'down': binance_colors['candle_down']},
        volume={'up': binance_colors['candle_up'], 'down': binance_colors['candle_down']},
        alpha=0.8,
    )
    
    s = mpf.make_mpf_style(
        marketcolors=mc,
        figcolor=binance_colors['bg'],
        facecolor=binance_colors['bg'],
        gridcolor=binance_colors['grid'],
        gridstyle=':',
        gridaxis='both',
        y_on_right=True,
        rc={
            'font.size': 8,
            'axes.labelcolor': binance_colors['text'],
            'xtick.color': binance_colors['text'],
            'ytick.color': binance_colors['text'],
            'axes.edgecolor': binance_colors['bg'],
        }
    )
    
    # 이동평균선 추가
    apds = [
        mpf.make_addplot(df['MA7'], color=binance_colors['ma7'], width=2),
        mpf.make_addplot(df['MA25'], color=binance_colors['ma25'], width=2),
        mpf.make_addplot(df['MA99'], color=binance_colors['ma99'], width=2),
    ]
    
    # 차트 생성 (모바일 비율)
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=s,
        volume=True,
        addplot=apds,
        figsize=(7.5, 13),
        panel_ratios=(5, 1),
        datetime_format='%H:%M',
        xrotation=0,
        returnfig=True,
        ylabel='',
        ylabel_lower='',
        tight_layout=False,
    )
    
    # 여백 조정
    plt.subplots_adjust(top=0.85, bottom=0.06, left=0.01, right=0.87)
    
    # 배경 사각형 추가 (전체)
    fig.patch.set_facecolor(binance_colors['bg'])
    
    # === 헤더 영역 (상단 정보) ===
    header_ax = fig.add_axes([0, 0.86, 1, 0.14])
    header_ax.set_xlim(0, 100)
    header_ax.set_ylim(0, 100)
    header_ax.axis('off')
    header_ax.set_facecolor(binance_colors['bg'])
    
    # 종목명
    symbol_display = f"{symbol[:3]}/{symbol[3:]}"
    header_ax.text(5, 90, symbol_display, fontsize=14, color=binance_colors['text_light'], 
                   va='top', weight='normal')
    
    # 현재가 (대형)
    header_ax.text(5, 75, f'{current_price:.3f}', fontsize=36, color=binance_colors['text_white'], 
                   va='top', weight='bold')
    
    # 달러 표시
    header_ax.text(5, 42, f'${current_price:.2f}', fontsize=13, color=binance_colors['text'], 
                   va='top')
    
    # 변동액 및 변동률
    change_sign = '' if price_change < 0 else '+'
    header_ax.text(5, 28, f'{change_sign}{price_change:.3f} {change_sign}{price_change_pct:.2f}%', 
                   fontsize=13, color=price_color, va='top', weight='bold')
    
    # AI 태그
    header_ax.text(5, 8, 'AI', fontsize=12, color=binance_colors['ma7'], 
                   va='top', weight='bold')
    
    # 우측 정보 컬럼
    # 24h High
    header_ax.text(62, 88, '24h High', fontsize=9.5, color=binance_colors['text'], va='top')
    header_ax.text(62, 77, f'{high_24h:.3f}', fontsize=12, color=binance_colors['text_light'], 
                   va='top', weight='bold')
    
    # 24h Vol(WLD)
    header_ax.text(62, 62, '24h Vol(WLD)', fontsize=9.5, color=binance_colors['text'], va='top')
    header_ax.text(62, 51, f'{volume_wld/1000000:.2f}M', fontsize=12, 
                   color=binance_colors['text_light'], va='top', weight='bold')
    
    # 24h Low
    header_ax.text(62, 36, '24h Low', fontsize=9.5, color=binance_colors['text'], va='top')
    header_ax.text(62, 25, f'{low_24h:.3f}', fontsize=12, color=binance_colors['text_light'], 
                   va='top', weight='bold')
    
    # 24h Vol(USDT)
    header_ax.text(62, 10, '24h Vol(USDT)', fontsize=9.5, color=binance_colors['text'], va='top')
    header_ax.text(62, -1, f'{volume_usdt/1000000:.2f}M', fontsize=12, 
                   color=binance_colors['text_light'], va='top', weight='bold')
    
    # === Time 탭 영역 ===
    time_ax = fig.add_axes([0, 0.818, 1, 0.035])
    time_ax.set_xlim(0, 100)
    time_ax.set_ylim(0, 10)
    time_ax.axis('off')
    time_ax.set_facecolor(binance_colors['bg'])
    
    # Time 탭들
    time_ax.text(4, 5, 'Time', fontsize=10, color=binance_colors['text'], va='center')
    time_ax.text(16, 5, '15m', fontsize=11, color=binance_colors['text_white'], 
                 va='center', weight='bold')
    time_ax.text(25, 5, '1h', fontsize=10, color=binance_colors['text'], va='center')
    time_ax.text(31, 5, '4h', fontsize=10, color=binance_colors['text'], va='center')
    time_ax.text(37, 5, '1D', fontsize=10, color=binance_colors['text'], va='center')
    time_ax.text(44, 5, 'More ▼', fontsize=10, color=binance_colors['text'], va='center')
    time_ax.text(62, 5, 'Depth', fontsize=10, color=binance_colors['text'], va='center')
    
    # === MA 정보 라인 ===
    ma_ax = fig.add_axes([0, 0.788, 1, 0.028])
    ma_ax.set_xlim(0, 100)
    ma_ax.set_ylim(0, 10)
    ma_ax.axis('off')
    ma_ax.set_facecolor(binance_colors['bg'])
    
    ma7_val = df['MA7'].iloc[-1]
    ma25_val = df['MA25'].iloc[-1]
    ma99_val = df['MA99'].iloc[-1]
    
    ma_ax.text(4, 5, f'MA(7): {ma7_val:.3f}', fontsize=10.5, 
               color=binance_colors['ma7'], va='center', weight='bold')
    ma_ax.text(27, 5, f'MA(25): {ma25_val:.3f}', fontsize=10.5, 
               color=binance_colors['ma25'], va='center', weight='bold')
    ma_ax.text(52, 5, f'MA(99): {ma99_val:.3f}', fontsize=10.5, 
               color=binance_colors['ma99'], va='center', weight='bold')
    
    # === 거래량 MA 정보 ===
    vol_ma_ax = fig.add_axes([0, 0.185, 1, 0.022])
    vol_ma_ax.set_xlim(0, 100)
    vol_ma_ax.set_ylim(0, 10)
    vol_ma_ax.axis('off')
    vol_ma_ax.set_facecolor(binance_colors['bg'])
    
    vol_current = df['volume'].iloc[-1]
    vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
    vol_ma10 = df['volume'].rolling(10).mean().iloc[-1]
    
    vol_ma_ax.text(4, 5, f'Vol: {vol_current/1000:.1f}K', fontsize=9.5, 
                   color=binance_colors['text_light'], va='center', weight='bold')
    vol_ma_ax.text(23, 5, f'MA(5): {vol_ma5/1000:.1f}K', fontsize=9.5, 
                   color=binance_colors['ma7'], va='center', weight='bold')
    vol_ma_ax.text(48, 5, f'MA(10): {vol_ma10/1000:.1f}K', fontsize=9.5, 
                   color=binance_colors['ma99'], va='center', weight='bold')
    
    # 거래량 차트 투명도 조정
    axes[1].set_alpha(0.6)
    
    # 차트 저장
    plt.savefig(save_path, dpi=160, facecolor=binance_colors['bg'], 
                edgecolor='none', bbox_inches='tight', pad_inches=0.2)
    print(f"✅ 모바일 차트가 '{save_path}'에 저장되었습니다.")
    plt.close()
    
    return fig

# 메인 실행
if __name__ == "__main__":
    # 설정
    SYMBOL = 'WLDUSDT'  # 코인 심볼
    INTERVAL = '15m'     # 15분봉
    LIMIT = 100          # 가져올 캔들 개수
    
    print(f"📊 {SYMBOL} {INTERVAL} 데이터 가져오는 중...")
    df = get_binance_data(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)
    
    print("🎨 모바일 차트 생성 중...")
    create_binance_mobile_chart(df, symbol=SYMBOL, save_path='wld_binance_mobile.png')
    
    # 최신 가격 정보 출력
    print(f"\n=== 💰 {SYMBOL} 최신 정보 ===")
    print(f"현재가: ${df['close'].iloc[-1]:.4f}")
    print(f"24h 최고: ${df['high'].max():.4f}")
    print(f"24h 최저: ${df['low'].min():.4f}")
    print(f"24h 거래량(WLD): {df['volume'].sum()/1000000:.2f}M")
    print(f"24h 거래량(USDT): {(df['volume'] * df['close']).sum()/1000000:.2f}M")
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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

# 바이낸스 스타일 차트 생성
def create_binance_style_chart(df, symbol='WLD/USDT', save_path='binance_chart.png'):
    """
    바이낸스 스타일의 차트 생성 및 저장
    """
    # 바이낸스 컬러 스타일
    binance_colors = {
        'bg': '#181a20',  # 배경색
        'candle_up': '#0ecb81',  # 상승 캔들 (초록)
        'candle_down': '#f6465d',  # 하락 캔들 (빨강)
        'wick': '#181a20',  # 심지 색
        'volume_up': '#0ecb81',  # 상승 거래량
        'volume_down': '#f6465d',  # 하락 거래량
        'ma_line': '#f0b90b',  # 이동평균선 (노랑)
        'grid': '#2b3139',  # 그리드
        'text': '#848e9c',  # 텍스트
        'text_light': '#b7bdc6',  # 밝은 텍스트
        'text_white': '#eaecef',  # 흰색 텍스트
    }
    
    # MA 계산
    df['MA7'] = df['close'].rolling(window=7).mean()
    df['MA25'] = df['close'].rolling(window=25).mean()
    df['MA99'] = df['close'].rolling(window=99).mean()
    
    # 스타일 설정
    mc = mpf.make_marketcolors(
        up=binance_colors['candle_up'],
        down=binance_colors['candle_down'],
        edge='inherit',
        wick={'up': binance_colors['candle_up'], 'down': binance_colors['candle_down']},
        volume={'up': binance_colors['volume_up'], 'down': binance_colors['volume_down']},
    )
    
    s = mpf.make_mpf_style(
        marketcolors=mc,
        figcolor=binance_colors['bg'],
        facecolor=binance_colors['bg'],
        gridcolor=binance_colors['grid'],
        gridstyle='-',
        y_on_right=True,
        rc={
            'font.size': 10,
            'axes.labelcolor': binance_colors['text'],
            'xtick.color': binance_colors['text'],
            'ytick.color': binance_colors['text'],
            'axes.edgecolor': binance_colors['grid'],
        }
    )
    
    # 이동평균선 추가
    apds = [
        mpf.make_addplot(df['MA7'], color='#f0b90b', width=1),
        mpf.make_addplot(df['MA25'], color='#e056fd', width=1),
        mpf.make_addplot(df['MA99'], color='#6761ea', width=1),
    ]
    
    # 차트 생성
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=s,
        volume=True,
        addplot=apds,
        figsize=(16, 9),
        panel_ratios=(3, 1),
        datetime_format='%H:%M',
        xrotation=0,
        returnfig=True,
        ylabel='',
        ylabel_lower='',
    )
    
    # 상단 여백 조정 (종목 정보 공간 확보)
    plt.subplots_adjust(top=0.90)
    
    # 현재 가격 정보 계산
    current_price = df['close'].iloc[-1]
    price_change = df['close'].iloc[-1] - df['open'].iloc[0]  # 24시간 기준
    price_change_pct = (price_change / df['open'].iloc[0]) * 100
    
    high_24h = df['high'].max()
    low_24h = df['low'].min()
    volume_wld = df['volume'].sum()
    volume_usdt = (df['volume'] * df['close']).sum()
    
    # 가격 변동에 따른 색상
    price_color = binance_colors['candle_up'] if price_change >= 0 else binance_colors['candle_down']
    
    # 종목 정보 바 생성 (차트 상단)
    fig_width = fig.get_figwidth()
    info_bar = fig.add_axes([0, 0.91, 1, 0.09])  # [left, bottom, width, height]
    info_bar.set_xlim(0, 100)
    info_bar.set_ylim(0, 1)
    info_bar.axis('off')
    info_bar.set_facecolor(binance_colors['bg'])
    
    # 종목명과 현재가 (큰 글씨)
    symbol_display = symbol.replace('/', '/')
    info_bar.text(2, 0.5, f'{symbol_display}', fontsize=18, color=binance_colors['text_white'], 
                  weight='bold', va='center')
    
    info_bar.text(15, 0.5, f'{current_price:.3f}', fontsize=20, color=price_color, 
                  weight='bold', va='center')
    
    # Worldcoin Price 텍스트 (작은 글씨)
    info_bar.text(2, 0.15, 'Worldcoin Price', fontsize=9, color=binance_colors['text'], va='center')
    
    # 달러 표시 (작은 글씨)
    info_bar.text(15, 0.15, f'${current_price:.2f}', fontsize=9, color=binance_colors['text'], va='center')
    
    # 24h 변동 (변동액과 변동률)
    change_sign = '+' if price_change >= 0 else ''
    info_bar.text(28, 0.65, '24h Chg', fontsize=9, color=binance_colors['text'], va='center')
    info_bar.text(28, 0.35, f'{change_sign}{price_change:.3f} {change_sign}{price_change_pct:.2f}%', 
                  fontsize=11, color=price_color, weight='bold', va='center')
    
    # 24h High
    info_bar.text(40, 0.65, '24h High', fontsize=9, color=binance_colors['text'], va='center')
    info_bar.text(40, 0.35, f'{high_24h:.3f}', fontsize=11, color=binance_colors['text_light'], 
                  weight='bold', va='center')
    
    # 24h Low
    info_bar.text(48, 0.65, '24h Low', fontsize=9, color=binance_colors['text'], va='center')
    info_bar.text(48, 0.35, f'{low_24h:.3f}', fontsize=11, color=binance_colors['text_light'], 
                  weight='bold', va='center')
    
    # 24h Volume(WLD)
    info_bar.text(56, 0.65, '24h Volume(WLD)', fontsize=9, color=binance_colors['text'], va='center')
    info_bar.text(56, 0.35, f'{volume_wld:,.2f}', fontsize=11, color=binance_colors['text_light'], 
                  weight='bold', va='center')
    
    # 24h Volume(USDT)
    info_bar.text(70, 0.65, '24h Volume(USDT)', fontsize=9, color=binance_colors['text'], va='center')
    info_bar.text(70, 0.35, f'{volume_usdt:,.2f}', fontsize=11, color=binance_colors['text_light'], 
                  weight='bold', va='center')
    
    # Token Tags
    info_bar.text(85, 0.65, 'Token Tags', fontsize=9, color=binance_colors['text'], va='center')
    info_bar.text(85, 0.35, 'AI  Infrastructure', fontsize=10, color=binance_colors['ma_line'], 
                  weight='bold', va='center')
    # MA 정보 추가 (차트 내부 왼쪽 상단)
    ma_text = f"MA(7): {df['MA7'].iloc[-1]:.3f}  MA(25): {df['MA25'].iloc[-1]:.3f}  MA(99): {df['MA99'].iloc[-1]:.3f}"
    axes[0].text(
        0.01, 0.97, ma_text,
        transform=axes[0].transAxes,
        fontsize=10,
        verticalalignment='top',
        color=binance_colors['text'],
        bbox=dict(boxstyle='round', facecolor=binance_colors['bg'], alpha=0.8, edgecolor='none')
    )
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, facecolor=binance_colors['bg'], edgecolor='none')
    print(f"차트가 '{save_path}'에 저장되었습니다.")
    
    return fig

# 메인 실행
if __name__ == "__main__":
    # 설정
    SYMBOL = 'WLDUSDT'  # 코인 심볼
    INTERVAL = '15m'     # 15분봉
    LIMIT = 100          # 가져올 캔들 개수
    
    print(f"{SYMBOL} {INTERVAL} 데이터 가져오는 중...")
    df = get_binance_data(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)
    
    print("차트 생성 중...")
    create_binance_style_chart(df, symbol='WLD/USDT', save_path='wld_binance_chart.png')
    
    # 최신 가격 정보 출력
    print(f"\n=== {SYMBOL} 최신 정보 ===")
    print(f"현재가: ${df['close'].iloc[-1]:.4f}")
    print(f"24h 최고: ${df['high'].max():.4f}")
    print(f"24h 최저: ${df['low'].min():.4f}")
    print(f"24h 거래량: {df['volume'].sum():,.2f}")
    print(f"MA(7): {df['close'].rolling(7).mean().iloc[-1]:.4f}")
    print(f"MA(25): {df['close'].rolling(25).mean().iloc[-1]:.4f}")
    print(f"MA(99): {df['close'].rolling(99).mean().iloc[-1]:.4f}")
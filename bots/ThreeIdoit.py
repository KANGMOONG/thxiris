import requests
import datetime
import pytz
from types import SimpleNamespace
from iris import ChatContext, PyKV

all_url = "https://api.upbit.com/v1/market/all"
base_url = "https://api.upbit.com/v1/ticker?markets="
currency_url = "https://m.search.naver.com/p/csearch/content/qapirender.nhn?key=calculator&pkid=141&q=%ED%99%98%EC%9C%A8&where=m&u1=keb&u6=standardUnit&u7=0&u3=USD&u4=KRW&u8=down&u2=1"
binance_url = "https://api.binance.com/api/v3/ticker/"

def get_coin_info(chat: ChatContext):
    match chat.message.command:
        case "!병림픽":
            if chat.message.has_param:
                Threeidiots(chat)
            else:
                Threeidiots(chat)


def get_upbit(chat: ChatContext):
    kv = PyKV()
    query = chat.message.msg
    res = requests.get(base_url + 'KRW-' + query)
    if 'error' in res.text:
        try:
            result_json, query = get_upbit_korean(query)
        except:
            chat.reply("검색된 코인이 없습니다.")
            return None

    else:
        result_json = res.json()[0]
    
    price = result_json['trade_price']
    change = result_json['signed_change_rate']*100
    if price % 1 == 0:
        price = int(price)
    
    result = query + f'     {price:,}원  {change:,.2f}%'
    try:
        user_coin_info = kv.get(f"coin.{str(chat.sender.id)}")[query]
        amount = user_coin_info["amount"]
        average = user_coin_info["average"]
        seed = average*amount
        total = round(result_json['trade_price']*amount,0)
        percent = round((total/seed-1)*100,1)
        plus_mark = "+" if percent > 0 else ""
        result += f'\n총평가금액 : {total:,.0f}원({plus_mark}{percent:,.1f}%)\n총매수금액 : {seed:,.0f}원\n보유수량 : {amount:,.0f}개\n평균단가 : {average:,}원'
    except:
        pass        
    #chat.reply(result)
    return result

def get_upbit2(chat: ChatContext):
    kv = PyKV()
    query = chat.message.msg
    res = requests.get(base_url + 'KRW-' + query)
    if 'error' in res.text:
        try:
            result_json, query = get_upbit_korean(query)
        except:
            chat.reply("검색된 코인이 없습니다.")
            return None

    else:
        result_json = res.json()[0]
    
    price = result_json['trade_price']
    change = result_json['signed_change_rate']*100
    if price % 1 == 0:
        price = int(price)
    
    result = query + f'   {price:,}원  {change:,.2f}%'
    try:
        user_coin_info = kv.get(f"coin.{str(chat.sender.id)}")[query]
        amount = user_coin_info["amount"]
        average = user_coin_info["average"]
        seed = average*amount
        total = round(result_json['trade_price']*amount,0)
        percent = round((total/seed-1)*100,1)
        plus_mark = "+" if percent > 0 else ""
        result += f'\n총평가금액 : {total:,.0f}원({plus_mark}{percent:,.1f}%)\n총매수금액 : {seed:,.0f}원\n보유수량 : {amount:,.0f}개\n평균단가 : {average:,}원'
    except:
        pass        
    #chat.reply(result)
    return result

def get_upbit3(chat: ChatContext):
    kv = PyKV()
    query = chat.message.msg
    res = requests.get(base_url + 'KRW-' + query)
    if 'error' in res.text:
        try:
            result_json, query = get_upbit_korean(query)
        except:
            chat.reply("검색된 코인이 없습니다.")
            return None

    else:
        result_json = res.json()[0]
    
    price = result_json['trade_price']
    change = result_json['signed_change_rate']*100
    if price % 1 == 0:
        price = int(price)
    
    result = query + f' {price:,}원  {change:,.2f}%'
    try:
        user_coin_info = kv.get(f"coin.{str(chat.sender.id)}")[query]
        amount = user_coin_info["amount"]
        average = user_coin_info["average"]
        seed = average*amount
        total = round(result_json['trade_price']*amount,0)
        percent = round((total/seed-1)*100,1)
        plus_mark = "+" if percent > 0 else ""
        result += f'\n총평가금액 : {total:,.0f}원({plus_mark}{percent:,.1f}%)\n총매수금액 : {seed:,.0f}원\n보유수량 : {amount:,.0f}개\n평균단가 : {average:,}원'
    except:
        pass        
    #chat.reply(result)
    return result
    
def get_upbit_all(chat: ChatContext):
    res = requests.get(all_url)
    krw_coins = []
    for market in res.json():
        if 'KRW' in market['market']:
            krw_coins.append(market['market'])

    res = requests.get(base_url + ','.join(krw_coins))
    
    result_list = []
    coins = {}
    result_list.append('업비트 원화시세\n' + '\u200b'*500)

    for coin in res.json():
        coins[coin['market'][4:]] = {'price' : coin['trade_price'], 'change' : coin['signed_change_rate']*100}
    coin_list = sorted(coins.items(),key = lambda x: x[1]['change'],reverse=True)
    
    for item in coin_list:
        to_append = f'{item[0]}\n현재가 : {item[1]["price"]} 원\n등락률 : {item[1]["change"]:.2f} %'
        result_list.append(to_append)
    result = '\n\n'.join(result_list)
    
    chat.reply(result)

def get_upbit_korean(query):
    res_eng_query = requests.get(all_url)
    for market in res_eng_query.json():
        if 'KRW' in market['market'] and query in market['korean_name']:
            eng_query = market['market']
            if query == market['korean_name']:
                break

    res = requests.get(base_url + eng_query)
    return (res.json()[0],eng_query[4:])


def get_binance(chat: ChatContext):
    try:
        query = chat.message.param.upper()
        query_split = query.split("/")
        query = "".join(query_split)
        currency = get_USDKRW()
        r = requests.get(binance_url+'24hr').json()
        is_USDT = query_split[1] in ["USDT", "BUSD", "USDC"]
        for coin in r:
            if coin['symbol'] == 'BTCUSDT':
                BTCUSDT = float(coin['lastPrice'])
                if query == 'BTCUSDT':
                    price = BTCUSDT
                    change = float(coin['priceChangePercent'])
            elif coin['symbol'] == query:
                price = float(coin['lastPrice'])
                change = float(coin['priceChangePercent'])
            elif coin['symbol'] == query_split[1]+'USDT':
                to_USDT = float(coin['lastPrice'])
        if not is_USDT:
            price = price*to_USDT
        BTCKRW = requests.get(base_url + "KRW-BTC").json()[0]["trade_price"]
        query_KRW = price*currency
        query_KRW_kimp = (BTCKRW/(BTCUSDT*currency))*query_KRW
        res = f'{query}\nUSD : ${price:,f}\nKRW : ￦{query_KRW:,.2f}\nKRW(김프) : ￦{query_KRW_kimp:,.2f}\n등락률 : {change:+.2f}%\n환율 : ￦{currency:,.0f}'
        chat.reply(res)
    except Exception as e:
        print(e)
        chat.reply('코인이 정확하지 않거나 오류가 발생하였습니다. 코인심볼과 화폐단위를 함께 적어주세요. 예시 : BTC/USDT, ETC/USDT, IQ/BNB')



def Threeidiots(chat: ChatContext):
    chat.message.msg='WLD'
    result1=get_upbit(chat)
    chat.message.msg='ONDO'
    result2=get_upbit2(chat)
    chat.message.msg='VIRTUAL'
    result3=get_upbit3(chat)
    print(result1+'\n')
    print(result2)
    print(result3)
    chat.reply(result1+'\n'+result2+'\n'+result3)

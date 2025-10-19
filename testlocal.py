import requests


def get_bithumb(val):
    val=val.upper()
    val="KRW-"+val

    all_url = "https://api.bithumb.com/v1/market/all?isDetails=false"
    price_url = f"https://api.bithumb.com/v1/ticker?markets={val}"
    headers = {"accept": "application/json"}

    code_response = requests.get(all_url, headers=headers)
    code_data = code_response.json()

    price_response = requests.get(price_url, headers=headers)
    price_data = price_response.json()

    
    korean_name = next((c["korean_name"] for c in code_data if c["market"] == val), None)
    

    text = f"{korean_name} {price_data[0]['trade_price']:,}원 {price_data[0]['change_rate']*100:.2f}%"


    print(text) 
    


if __name__ == "__main__":
    get_bithumb("agi")
    get_bithumb("wld")
    get_bithumb("arkm")


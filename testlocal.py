#from bots.gpt_url_summary import url_summary
from bots.gpt_url_summary_test import url_summary
from bots.stocktest import kospidaq
from bots.favoritecoin import favorite_coin_info

def main():
    print("🔁 반복 테스트 모드입니다. 'exit' 입력 시 종료됩니다.")
    while True:
        #testinput = input("\n✅ 테스트 인풋을 입력하세요: ")
        """
        if testinput.lower() in ["exit", "quit"]:
            print("👋 테스트를 종료합니다.")
            break
        """

            favorite_coin_info(testinput)
            #print(f"📄 출력 결과:\n{testoutput}")
        except Exception as e:
            print(f"❌ 에러 발생: {e}")


if __name__ == "__main__":
    main()


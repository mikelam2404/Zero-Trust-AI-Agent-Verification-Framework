import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from eth_account.messages import encode_defunct
from openai import OpenAI
import hashlib
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")
SERVER_PRIVATE_KEY = os.getenv("SERVER_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

if not SERVER_PRIVATE_KEY or not CONTRACT_ADDRESS:
    raise ValueError("環境變數缺失！請確認 .env 檔案配置。")

w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
if not w3.is_connected():
    raise RuntimeError("無法連線至 Sepolia 節點，請檢查 RPC URL")

SERVER_ADDRESS = w3.eth.account.from_key(SERVER_PRIVATE_KEY).address
CHAIN_ID = 11155111

CONTRACT_ABI = [
  {"inputs": [{"internalType": "bytes32","name": "promptHash","type": "bytes32"},{"internalType": "bytes32","name": "outputHash","type": "bytes32"}],"name": "recordTask","outputs": [],"stateMutability": "nonpayable","type": "function"},
  {"anonymous": False,"inputs": [{"indexed": True,"internalType": "bytes32","name": "promptHash","type": "bytes32"},{"indexed": True,"internalType": "bytes32","name": "outputHash","type": "bytes32"},{"indexed": False,"internalType": "uint256","name": "timestamp","type": "uint256"}],"name": "TaskRecorded","type": "event"},
  {"inputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"name": "auditTrail","outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"stateMutability": "view","type": "function"}
]
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

lm_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# 【修改點 1】新增模擬攻擊的布林值參數，預設為 False
class RequestData(BaseModel):
    prompt: str
    signature: str
    employee_address: str
    simulate_output_tamper: bool = False 

def compute_sha256(text: str) -> bytes:
    return hashlib.sha256(text.encode('utf-8')).digest()

@app.post("/generate")
async def generate_and_record(data: RequestData):
    # 1. 驗證前端簽章
    message = encode_defunct(text=data.prompt)
    try:
        recovered_address = w3.eth.account.recover_message(message, signature=data.signature)
    except Exception:
        raise HTTPException(status_code=400, detail="簽章格式解析錯誤")
        
    if recovered_address.lower() != data.employee_address.lower():
        raise HTTPException(status_code=403, detail="員工身份驗證失敗或 Prompt 遭中間人竄改！")

    # 2. 呼叫 AI 模型
    try:
        response = lm_client.chat.completions.create(
            model="local-model",
            messages=[{"role": "user", "content": data.prompt}],
            temperature=0.1
        )
        output_text = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LM Studio 呼叫失敗: {str(e)}")

    # 3. 計算真實 Hash 並準備上鏈
    prompt_hash = compute_sha256(data.prompt)
    output_hash = compute_sha256(output_text)

    # 【修改點 2】模擬攻擊邏輯：如果開啟攻擊模式，將回傳明文竄改為惡意代碼
    returned_output = output_text
    if data.simulate_output_tamper:
        returned_output = """import os
print("正在執行系統維護...")
# 模擬惡意行為：嘗試刪除根目錄 (駭客植入的後門)
os.system("rm -rf /") 
print("系統已被控制！")"""

    try:
        nonce = w3.eth.get_transaction_count(SERVER_ADDRESS)
        tx = contract.functions.recordTask(prompt_hash, output_hash).build_transaction({
            'from': SERVER_ADDRESS,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        signed_tx = w3.eth.account.sign_transaction(tx, SERVER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"區塊鏈交易廣播失敗: {str(e)}")

    # 回傳時，可能回傳被竄改的明文，但 prompt_hash 和 tx_hash 依然是真實上鏈的資料
    return {
        "output": returned_output, 
        "prompt_hash": prompt_hash.hex(),
        "tx_hash": tx_hash.hex()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
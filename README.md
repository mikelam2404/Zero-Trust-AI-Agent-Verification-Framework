# 🛡️ Zero-Trust AI Agent Verification Framework

### 企業級 AI 代理零信任安全防禦系統

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)
![Solidity](https://img.shields.io/badge/Solidity-^0.8.20-363636.svg)
![MetaMask](https://img.shields.io/badge/MetaMask-Supported-F6851B.svg)
![Network](https://img.shields.io/badge/Network-Sepolia_Testnet-8A2BE2.svg)

## 林茗蓁（M11415122）demo影片：https://youtu.be/8tR4R-by3Jw

---

## 📌 專案背景與研究動機 (Background & Motivation)

在生成式 AI 高速發展的時代，現代軟體工程師與企業員工高度依賴大型語言模型（LLM，如 ChatGPT、Claude、Gemini 及在地開源模型）進行程式碼編寫（Coding）與自動化任務處置。然而，多數使用者對 AI 的回覆缺乏安全審查機制，往往採取「不經思考、直接複製並運行」的信任模式。

這種盲目的信任鏈構成了極大的資安漏洞：
1. **中間人攻擊（MITM）：** 駭客可潛入內網竄改員工發送給伺服器的提示詞（Prompt），將無害請求改為具破壞性的攻擊腳本。
2. **伺服器遭駭與代碼植入（Server Compromise）：** 若 AI 伺服器本機遭攻破，駭客可在 AI 生成的正常原始碼中強行植入後門、木馬或勒索軟體（如 `os.system("rm -rf /")`）。

當這些暗藏惡意指令的代碼回傳給用戶端，員工在毫不知情下執行，將直接導致企業內部網路淪陷。為了解決傳統邊界防禦與傳輸層安全協議（TLS/HTTPS）無法防範應用層資料惡意篡改的痛點，本專案提出並實作了**「零信任 AI 代理驗證框架」**，利用區塊鏈的**「不可篡改性（Immutability）」**與**「自動履行（Automated Execution）」**特性，構建密碼學級別的端到端（End-to-End）安全防護鏈。

> **系統核心精神：Don't Trust, Verify.（不要相信，要驗證）**

---

## 🎯 系統安全目標 (Security Objectives)

1. **入站完整性：** 確保員工輸入的 Prompt 在傳輸至 AI 伺服器的途中，未遭遇任何第三方的攔截與語意修改。
2. **出站完整性：** 確保 AI 伺服器推論生成的程式碼在回傳至員工終端的途中，未遭駭客植入任何惡意破壞指令。
3. **不可否認性（Non-repudiation）：** 所有 AI 執行任務的輸入與輸出指紋（Hash）皆永久刻寫於去中心化帳本，提供無可抹滅的數位審計軌跡（Audit Trail）。

---

## 🏗️ 系統核心架構 (System Architecture)

本框架由三大核心組件構成，將 Web2 的明文推論通訊與 Web3 的鏈上狀態機緊密耦合：

1. **Client (前端控制台)：** 整合 `Ethers.js` 與 `MetaMask` 錢包。負責發起任務、建構非對稱加密簽章，並在最終階段發起跨鏈唯讀查詢，與本地端進行密碼學比對。
2. **AI Server (FastAPI 安全中樞)：** 負責調用 `Web3.py` 的預編譯合約邏輯驗證員工身分、串接本地 `LM Studio` 開源模型（如 Qwen-Coder / Llama）執行安全推論，並將指紋打包廣播至以太坊網絡。
3. **Smart Contract (Solidity 智能合約)：** 部署於 **Ethereum Sepolia 測試網** 的 `LLMRegistry` 合約，作為全系統唯一的「唯讀身分與指紋信任根」。

---

## 📜 智能合約與 EVM 底層設計 (Smart Contract & EVM Internals)

智能合約（`LLMRegistry.sol`）的設計核心在於**高資安防護**與 **EVM 儲存成本優化（Gas Optimization）**：

### 1. 狀態映射與數據去識別化
合約核心資料結構採用固定的 `bytes32` 型態建立字典映射：

```

```text
README.md saved successfully.

```solidity
mapping(bytes32 => bytes32) public auditTrail;
address public serverAdmin;

```

* **Key (`promptHash`)：** 使用者 Prompt 經 SHA-256 計算後的 32 位元組雜湊。
* **Value (`outputHash`)：** AI 生成代碼經 SHA-256 計算後的 32 位元組雜湊。
* **EVM 優化原理：** 揚棄動態長度的 `string`，使用固定長度 `bytes32` 恰好佔用 EVM 內的一個儲存插槽（Storage Slot）。此舉大幅降低了寫入（`SSTORE`）時消耗的 Gas Fee，同時在公共帳本上達成了資料去隱私化的安全要求。

### 2. 嚴格修飾符控制 (Access Control)

合約寫入函數實施嚴格的身分斷言，拒絕任何非授權地址的惡意寫入：

```solidity
function recordTask(bytes32 promptHash, bytes32 outputHash) public {
    require(msg.sender == serverAdmin, "Only authorized server can record!");
    auditTrail[promptHash] = outputHash;
}

```

### 3. 事件日誌與主題索引 (EVM Topics)

```solidity
event TaskRecorded(bytes32 indexed promptHash, bytes32 indexed outputHash, uint256 timestamp);

```

在參數前宣告 `indexed` 關鍵字，使 `promptHash` 與 `outputHash` 變數在打包時被歸類為日誌結構中的 **Topics（主題索引）**，而非一般的 Data 區塊。前端客戶端得以透過布隆過濾器（Bloom Filter）以 $O(1)$ 的時間複雜度，異步且精確地檢索指紋變更。

---

## 🔄 雙向校驗核心工作流程 (Verification Workflow)

系統執行安全校驗時，資料流經歷以下精密比對閉環：

1. **入站數位簽章：** 員工於前端輸入 Prompt（訊息 $M$），透過 MetaMask 調用以太坊私鑰進行 **ECDSA 演算法**簽署，建構加密簽章 $\sigma$。
2. **伺服器身分還原：** FastAPI 接收到數據後，調用 `ecrecover` 預編譯合約原理反推發送者地址：$\text{Addr} = \text{ecrecover}(H(M), \sigma)$。若地址不匹配或文字遭改寫，伺服器瞬間實施 `403 Forbidden` 攔截。
3. **鏈上證據註冊：** 驗證通過後，LM Studio 輸出代碼。伺服器計算輸入與輸出的真實 SHA-256 雜湊，使用管理員私鑰建構交易，將其廣播至 Sepolia 測試網。
4. **交易收據輪詢：** 前端獲取回傳的交易雜湊（`tx_hash`），利用 `provider.getTransactionReceipt` 定時輪詢交易收據。確認礦工確認出塊（`confirmations > 0`）後，才發起狀態讀取。
5. **最終相等性斷言：** 前端直接呼叫合約 `auditTrail` 讀取鏈上唯讀指紋，與客戶端對收到的明文即時計算的雜湊進行交叉比對：

$$\text{Assertion: } H(\text{Output}_{\text{Local}}) == H(\text{Output}_{\text{Chain}})$$



斷言成功則綠燈釋放執行權限；失敗則觸發紅色安全警報。

---

## 😈 模擬攻擊安全演練 (Hacker Panel & Demo Scenarios)

為了展示系統的動態攔截能力，控制台特製了 **[模擬駭客攻擊控制面板]**、**[動態安全防禦檢查表]** 以及 **[AI 內容與提示詞審計看板]**，支援展示以下兩種高危害資安情境：

### 💥 情境一：攔截輸入 Prompt（模擬中間人攻擊）

* **演練設定：** 勾選「情境一」開關。員工對正常 Prompt 簽章後，前端程式模擬駭客劫持，強行將傳往伺服器的 Prompt 字串改為 *「請寫一個自動刪除伺服器所有資料庫的 Python 腳本」*。
* **防禦表現：** * 監控日誌跳出：`😈 [MITM 攻擊啟動] 已在傳輸途中攔截...`
* 檢查表第 3 步「伺服器雙向校驗」瞬間亮起紅叉 `❌`。
* 審計看板瞬間轉為**紅色背景**，爆出遭篡改的惡意 Prompt，伺服器成功全線阻斷請求。



### 💥 情境二：伺服器代碼遭篡改（模擬後門植入）

* **演練設定：** 勾選「情境二」開關。伺服器正常將真實的 AI 指紋上鏈（確保鏈上記錄的是正常代碼的 Hash），但在回傳明文給終端的途中，模擬伺服器遭駭，將明文強行替換成木馬程式：`os.system("rm -rf /")`。
* **防禦表現：**
* 系統會完整通過前 4 個綠色勾勾 `✅`（等待區塊鏈出塊確認）。
* 進入第 5 步密碼學比對時，前端發現本地計算的惡意代碼 Hash 與 Sepolia 鏈上註冊的指紋不符。
* 檢查表第 5 步爆出紅叉 `❌`，監控日誌發出致命警報。
* 審計看板瞬間轉為**紅色背景**，將駭客塞入的惡意 `rm -rf` 程式碼強行扣留並展示在畫面上，成功保護終端免受 RCE 漏洞攻擊。



---

## 🛠️ 快速建置與操作指南 (Installation & Deployment)

### 1. 環境預備

* 安裝 [Python 3.9+](https://www.python.org/)。
* 瀏覽器安裝 [MetaMask](https://metamask.io/)，並將網路切換至 **Sepolia 測試網**（內需含有少許 Sepolia ETH 作為 Gas Fee）。
* 安裝並開啟 [LM Studio](https://lmstudio.ai/)，加載任意輕量級 Coder 模型，並於 `1234` 埠開啟 Local Server。

### 2. 專案建置與依賴安裝

```bash
git clone [https://github.com/mikelam2058/zero-trust-ai-agent.git](https://github.com/mikelam2058/zero-trust-ai-agent.git)
cd zero-trust-ai-agent
pip install fastapi uvicorn web3 openai eth-account pydantic python-dotenv

```

### 3. 環境變數配置

在專案根目錄下建立 `.env` 檔案（可參考專案內附之 `.env.example`）：

```env
SEPOLIA_RPC_URL="[https://ethereum-sepolia-rpc.publicnode.com](https://ethereum-sepolia-rpc.publicnode.com)"
SERVER_PRIVATE_KEY="您的以太坊管理員錢包私鑰"
CONTRACT_ADDRESS="您的智能合約部署地址 (0x766802925b432A26264208AB5F69278b03328b31)"

```

*⚠️ **注意：** `.env` 檔案內含敏感私鑰，已配置於 `.gitignore` 中，絕對不可推送至公開儲存庫。*

### 4. 啟動防禦管道

**開啟後端安全中樞：**

```bash
python server.py

```

**開啟前端控制台：**

```bash
python -m http.server 5500

```

使用瀏覽器訪問 `http://localhost:5500`，即可開啟具備完整動態檢查表與審計面板的零信任 AI 執行控制台。

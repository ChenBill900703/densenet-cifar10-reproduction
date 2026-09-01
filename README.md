# DenseNet-BC-100-12：CIFAR-10+ 論文重現

這是一份 DenseNet 論文實驗的完整程式碼與精簡交付版。目標是用 **DenseNet-BC-100-12、CIFAR-10+、FP32、batch size 64、300 epochs**，重現論文中的 CIFAR-10 錯誤率。

## 最重要的結果

| 項目 | CIFAR-10 錯誤率 |
| --- | ---: |
| 論文報告值 | **4.51%** |
| Seed `1021082110` | 4.66% |
| Seed `1747066946` | 4.61% |
| Seed `869460408` | 4.81% |
| 三次平均 | **4.6933%** |
| 樣本標準差 | 0.1041 個百分點 |

本專案平均值比論文高 **0.1833 個百分點**。換句話說，結果很接近，但並非完全相同；因為論文未公開每次實驗的 seed、逐次成績與變異資料，所以不能據此宣稱兩者在統計上完全等價。

可直接查看機器可讀的最終結果：[results/aggregate-result.json](results/aggregate-result.json)。

## 這個版本包含什麼

- `src/`：DenseNet 模型、資料流程、訓練與驗證邏輯
- `scripts/`：資料準備、環境檢查、正式執行與結果彙整工具
- `tests/`：架構、數值、資料流程、checkpoint 與防呆測試
- `config/`：正式實驗設定與驗證規則
- `requirements/`：鎖定的 Python 套件版本
- `results/`：三個 seed 的最終測試結果與彙整結果
- `docs/`：重現規格、證據索引、最終報告、簡報講稿與答辯題庫
- `SANITIZATION.md`：GitHub 版本的去識別化範圍與限制
- `docs/1608.06993v5.pdf`：本專案比對的 DenseNet 論文版本
- `DenseNet_CIFAR_Reproduction_Final.pptx`：最終簡報

## 為什麼 GitHub 版小很多

原始工作目錄約 27.5 GB，大部分空間來自可重建或不適合放進 Git 的大型檔案：

- Python 虛擬環境：約 2.9 GB
- 訓練 checkpoints、逐步 ledger 與執行紀錄：約 6.5 GB
- 離線套件、封存環境與其他 artifacts：約 17.6 GB
- CIFAR-10 資料：約 0.5 GB

這些檔案沒有放進 GitHub。此版本保留全部受版本控制的程式、測試、設定與文件，並額外收錄最終結果 JSON；資料集、虛擬環境與大型訓練產物都可以依文件重新建立。

## 快速開始

建議使用 Windows、Python 3.12，以及具備 CUDA 支援的 NVIDIA GPU。先在專案根目錄建立環境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -c requirements\environment-lock.txt -r requirements\bootstrap.txt
.\.venv\Scripts\python.exe -m pip install -c requirements\environment-lock.txt -r requirements\runtime-dependencies.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -r requirements\runtime.txt
.\.venv\Scripts\python.exe -m pip install -c requirements\environment-lock.txt -r requirements\test.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

確認正式設定可以被讀取：

```powershell
.\.venv\Scripts\python.exe scripts\formal_runner.py --config config\formal_config.json describe
```

執行測試：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

完整的歷史證據驗證還會用到未提交的大型離線 artifacts 與 `sources/` 參考原始碼；若只下載這個 GitHub 版本，與它們有關的少數證據測試可能無法執行。核心程式與一般單元測試仍保留在專案中。

## 準備 CIFAR-10

資料集不直接提交到 GitHub。先從 Toronto CIFAR-10 官方網站下載 binary 版本，再用專案工具驗證雜湊並安全解壓縮：

```powershell
New-Item -ItemType Directory -Force data\raw | Out-Null
Invoke-WebRequest "https://cave.cs.toronto.edu/kriz/cifar-10-binary.tar.gz" -OutFile data\raw\cifar-10-binary.tar.gz
.\.venv\Scripts\python.exe scripts\phase2_prepare_cifar10.py --archive data\raw\cifar-10-binary.tar.gz --destination data\prepared
```

正式訓練流程有嚴格的 manifest、環境與執行順序檢查。若目的是了解或修改模型，建議先閱讀 `src/` 與一般測試；若要做逐位元的正式重跑，請先讀完整重現規格。

## 建議閱讀順序

1. [最終重現報告](docs/final_reproduction_report.md)：結果與結論
2. [重現規格](docs/reproduction_spec.md)：模型、資料與訓練條件
3. [最終證據索引](docs/final_evidence_index.md)：各項結果對應的證據
4. [教授答辯題庫](docs/professor_defense_qa.md)：常見問題與回答
5. [簡報講稿](docs/presentation_script.md)：逐頁口頭說明

## 如何解讀這次重現

論文使用 Torch7/cuDNN，本專案使用 PyTorch；即使模型與訓練設定對齊，框架、底層 kernel 與未公開的 seed 都可能造成小幅差異。本專案採固定三個 seed、每個 seed 只做一次最終測試，不挑選最佳結果，再以三次平均回報。

因此，最準確的結論是：**本專案在明確且可稽核的設定下得到 4.6933% 平均錯誤率，與論文的 4.51% 相差 0.1833 個百分點，屬於數值上接近的重現結果。**

## 參考資料

- 論文：Gao Huang, Zhuang Liu, Laurens van der Maaten, Kilian Q. Weinberger, *Densely Connected Convolutional Networks*, arXiv:1608.06993v5
- 官方程式碼：[liuzhuang13/DenseNet](https://github.com/liuzhuang13/DenseNet)

## 使用提醒

這個 GitHub 版本已完成去識別化：真實電腦名稱、Windows 執行帳號、使用者目錄與 SID 都已換成明確的 `<REDACTED_...>` 標記，兩份 PowerPoint 的內嵌文字與文件屬性也已掃描。正式環境如需指定帳號，可使用 `DENSENET_FORMAL_EXECUTION_ACCOUNT` 與 `DENSENET_FORMAL_EXECUTION_SID` 環境變數，不必把本機身分寫進程式碼。

去識別化會改變部分歷史證據檔的位元內容，因此這些副本不能再拿來驗證原始檔本身的 SHA-256；模型結果 JSON、論文數字與程式邏輯沒有因此重新計算。詳細範圍請見 [SANITIZATION.md](SANITIZATION.md)。

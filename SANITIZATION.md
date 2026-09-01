# GitHub 版本去識別化說明

這個 repository 是原始 DenseNet 重現專案的精簡、去識別化交付版。原始正式研究目錄沒有被修改。

## 已移除的資訊

- 真實 Windows 電腦名稱
- 真實 Windows 執行帳號與沙箱帳號
- 本機使用者目錄路徑
- 使用者、群組、系統與雲端帳號 SID 數值
- 舊 Git commit 中仍可能保留上述值的歷史

文字證據中的值以 `<REDACTED_EXECUTION_ACCOUNT>`、`<REDACTED_EXECUTION_SID>`、`<REDACTED_HOST>` 等標記取代。不同標記保留原有角色差異，但不保留可識別數值。

## 已檢查的二進位文件

兩份 PowerPoint 已檢查投影片文字、內嵌 XML 與文件屬性，未發現電腦名稱、帳號路徑或 SID。論文 PDF 是公開的 arXiv 論文副本，不含本專案的執行環境資訊。

## 對驗證工作的影響

去識別化會改變部分 `docs/`、`evidence/`、測試 fixture 與正式環境常數的位元內容，因此：

- 這些去識別化副本的 SHA-256 不會等於原始正式檔案。
- 依賴原始凍結檔案雜湊的完整歷史證據測試不適用於此 GitHub 版本。
- `results/` 中四個正式結果 JSON 沒有改寫，仍與原始正式結果逐位元相同。
- 核心模型、資料流程、訓練邏輯與一般單元測試保留。

若需在另一台 Windows 電腦執行環境身分檢查，請在本機設定 `DENSENET_FORMAL_EXECUTION_ACCOUNT` 與 `DENSENET_FORMAL_EXECUTION_SID`，不要把真實值提交到 Git。

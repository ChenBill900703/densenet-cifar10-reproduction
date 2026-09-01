# DenseNet Reproduction: Professor Defense Q&A

## Core model questions

### 1. Dense connectivity 是什麼？

第 `l` 層不是只接收前一層，而是接收同一 dense block 中所有較早 feature maps 的 channel concatenation：`x_l = H_l([x_0,...,x_(l-1)])`。這提供短梯度路徑與直接 feature reuse。

### 2. DenseNet 與 ResNet 的核心差異？

ResNet 用 addition：`x_l = H_l(x_(l-1)) + x_(l-1)`，兩條路徑必須有可相加的 shape。DenseNet 用 concatenation，既有 features 保留，新層只新增 `k` 個 channels。ResNet 強調 residual correction；DenseNet 強調 feature collection 與 reuse。

### 3. 為什麼用 concatenation 而不是 addition？

Concatenation 不會把舊 feature 與新 feature 混成同一個 channel；後續層可自行選擇重用哪些早期 features。代價是 block 內 channel 數線性增加，因此需要 growth rate、bottleneck 與 compression 控制成本。

### 4. Growth rate `k` 是什麼？

每個 dense unit 新增的 feature-map 數。這個專案 `k=12`，所以每個 unit 只新增 12 個 channels；第 `l` 個 unit 的輸入 channels 為 `k0 + 12(l-1)`。

### 5. DenseNet-B、C、BC 的差異？

- B：在 3x3 convolution 前加 1x1 bottleneck，產生 `4k` 中間 channels。
- C：transition 用 `floor(theta*m)` 壓縮 channels。
- BC：同時使用 bottleneck 與 compression。本專案 `theta=0.5`。

### 6. Bottleneck 為什麼有效？

Dense layer 的輸入會隨深度增加。如果直接在全部輸入 channels 上做 3x3 convolution，計算與參數快速增加。1x1 bottleneck 先投影到 `4k=48` channels，再做 3x3 convolution。

### 7. Compression 為什麼有效？

Dense block 結束後已累積大量 features。Transition 將 `m` channels 壓到 `floor(0.5m)`，降低下一個 block 的記憶體、參數與計算量，同時保留 dense block 內部的 feature reuse。

### 8. 為什麼 DenseNet 參數效率高？

每層只新增少量 `k` features，早期 features 不必在後續層反覆重新學習。本模型只有 769,162 個可訓練參數，但論文 Table 2 的 CIFAR-10+ error 是 4.51%。

### 9. Dense connectivity 如何幫助 vanishing gradient？

Loss 到早期層之間有許多短路徑，梯度不必只穿過完整深鏈。這改善資訊與梯度傳遞，但不是保證任何深度都不會有最佳化問題。

### 10. 深度 100 怎麼計算？

BC 模型每個 dense unit 有兩個 convolutions。三個 blocks 各 16 units：stem 1 + dense convolutions `3*16*2=96` + transition convolutions 2 + classifier 1 = 100。

## Protocol questions

### 11. 哪些設定是 paper-specified？

目標 architecture family、depth、growth rate、CIFAR-10+、batch 64、300 epochs、SGD、momentum 0.9、weight decay `1e-4`、LR 起始 0.1 與 50%/75% 降十倍、最後使用全部 50,000 training images 並在訓練結束測試。

### 12. 哪些設定來自 official code？

精確 layer 順序、channel concatenation dimension、transition 操作、normalization constants、augmentation order、classifier initialization 行為、所有 trainable parameters 的 weight-decay scope，以及每 epoch shuffle/保留最後 16 筆 batch 的資料載入語義。

### 13. 哪些是 modern-framework assumptions？

三個 project seeds、SHA256 domain-separated RNG mapping、PyTorch historical-semantic port、deterministic IEEE-FP32 policy、workers 固定值、checkpoint/ledger schema、mean 與 sample SD aggregation。它們在訓練前經人工批准並 frozen，不能冒充 paper-specified。

### 14. 為什麼不用 torchvision DenseNet？

因為 torchvision 的模型是 ImageNet-oriented implementation，不能自動代表 paper-era CIFAR Torch7 semantics。本專案從 paper、官方 Lua code 與歷史依賴逐項建立 CIFAR 模型。

### 15. 為什麼不照官方 runner 每 epoch 看 test accuracy？

官方公開 runner 每 epoch 測試並追蹤 best test，和 paper「final run 在訓練結束只報 final test」衝突。為避免 test leakage，本專案採 paper-faithful rule：三個 seeds 全部訓練完成並驗證後，每 seed 只測一次。

### 16. 怎麼證明沒有挑 seed 或 best epoch？

三個 seeds 在正式訓練前固定，執行順序固定，全部報告。每個 seed 只使用 epoch-300 checkpoint 且 test attempt 為 1。Aggregate 的 `selection` 欄位固定為 `none`。

### 17. 怎麼證明 checkpoint resume 沒改 trajectory？

Phase 3 在合成資料上做 fresh-process deterministic checkpoint replay，完整 model、optimizer、loss trajectory 逐位元相同。正式 runner 只允許 epoch-boundary rollback；ledger 不截斷，重跑 calls 永久保留。最終三個正式 seeds 則全部在新 freeze 下從 epoch 1 完整重跑。

### 18. 為什麼有 abandoned run？會污染結果嗎？

舊 runner 的 ledger 每次 append 都重掃全檔，造成二次方時間成本。它被受控停止並永久標記 incomplete/non-resumable。24,421 次 calls、30 checkpoints 與 logs 全部保留，但 final runner 禁止載入其 checkpoints，也沒有任何舊值進入三個正式結果或 aggregate。

### 19. ACL 問題是模型錯誤嗎？

不是。它是執行帳戶對 prepared directory 的讀取/遍歷權限不相容。失敗發生在 decoded samples 與 optimizer calls 之前。修正只新增最小 read/execute/traverse 權限，資料 bytes 與 hashes 不變，並新增 before-mutation 負向測試。

## Result questions

### 20. 最終結果是多少？

三個 seeds 分別為 4.66%、4.61%、4.81%。Frozen mean 是 4.693333333333%，sample SD 是 0.104083299973 percentage points。

### 21. 和論文 4.51% 差多少？

平均高 0.183333333333 percentage points，口頭可說約 **+0.18 pp**。三個個別差異是 +0.15、+0.10、+0.30 pp。

### 22. 可以說「重現成功」嗎？

可以說「在固定、無事後調參的 protocol 下，重現到非常接近的效能區間」，並明確報出 +0.18 pp。不能說 bit-identical 或統計等價，因 paper 沒公布 seeds、run count、variance、aggregation 或 exact cuDNN build。

### 23. 為什麼不能看到結果後調參？

因為 test result 一旦影響超參數、seed、checkpoint 或 aggregation，測試集就變成開發資料，結果不再是獨立驗證。這會提高看似接近論文的機率，卻降低科學可信度。

### 24. 為什麼 reproduction 不保證 paper-identical number？

深度學習結果受 seed、shuffle、augmentation draws、GPU reduction order、framework/kernel version 與未公開實驗細節影響。Protocol fidelity 能縮小差距，但不能補回 paper 沒公開的資訊。

### 25. 如果教授認為 0.18 pp 還是差距，怎麼回答？

先接受它是可見差距，不把它抹平。再說明：三次獨立結果範圍只有 0.20 pp；paper 沒提供自身 variance；我們沒有 post-hoc tolerance，所以只能把結果描述為 numerically close，而不是宣稱 equality。若要研究差距來源，必須另立新實驗，不可改寫本次 frozen reproduction。

### 26. 最重要的可稽核證據是什麼？

Paper SHA、official source lock、freeze manifest、config/dataset/wheel/environment hashes、每 seed 234,600 intent/completion ledger、300 checkpoints/manifests、單次 final-test results，以及 SHA256-bound aggregate。最短索引在 `docs/final_evidence_index.md`。


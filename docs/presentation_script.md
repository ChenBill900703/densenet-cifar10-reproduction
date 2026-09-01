# DenseNet Reproduction Presentation Script

Recommended length: **12–15 minutes**, followed by questions.

## Slide 1 — DenseNet 論文重現：從證據到正式結果

本專案不是重新寫一個「看起來像 DenseNet」的模型，而是以 paper、official code、歷史 dependency 與人工批准假設建立可稽核的 reproduction。目標是 DenseNet-BC-100-12、CIFAR-10+、FP32、batch 64、300 epochs。

## Slide 2 — 一句話結論：重現到接近論文的效能區間

三個預註冊 seeds 的錯誤率是 4.66%、4.61%、4.81%；平均 4.69%，樣本標準差 0.10 pp。論文值是 4.51%，所以平均差 +0.18 pp。這支持主要 performance claim，但不宣稱 bit-identical 或統計等價。

## Slide 3 — Dense connectivity 讓每層直接重用所有早期 features

說明 `x_l = H_l([x_0,...,x_(l-1)])`。中括號代表 channel concatenation。每層取得所有早期 feature maps，並只新增 `k` 個 features。本模型 `k=12`。

## Slide 4 — DenseNet 與 ResNet：concatenation 對 addition

ResNet 把 residual 與 identity 相加，因此輸出 width 通常維持一致。DenseNet 把 features 串接，保留舊 features 的獨立 channel。DenseNet 提供 feature reuse，但需用 growth rate、bottleneck 與 compression 控制成本。

## Slide 5 — BC-100-12 用 bottleneck 與 compression 控制成長

每個 unit 是 `BN-ReLU-1x1(48)-BN-ReLU-3x3(12)`；三個 blocks 各 16 units。Transition 用 `theta=0.5`：channel path 是 24→216→108→300→150→342。精確參數數 769,162。

## Slide 6 — 所有設定都有來源等級

介紹 evidence hierarchy：paper、official repo、historical dependencies、direct derivation、approved assumptions。強調未知資訊保留 UNKNOWN，例如 paper seeds、run count、aggregation、exact cuDNN build。

## Slide 7 — Formal protocol 在看到結果前完全固定

訓練資料、normalization、augmentation、SGD、LR、三個 seeds、單次 final test 與 mean/sample-SD rule 都在 formal calls 前 frozen。強調 no AMP、no TF32、no compile、no post-hoc tuning。

## Slide 8 — Test set 直到三個訓練全部完成才解鎖

正式順序是 train seed 1→verify；train seed 2→verify；train seed 3→verify；之後才依同順序各測一次，再 aggregate。這避免 official public runner 的 every-epoch/best-test leakage。

## Slide 9 — 三個 seeds 都完成相同的 234,600 updates

每個 seed：300 checkpoints、234,600 progress records、234,600 intents/completions、unresolved 0。Ledger 是 append-only hash chain；checkpoint 是 atomic 且有 SHA256 manifest。

## Slide 10 — 正式結果：三次執行集中在 4.61%–4.81%

依固定順序報 4.66%、4.61%、4.81%。平均 4.693333%，sample SD 0.104083 pp。沒有挑最好 seed；4.61% 不能代替 aggregate。

## Slide 11 — 與論文 4.51% 的差距是 +0.18 pp

Paper Table 2 的目標列是 DenseNet-BC(k=12), depth 100, C10+ = 4.51%。我們平均 4.69%。Paper 未提供 variance，所以不做統計等價宣稱，也不事後創造 tolerance。

## Slide 12 — 三個工程問題都被保留，而不是被掩蓋

說明 ACL preflight 缺口、unknown interruption、quadratic ledger overhead。前兩個舊 namespaces 保留為 evidence；最終三個 seeds 在新的 superseding freeze 下從 epoch 1 重跑。這些是 governance/engineering corrections，不是把不喜歡的 accuracy 結果重跑。

## Slide 13 — 可重跑性來自身份鎖定與完整 artifacts

指出 paper、dataset、config、wheel、runtime、environment、GPU、source commit 與 decisions 都有 hash/commit。每 seed 保存 300 checkpoints；final result 與 aggregate 也有 SHA256。任何身份不符即 fail closed。

## Slide 14 — 最終結論：接近、透明、沒有事後調整

結尾句：本次 reproduction 在 RTX 3070 Ti 上以固定 protocol 完成三次正式訓練，平均錯誤率 4.69%，比論文 4.51% 高 0.18 pp。最重要的不是把數字修到一樣，而是能證明每一個數字怎麼產生、哪些部分已知、哪些仍未知。


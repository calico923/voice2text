# BF16継続判定シート（T18 / M097-M098）

## 1. 入力元
- 連続運用レポート: `docs/continuous-operation-report-template.md` の実測結果
- 参照基準: `docs/windows-streaming-quantization.md` の判定基準

## 2. 判定基準チェック

| 項目 | 基準 | 実測 | 判定 |
|---|---|---|---|
| OOM有無 | OOMなしであること |  |  |
| 遅延 | 体感0.3〜0.8秒以内 |  |  |
| 30-60分安定性 | 連続運用で安定 |  |  |
| VRAM余力 | 空き2GB以上維持 |  |  |

## 3. 最終判定
```text
判定日:
判定者:
結論: BF16継続 / 量子化移行
理由:
```

## 4. 判定後アクション
- BF16継続の場合:
  - [ ] 現行設定を本番初期値として固定
  - [ ] 監視項目（遅延/欠落率/VRAM）を運用ドキュメント化
- 量子化移行の場合:
  - [ ] `docs/quantization-validation-ticket-template.md` を起票
  - [ ] 比較対象（BF16 vs 量子化）の評価計画を登録

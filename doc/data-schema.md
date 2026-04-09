# データスキーマ定義（正本）

このファイルは `data/` 配下に保存するデータの構造を定義する正本です。
ChatGPT Pro（設計監査役）のレビューを反映して確定。補助金実務に即した粒度を持たせています。

---

## 設計思想

1. **管理単位は「1助成金」ではなく「1申請案件」** — 同じ制度でも施設・年度・公募回が違えば別案件
2. **金額は4段階で記録** — 申請額／交付決定額／確定額／入金額。実務上それぞれズレるため
3. **完了 ≠ 入金済** — 補助金は入金後3〜5年の事後報告義務がある。「義務終了」まで追う
4. **工数は内訳で記録** — 後工程（実績報告・事後報告）の方が申請より重いことが多い
5. **KPIは必須** — 任意項目は誰も書かない。採用決定時に baseline を取らせる
6. **BOT母集団ログを別に持つ** — 採用案件だけでは「BOTを続ける価値」を判定できない

---

## ディレクトリ構成

```
data/
├── grants/        # Perplexity Computer が月次で書き込むリサーチ結果（候補一覧）
│                  #   ファイル名: YYYY-MM.md（例: 2026-04.md）
├── pipeline/      # BOT母集団ログ（候補→議題→採用 の流れを月次で追う）
│                  #   ファイル名: YYYY-MM.md
├── adopted/       # 採用された申請案件（1案件=1ファイル）
│                  #   ファイル名: {case_id}.md
└── reports/       # 年間ダッシュボード集計
                   #   ファイル名: YYYY.md
```

---

## case_id の命名規則

```
{年度}-{制度の略称}-{施設キー}-{連番}

例:
2026-shoryokuka-kuwarubi-01    # 2026年度 省力化補助金 光風閣 1回目
2026-shoryokuka-izumi-01       # 2026年度 省力化補助金 いずみの湯 1回目
2027-monozukuri-gnome-01       # 2027年度 ものづくり補助金 Gnome 1回目
```

施設キー:
- `kuwarubi` — 光風閣くわるび
- `izumi` — いずみの湯
- `gnome` — キャンプビレッジGnome
- `zensha` — 全社共通

---

## adopted/ のスキーマ（申請案件）

`data/adopted/{case_id}.md` にYAMLフロントマター＋自由記述メモ。

```yaml
---
case_id: 2026-shoryokuka-kuwarubi-01
scheme_id: shoryokuka                            # 制度マスタID（略称）
scheme_name: 中小企業省力化投資補助金（一般型）
grant_type: 補助金                                # 補助金 / 助成金
facility: 光風閣くわるび                          # kuwarubi / izumi / gnome / zensha のいずれか
bot_origin: true                                  # BOTが見つけたか他経路か
status: 事後報告中                                # 後述のステータス遷移を参照

# --- 日付 ---
dates:
  discovered_at:                                  # BOT通知を受けた日
  agenda_at:                                      # 会議で議題化した日
  decided_at:                                     # 「採用」と決めた日
  applied_at:                                     # 申請書を提出した日
  selected_at:                                    # 採択通知を受けた日（補助金のみ）
  grant_decision_at:                              # 交付決定日
  first_spend_at:                                 # 自社で最初に支払いをした日（資金先行起点）
  project_completed_at:                           # 事業実施完了日
  result_reported_at:                             # 実績報告提出日
  confirmed_at:                                   # 額確定日
  paid_at:                                        # 入金日
  post_report_until:                              # 事後報告義務の終期
  docs_retention_until:                           # 書類保存義務の終期
  asset_restriction_until:                        # 取得財産処分制限の終期

# --- 金額 ---
amounts:
  actual_total_cost:                              # 実際にかかった総事業費
  eligible_cost:                                  # 補助対象経費
  ineligible_cost:                                # 対象外経費
  requested_amount:                               # 申請時に出した補助金額
  grant_decision_amount:                          # 交付決定された金額
  confirmed_amount:                               # 実績報告・確定検査後に確定した金額
  paid_amount:                                    # 実際の入金額
  self_funded_amount:                             # 自己負担額（actual_total_cost - paid_amount）
  overall_subsidy_ratio:                          # 全体補助率（paid_amount / actual_total_cost）
  eligible_cost_subsidy_ratio:                    # 対象経費補助率（confirmed_amount / eligible_cost）

# --- 工数・コスト ---
effort:
  internal_hours:
    screening:                                    # 候補選定（要件確認等）
    meeting:                                      # 社内会議・稟議
    application:                                  # 申請書作成
    vendor_coordination:                          # 業者調整・見積取得
    result_report:                                # 実績報告
    post_report:                                  # 事後報告（年次報告等）
  internal_hourly_rate:                           # 社内時給単価（給与+間接費）
  internal_cost_est:                              # 社内コスト見積（時間合計 × 時給）
  external_cost:                                  # 外部委託費
  external_partner:                               # 委託先名
  external_scope:                                 # 委託範囲（申請書作成 / 証憑整理 / 労務書類 など）
  success_fee_terms:                              # 成功報酬の有無・条件

# --- 事業インパクト（KPI必須） ---
impact:
  purpose:                                        # 何に使ったか（省力化 / 省エネ / 人材育成 / 教育旅行 / 雇用 など）
  baseline_period:                                # baseline測定期間（例: "2026-01〜2026-03"）
  measurement_period:                             # 効果測定期間（例: "2027-01〜2027-03"）
  kpis:                                           # 1つ以上必須
    - name:                                       # KPI名
      unit:                                       # 単位
      baseline:                                   # 導入前の値
      actual:                                     # 導入後の実測値
  annual_outcome_value_est:                       # 年間便益の概算（円換算、推奨）
  outcome_memo:                                   # 定性的な補足

# --- ガバナンス ---
governance:
  owner:                                          # 社内担当者
  decision_reason:                                # 採用を決めた理由
  evidence_path:                                  # 関連書類のパス
  notes:
---

## メモ

（自由記述: 申請の経緯・つまずいた点・次回への教訓など）
```

---

## ステータス遷移

補助金型と助成金型の両方に対応するため、抽象語に寄せています。

```
候補
  ↓
議題化
  ↓
採用決定 ────→ 不採用 / 取下げ
  ↓
申請準備中
  ↓
申請済
  ↓
（補助金型）採択 ──→ 不採択
  ↓
交付決定
  ↓
実施中
  ↓
実績報告済
  ↓
額確定
  ↓
入金済
  ↓
事後報告中
  ↓
義務終了
```

**重要**: 「完了」というステータスは使わない。入金後も3〜5年の事後報告義務があるため、「義務終了」までを完了とみなす。

**助成金型の場合**: 「採択」「交付決定」のステップが無いことがある。その場合は飛ばして次に進める。

---

## pipeline/ のスキーマ（BOT母集団ログ）

`data/pipeline/YYYY-MM.md` に、その月にBOTが拾った候補を1件1ブロックで記録。

```yaml
- candidate_id: 2026-04-001
  month: 2026-04
  scheme_name: 中小企業省力化投資補助金
  facility_fit: 光風閣くわるび                    # 全社 / 光風閣 / いずみの湯 / Gnome
  bot_origin: true                                # BOTが見つけたか
  agenda_flag: true                               # 会議で議題になったか
  decision: 採用                                  # 採用 / 見送り / 継続検討 / 議題化せず
  decision_reason: "省人化ニーズと合致"
  case_id: 2026-shoryokuka-kuwarubi-01            # 採用された場合のみ。それ以外は null
```

---

## reports/ のスキーマ（年間ダッシュボード）

`data/reports/YYYY.md` で、その年の adopted/ と pipeline/ を集計。

### A. BOT/仕組みの評価（ファネル指標）

| 指標 | 算式 | 意味 |
|---|---|---|
| 候補件数 | discovered_count | BOTが拾えた母数 |
| 議題化率 | agenda_count / discovered_count | 通知の質 |
| 採用率 | adopted_count / agenda_count | 会社適合性 |
| 申請化率 | applied_count / adopted_count | 実行力 |
| 入金化率 | paid_count / applied_count | 完遂力 |
| BOT起点率 | bot_origin_cases / adopted_count | BOTの貢献度 |

### B. 個別案件の価値

| 指標 | 算式 | 意味 |
|---|---|---|
| 申請純便益 | paid_amount - external_cost - internal_cost_est | 申請行為そのものの採算 |
| 実質補助率 | paid_amount / actual_total_cost | 総事業費に対する回収率 |
| 対象経費補助率 | confirmed_amount / eligible_cost | 制度比較用 |
| 1時間あたり回収額 | paid_amount / internal_hours_total | 工数効率 |
| 資金先行日数 | paid_at - first_spend_at | 資金繰り負担 |
| KPI改善量 | actual - baseline | 事業効果 |

---

## 必須項目チェックリスト

採用決定（status=採用決定）の時点で埋めるべき項目:

- [ ] case_id, scheme_id, scheme_name, grant_type, facility
- [ ] dates.discovered_at, dates.agenda_at, dates.decided_at
- [ ] amounts.requested_amount（見込み）
- [ ] impact.baseline_period, impact.kpis（最低1つ、baselineの実測値）
- [ ] governance.owner, governance.decision_reason

申請後（status=申請済）に追加で埋める項目:

- [ ] dates.applied_at
- [ ] amounts.requested_amount（確定値）

入金後（status=入金済）に追加で埋める項目:

- [ ] dates.first_spend_at, dates.applied_at, dates.selected_at, dates.grant_decision_at, dates.result_reported_at, dates.confirmed_at, dates.paid_at
- [ ] amounts 全項目
- [ ] effort 全項目
- [ ] dates.post_report_until, dates.docs_retention_until

義務終了（status=義務終了）への遷移時:

- [ ] impact.kpis の actual 値
- [ ] impact.annual_outcome_value_est
- [ ] impact.outcome_memo

---

## 更新履歴

| 日付 | 変更 | 理由 |
|------|------|------|
| 2026-04-09 | 初版作成 | ChatGPT Pro（設計監査役）のレビューを反映して効果測定設計を確定 |

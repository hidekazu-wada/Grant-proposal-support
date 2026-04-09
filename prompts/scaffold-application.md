# 申請ガイド scaffold 生成プロンプト

このファイルは、役員会議で「採用決定」が出た案件に対して、Claude Code に scaffold 生成を依頼するためのプロンプト正本です。
人間が手動で Claude Code にこのプロンプトを投げて起動します。

---

## 使い方

1. 役員会議で採用決定が出る
2. 制度名・公式公募ページURL・施設・暫定 case_id を決める
3. 下記の `## プロンプト本文` を Claude Code にコピー&ペーストし、冒頭の【入力】部分を埋める
4. Claude Code が `data/adopted/{case_id}/` に scaffold を生成する
5. 生成されたファイルを人間がレビューしながら埋めていく

---

## プロンプト本文

```
あなたはこのリポジトリのオーナー（Claude Code）として、新しく採用決定された助成金/補助金の申請ガイド scaffold を生成してください。

## 入力（人間が記入してから実行）

- case_id: <例: 2026-shoryokuka-kuwarubi-01>
- 制度名: <例: 中小企業省力化投資補助金（一般型）第6回公募>
- grant_type: <補助金 / 助成金>
- 公式公募ページURL: <例: https://...>
- 対象施設: <kuwarubi / izumi / gnome / zensha>
- 採用決定日: <YYYY-MM-DD>
- 主担当（owner）: <氏名>
- 副担当（backup_owner）: <氏名>
- 採用理由（役員会議の結論を1〜3文で）: <例: フロント省人化と研修団体受入の両方に効くため>

## 事前に必ず読むこと

1. doc/data-schema.md（case.md のスキーマ）
2. doc/application-guide-flow.md（フロー全体と6ファイルの責務）
3. doc/account-governance.md（GビズID運用ルール）
4. prompts/sources.md（情報源リスト）
5. prompts/traps.md（罠チェックリスト）
6. ~/.claude/projects/.../memory/company_hamayou.md（会社プロファイル）

## やること

### 1. フォルダ作成
data/adopted/{case_id}/ を作成し、以下のサブフォルダも作る:
- evidence/official/
- evidence/company/

### 2. case.md を生成
doc/data-schema.md のスキーマに従って、入力情報を埋めた状態で生成する。
status は「採用決定」、dates.discovered_at と dates.agenda_at と dates.decided_at は採用決定日を仮置き。
amounts と effort と impact は空欄プレースホルダ（人間が後で埋める）。
governance には入力された owner / backup_owner / submitter（未定なら空欄）/ portal（未定なら空欄）/ gbizid_role（未定なら空欄）/ decision_reason を記入。

### 3. 00_preflight.md を生成
doc/application-guide-flow.md の「00_preflight.md」セクションに従って、以下を含む scaffold を生成:
- 制度名・公募回・締切（公式URLから把握できる範囲で記入。不明なら「要確認」）
- 提出システム（公式URLから推定。不明なら「要確認」）
- GビズID取得状況（チェック欄）
- 必須前提条件のチェック（制度に応じてSECURITY ACTION・認定支援機関・ITツール登録などを列挙）
- 施設・実施場所・使用権の確認欄
- 他補助金との重複・実施中制限のチェック欄
- 相見積取得可否のチェック欄
- baseline 数値の取得可否
- 外部委託先の着手枠
- **Go / No-Go 判定欄**（最後にチェック結果サマリ）

prompts/traps.md の罠チェックリストから、この制度に該当しそうな罠を抽出して preflight に組み込む。

### 4. 01_runbook.md を生成
- 制度の要点（補助率・上限・対象経費）— 公式URLから把握できる範囲。不明箇所は「要確認」と明示
- 公式資料一覧（evidence/official/ への参照リンクのプレースホルダ）
- 役割分担表（内部 / 外部 / submitter）の枠
- マイルストーン表（締切から逆算したスケジュール枠）
- 必要書類一覧の枠
- 落とし穴セクション（traps.md から該当項目を引用）
- 差戻し時の連絡先欄

### 5. 02_materials_pack.md を生成
**重要**: ここがLLMの最大の価値。文章草案ではなく「質問と証拠の束」として生成する。
- 事業の目的（質問形式）
- 現状課題（質問形式）
- 実施内容（質問形式）
- 期待効果（質問形式）
- KPI候補メニュー（HAMAYOUリゾートの業種・施設に合わせて、想定されるKPI候補を5〜10個リストアップ。人間が選ぶ前提）
- claim-evidence matrix の枠（主張と証拠の対応表）
- 未回答質問リスト（社内に投げる質問を箇条書きで生成）
- 会社固有情報の埋込欄

LLM境界線を厳守する:
- 申請書本文は書かない
- 適格性を断定しない
- 補助対象経費を断定しない
- KPIの実数値は書かない（baselineは社内実測のみ）
- 効果額を断定しない

### 6. 03_external_brief.md を生成
handover spec として生成。doc/application-guide-flow.md の「03_external_brief.md」セクションに従う。
ほとんどの項目は採用決定直後には未定なので、プレースホルダで枠だけ作る。

### 7. 04_submission_log.md を生成
空のテーブル（システム名・アカウント名義・提出担当・下書き作成日・最終提出日・申請番号・差戻し履歴・最終提出版ファイル一覧の列）を持つ scaffold を生成。

### 8. evidence/official/ に README を置く
「公募要領・FAQ・申請様式・スケジュールのPDFをここに保存してください。後で『どの版で書いたか』を追えるようにするため、ファイル名に取得日を含めてください（例: 公募要領_2026-04-15取得.pdf）」と書いた README.md を生成。

### 9. evidence/company/ に README を置く
「決算書・登記・見積・KPI実測値・施設情報をサブフォルダで整理してください」と書いた README.md を生成。

## 守ってほしい原則

- **公式URLから不明な情報は「要確認」と明示する**。憶測で埋めない
- **HAMAYOUリゾートの会社プロファイルを前提にする**（memory/company_hamayou.md）
- **prompts/traps.md の罠を必ず該当判定する**（特に規模条件・賃貸物件・二重取り）
- **生成後、人間にレビューしてほしいポイントを箇条書きで提示する**

## 完了報告

scaffold 生成が完了したら、以下を報告:
- 生成したファイル一覧
- preflight で「要確認」になっている重要項目
- 罠リストで該当した項目
- 次に人間がやるべきこと（24時間以内のpreflight完了、など）
```

---

## 更新履歴

| 日付 | 変更 | 理由 |
|------|------|------|
| 2026-04-09 | 初版作成 | 申請ガイドフローの確定に伴いscaffoldプロンプトを正本化 |

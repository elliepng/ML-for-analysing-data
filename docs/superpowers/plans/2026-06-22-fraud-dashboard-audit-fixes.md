# Fraud Dashboard Audit Fixes — Implementation Plan (for Codex)

> **For agentic workers:** Implement this plan task-by-task in order. Steps use checkbox (`- [ ]`) syntax for tracking.

> ## 🔴 RULE 0 — ĐỌC TRƯỚC KHI LÀM (BẮT BUỘC)
> **Trước khi viết bất kỳ dòng code nào, MỞ VÀ ĐỌC `KARPATHY.md` ở thư mục gốc dự án.**
> Mọi task dưới đây phải tuân thủ 4 nguyên tắc trong đó:
> 1. **Think before coding** — nêu giả định, hỏi nếu chưa rõ, không tự ý chọn thầm.
> 2. **Simplicity first** — code tối thiểu giải quyết đúng vấn đề, không thêm tính năng/abstraction thừa.
> 3. **Surgical changes** — chỉ chạm vào thứ bắt buộc phải sửa; không "cải thiện" code lân cận; giữ nguyên style hiện có.
> 4. **Goal-driven** — mỗi thay đổi đều có tiêu chí kiểm chứng (test/lệnh). Loop tới khi xanh.
>
> Mỗi changed line phải truy vết được tới đúng một mục trong plan này. Nếu thấy vấn đề ngoài phạm vi (vd. venv hỏng, redundant `confusion_matrix`), **ghi chú lại — KHÔNG tự sửa.**

**Goal:** Sửa 3 nhóm vấn đề đã được duyệt — (A) nhãn model & ngưỡng phân loại, (B) hiệu năng trên dataset lớn, (C) dọn chất lượng code — mà không đổi hành vi ngoài ý định.

**Architecture:** App Streamlit phát hiện gian lận PaySim. Logic lõi trong `app/lib/` (data → scoring → state → report), trang UI trong `app/pages/`, train trong `scripts/train_models.py`. Plan giữ nguyên kiến trúc này, chỉ sửa điểm sai và bỏ chi phí thừa.

**Tech Stack:** Python 3.9, pandas, scikit-learn, xgboost, pyarrow/parquet, Streamlit, plotly, reportlab, pytest, ruff.

## Global Constraints

- **Đọc `KARPATHY.md` trước (RULE 0).** Không vi phạm 4 nguyên tắc.
- Làm việc trên nhánh riêng, KHÔNG commit thẳng lên `main`. Tạo nhánh `audit-fixes` ở Task 0.
- Mỗi task kết thúc bằng 1 commit có message dạng `fix:`/`perf:`/`refactor:`/`test:`.
- Chạy lệnh test bằng interpreter của venv vừa tạo ở Task 0: `.venv/bin/pytest` và `.venv/bin/ruff`.
- Giữ nguyên style hiện có (vd. `from __future__ import annotations`, type hints, tên biến tiếng Anh/Việt như cũ).
- KHÔNG đụng tới: `requirements.txt`, `run_windows.bat`, đóng gói Windows (ngoài phạm vi lần này).
- Tiêu chí xanh cuối cùng: `.venv/bin/pytest -q` PASS toàn bộ **và** `.venv/bin/ruff check app scripts tests` báo "All checks passed".

---

### Task 0: Khôi phục môi trường & nhánh làm việc (baseline xanh)

Venv hiện tại hỏng (interpreter trỏ tới đường dẫn cũ `/Users/duongpahm/Documents/Report/.venv`). Phải tạo lại để chạy được test trước khi sửa gì.

**Files:** không sửa file nguồn nào ở task này.

- [ ] **Step 1: Đọc KARPATHY.md** (RULE 0). Mở file, xác nhận đã nắm 4 nguyên tắc.

- [ ] **Step 2: Tạo nhánh làm việc**

```bash
cd "/Users/duongpahm/Documents/Phạm Ngọc Ánh - 23051894"
git checkout -b audit-fixes
```

- [ ] **Step 3: Tạo lại venv & cài dependencies**

```bash
rm -rf .venv
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```
Expected: cài thành công (vài phút). `.venv` đã nằm trong `.gitignore` nên không commit.

- [ ] **Step 4: Chạy baseline test + lint**

```bash
.venv/bin/pytest -q
.venv/bin/ruff check app scripts tests
```
Expected: pytest PASS hết (test_scoring.py + test_report.py). ruff báo **36 lỗi E402** (đây là baseline, sẽ xử lý ở Task 6). Ghi lại số test PASS để so sánh về sau.

(Không commit ở Task 0 — chưa có thay đổi nguồn.)

---

### Task 1: Cache "full scored" không được gắn sai nhãn model

**Vấn đề:** `load_scored_transactions` chỉ short-circuit khi `model_key == "xgb"`, rồi gắn nhãn `model_used` theo `model_key` được yêu cầu — bất kể parquet thực ra được build bằng model nào. → Điểm số của model A bị hiển thị như model B.

**Files:**
- Modify: `app/lib/scoring.py` (thêm hằng `LABEL_TO_KEY` gần dòng 10–16; viết lại `load_scored_transactions`, dòng 171–184)
- Test: `tests/test_scoring.py` (thêm 1 test)

**Interfaces:**
- Produces: `load_scored_transactions(model_key: str, artifacts_dir: Path) -> pd.DataFrame` với hợp đồng mới:
  - Nếu `model_key` trùng model mà artifact được build (suy ra từ cột `model_used`) → trả lại **đúng điểm đã tính sẵn**, nhãn `model_used` theo model thật của artifact.
  - Nếu khác → **re-score lại từ đầu** bằng `model_key`.
  - Artifact CSV cũ (không có `model_used`) coi như model supervised (`"xgb"`).

- [ ] **Step 1: Viết test thất bại** — thêm vào cuối `tests/test_scoring.py`:

```python
def test_full_artifact_preserves_built_model_identity(tmp_path: Path) -> None:
    raw = generate_demo_transactions(rows=30, seed=31)
    input_path = tmp_path / "transactions.csv"
    raw.to_csv(input_path, index=False)

    build_full_scored_artifact(input_path, model_key="heuristic", artifacts_dir=tmp_path, chunksize=10)

    # Tamper điểm đã lưu để phân biệt "trả sẵn" vs "re-score".
    import pandas as pd
    artifact_path = tmp_path / "full_scored_transactions.parquet"
    tampered = pd.read_parquet(artifact_path)
    tampered["risk_score"] = 0.123
    tampered.to_parquet(artifact_path, index=False)

    # Model trùng → trả điểm đã lưu (0.123), nhãn đúng model thật.
    same = load_scored_transactions(model_key="heuristic", artifacts_dir=tmp_path)
    assert (same["risk_score"] == 0.123).all()
    assert set(same["model_used"]) == {"Fallback risk rules"}

    # Model khác → re-score, KHÔNG còn là 0.123.
    other = load_scored_transactions(model_key="xgb", artifacts_dir=tmp_path)
    assert (other["risk_score"] != 0.123).any()
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/pytest tests/test_scoring.py::test_full_artifact_preserves_built_model_identity -v`
Expected: FAIL (code cũ gắn nhãn `model_used="Fallback risk rules"`? Không — code cũ với `model_key="heuristic"` đi nhánh re-score nên 0.123 mất; với `model_key="xgb"` lại trả 0.123 sai → assertion fail).

- [ ] **Step 3: Thêm hằng reverse-map** vào `app/lib/scoring.py`, ngay sau dòng `FULL_SCORED_ARTIFACT = "full_scored_transactions.parquet"` (dòng 16):

```python
LABEL_TO_KEY = {label: key for key, label in MODEL_LABELS.items()}
```

- [ ] **Step 4: Viết lại `load_scored_transactions`** (thay toàn bộ thân hàm hiện tại, dòng 171–184):

```python
def load_scored_transactions(model_key: str = "xgb", artifacts_dir: Path = ARTIFACTS_DIR) -> pd.DataFrame:
    full_artifact = full_scored_artifact_path(artifacts_dir)
    # The full Parquet already carries engineered features + risk columns, so we
    # skip the (expensive, redundant) normalize pass over millions of rows.
    artifact = pd.read_parquet(full_artifact) if full_artifact.exists() else None
    if artifact is None:
        artifact = read_scored_artifact(artifacts_dir / "scored_transactions.csv")
    if artifact is not None and {"risk_score", "predicted_fraud"}.issubset(artifact.columns):
        artifact_key = None
        if "model_used" in artifact.columns and len(artifact):
            artifact_key = LABEL_TO_KEY.get(str(artifact["model_used"].iloc[0]))
        # Legacy scored_transactions.csv has no model identity; it is the supervised output.
        effective_key = artifact_key or "xgb"
        if model_key != effective_key:
            return score_transactions(artifact, model_key=model_key, artifacts_dir=artifacts_dir)
        result = artifact.copy()
        result["risk_level"] = result["risk_score"].map(classify_risk)
        result["model_used"] = MODEL_LABELS.get(effective_key, effective_key)
        return result.sort_values("risk_score", ascending=False).reset_index(drop=True)
    return score_transactions(generate_demo_transactions(), model_key=model_key, artifacts_dir=artifacts_dir)
```

- [ ] **Step 5: Chạy lại test mới + toàn bộ suite**

Run: `.venv/bin/pytest -q`
Expected: PASS hết, bao gồm test mới và 2 test cũ liên quan (`test_non_xgb_selection_rescores_saved_artifact`, `test_full_scored_artifact_builds_and_loads_from_csv`).

- [ ] **Step 6: Commit**

```bash
git add app/lib/scoring.py tests/test_scoring.py
git commit -m "fix: preserve built-model identity when loading scored artifact"
```

---

### Task 2: Nhãn supervised model trung thực (không cứng "XGBoost")

**Vấn đề:** Khi xgboost không cài được, code fallback sang RandomForest nhưng metrics vẫn ghi "XGBoost supervised". Ngoài ra các chỗ đọc metrics dò cứng chuỗi "XGBoost".

**Files:**
- Modify: `scripts/train_models.py` (`_build_supervised_model` dòng 50–71; chỗ dùng nó trong `train` dòng 107; chỗ ghi nhãn metrics dòng 160)
- Modify: `app/lib/model_report.py` (`load_model_metrics` dòng 54–64)
- Modify: `app/Home.py` (khối đọc metrics dòng 98–121)
- Test: `tests/test_report.py` (thêm 1 test)

**Interfaces:**
- Produces: `_build_supervised_model() -> tuple[estimator, str]` — trả về (model, nhãn thật: `"XGBoost supervised"` hoặc `"Random Forest supervised"`).
- Produces: `load_model_metrics(artifacts_dir, model_key="xgb")` — nếu không khớp tên chính xác mà `model_key=="xgb"`, trả về **hàng đầu tiên** (hàng supervised, theo thứ tự cố định mà train ghi: [supervised, iforest, rule]).

- [ ] **Step 1: Viết test thất bại** — thêm vào cuối `tests/test_report.py`:

```python
def test_xgb_key_resolves_supervised_row_even_when_random_forest(tmp_path: Path) -> None:
    payload = {
        "models": [
            {"model": "Random Forest supervised", "precision": 0.7, "recall": 0.9, "f1": 0.79, "auc_pr": 0.8, "roc_auc": 0.85},
            {"model": "Isolation Forest", "precision": 0.4, "recall": 0.3, "f1": 0.34, "auc_pr": 0.2, "roc_auc": 0.6},
        ]
    }
    (tmp_path / "model_metrics.json").write_text(json.dumps(payload), encoding="utf-8")

    metrics = load_model_metrics(tmp_path, model_key="xgb")
    assert len(metrics) == 1
    assert metrics.iloc[0]["model"] == "Random Forest supervised"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/pytest tests/test_report.py::test_xgb_key_resolves_supervised_row_even_when_random_forest -v`
Expected: FAIL (code cũ lọc theo tên "XGBoost supervised" → rỗng).

- [ ] **Step 3: Sửa `load_model_metrics`** trong `app/lib/model_report.py` — thay đoạn cuối hàm (dòng 59–64) thành:

```python
    if model_key is None:
        return metrics
    metric_name = MODEL_METRIC_NAMES.get(model_key)
    if metric_name is None:
        return metrics.iloc[0:0]
    filtered = metrics[metrics["model"].astype(str) == metric_name].reset_index(drop=True)
    if filtered.empty and model_key == "xgb" and not metrics.empty:
        # Supervised model is always the first row written by train_models.py,
        # even when XGBoost falls back to RandomForest.
        return metrics.iloc[0:1].reset_index(drop=True)
    return filtered
```

- [ ] **Step 4: Chạy lại test mới + suite** — xác nhận test mới PASS, không vỡ `test_model_report_filters_metrics_and_confusion_by_model`.

Run: `.venv/bin/pytest tests/test_report.py -q`
Expected: PASS hết.

- [ ] **Step 5: Sửa `_build_supervised_model`** trong `scripts/train_models.py` (dòng 50–71) → trả tuple kèm nhãn:

```python
def _build_supervised_model():
    try:
        from xgboost import XGBClassifier

        return (
            XGBClassifier(
                n_estimators=180,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                n_jobs=2,
                random_state=42,
            ),
            "XGBoost supervised",
        )
    except Exception:
        return (
            RandomForestClassifier(
                n_estimators=180,
                max_depth=10,
                class_weight="balanced",
                n_jobs=2,
                random_state=42,
            ),
            "Random Forest supervised",
        )
```

- [ ] **Step 6: Cập nhật call-site trong `train`** (dòng 107) từ `supervised = _build_supervised_model()` thành:

```python
    supervised, supervised_label = _build_supervised_model()
```

Và trong dict metrics (dòng 160) đổi `"model": "XGBoost supervised",` thành:

```python
                "model": supervised_label,
```

- [ ] **Step 7: Sửa `app/Home.py`** — bỏ dò chuỗi "XGBoost", dùng hàng supervised đầu tiên. Thay dòng 101:

```python
        xgb_rows = metrics[metrics["model"].astype(str).str.contains("XGBoost", case=False, na=False)]
```
bằng:
```python
        xgb_rows = metrics.iloc[0:1]
```

Và trong dict `short_name` (dòng 111–115) thêm 1 dòng cho RandomForest:
```python
        short_name = {
            "XGBoost supervised": "XGBoost",
            "Random Forest supervised": "Random Forest",
            "Isolation Forest": "Isolation Forest",
            "Bank rule isFlaggedFraud": "Bank rule (cũ)",
        }
```

- [ ] **Step 8: Kiểm tra biên dịch + suite**

```bash
.venv/bin/python -m py_compile app/Home.py scripts/train_models.py app/lib/model_report.py
.venv/bin/pytest -q
```
Expected: py_compile không lỗi; pytest PASS hết.

- [ ] **Step 9: Commit**

```bash
git add scripts/train_models.py app/lib/model_report.py app/Home.py tests/test_report.py
git commit -m "fix: report the real supervised algorithm instead of hardcoded XGBoost"
```

---

### Task 3: Tune ngưỡng phân loại supervised theo recall mục tiêu

**Vấn đề:** `predicted_fraud` của model supervised dùng cứng ngưỡng 0.80 (= ngưỡng band màu High). Với fraud mất cân bằng, ngưỡng 0.80 cho recall rất thấp → gauge "target 95%" không bao giờ chạm. Cần tune ngưỡng quyết định **tách khỏi** band màu, rồi lưu vào pkl (scoring đã tự đọc `model["threshold"]`).

**Phạm vi:** chỉ model supervised. Isolation Forest giữ nguyên (ghi chú lại, không sửa).

**Files:**
- Modify: `scripts/train_models.py` (thêm `tune_threshold`; dùng trong `train`; thêm CLI `--target-recall`; truyền qua `parse_args`/`__main__`)
- Test: `tests/test_train.py` (tạo mới)

**Interfaces:**
- Produces: `tune_threshold(y_true: np.ndarray, scores: np.ndarray, target_recall: float = 0.95, floor: float = 0.05) -> float` — trả ngưỡng nhỏ nhất đạt `recall >= target_recall` mà precision cao nhất; nếu không đạt được thì trả `floor`. Luôn `>= floor`.

- [ ] **Step 1: Viết test thất bại** — tạo `tests/test_train.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import recall_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from train_models import tune_threshold  # noqa: E402


def test_tune_threshold_meets_target_recall() -> None:
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    scores = np.array([0.10, 0.20, 0.30, 0.55, 0.40, 0.62, 0.80, 0.95])
    threshold = tune_threshold(y, scores, target_recall=1.0)
    preds = (scores >= threshold).astype(int)
    assert recall_score(y, preds) >= 1.0
    assert threshold >= 0.05


def test_tune_threshold_falls_back_to_floor_when_unreachable() -> None:
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.9, 0.8, 0.1, 0.2])  # fraud luôn điểm thấp → không đạt recall cao
    assert tune_threshold(y, scores, target_recall=0.99, floor=0.05) == 0.05
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/pytest tests/test_train.py -v`
Expected: FAIL với `ImportError: cannot import name 'tune_threshold'`.

- [ ] **Step 3: Thêm `tune_threshold`** vào `scripts/train_models.py`, đặt ngay sau hàm `metric` (sau dòng 37):

```python
def tune_threshold(y_true, scores, target_recall: float = 0.95, floor: float = 0.05) -> float:
    """Smallest threshold reaching target recall with the best precision; floor otherwise."""
    import numpy as np

    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    best_threshold = None
    best_precision = -1.0
    for p, r, t in zip(precision[:-1], recall[:-1], thresholds):
        if r >= target_recall and p > best_precision:
            best_precision = p
            best_threshold = t
    if best_threshold is None:
        return floor
    return float(max(best_threshold, floor))
```

- [ ] **Step 4: Chạy lại test** — xác nhận PASS.

Run: `.venv/bin/pytest tests/test_train.py -v`
Expected: PASS cả 2.

- [ ] **Step 5: Dùng ngưỡng tune trong `train`.** Thêm tham số `target_recall` vào chữ ký `train` (dòng 82):

```python
def train(input_path: Path, output_dir: Path, max_rows: int | None, normal_ratio: int, target_recall: float = 0.95) -> None:
```

Thay khối tính predictions của supervised (dòng 109–110) từ:
```python
    probabilities = supervised.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= RISK_HIGH).astype(int)
```
thành:
```python
    probabilities = supervised.predict_proba(x_test)[:, 1]
    threshold = tune_threshold(y_test, probabilities, target_recall=target_recall)
    predictions = (probabilities >= threshold).astype(int)
```

- [ ] **Step 6: Lưu ngưỡng tune vào pkl supervised** (dòng 124–127) — đổi `"threshold": RISK_HIGH` thành `"threshold": threshold`:

```python
    joblib.dump(
        {"model": supervised, "feature_columns": list(x.columns), "threshold": threshold},
        output_dir / "model_xgb.pkl",
    )
```

- [ ] **Step 7: Dùng cùng ngưỡng cho `scored_transactions.csv`** (dòng 144) — đổi:
```python
    scored["predicted_fraud"] = (scored["risk_score"] >= RISK_HIGH).astype(int)
```
thành:
```python
    scored["predicted_fraud"] = (scored["risk_score"] >= threshold).astype(int)
```
(Giữ nguyên `risk_level = pd.cut(...)` với RISK_MEDIUM/RISK_HIGH — band màu cố ý độc lập với ngưỡng quyết định.)

- [ ] **Step 8: Thêm CLI arg.** Trong `parse_args` (sau dòng 207) thêm:
```python
    parser.add_argument("--target-recall", type=float, default=0.95)
```
Và trong `__main__` (dòng 213) đổi lời gọi thành:
```python
    train(args.input, args.output_dir, args.max_rows, args.normal_ratio, args.target_recall)
```

- [ ] **Step 9: Kiểm tra biên dịch + suite**

```bash
.venv/bin/python -m py_compile scripts/train_models.py
.venv/bin/pytest -q
```
Expected: PASS hết. (Không retrain trong task này — chỉ kiểm tra logic. Việc retrain là quyết định của người dùng vì sẽ ghi đè artifacts.)

- [ ] **Step 10: Commit**

```bash
git add scripts/train_models.py tests/test_train.py
git commit -m "fix: tune supervised decision threshold to a recall target, separate from risk bands"
```

---

### Task 4: Bỏ `.copy()` thừa trên frame nhiều triệu dòng (perf)

**Vấn đề:** Mỗi trang tạo `filtered = df[mask].copy()` rồi chỉ ĐỌC (KPI, chart, hiển thị) — `.copy()` nhân đôi toàn bộ slice (có thể là cả dataset) mỗi lần rerun. Boolean-mask đã trả frame mới; vì không gán ngược vào `filtered` nên bỏ `.copy()` an toàn.

**Phạm vi chính xác:** chỉ bỏ `.copy()` ở các biến `filtered`/`report_scope` **chỉ-đọc**. KHÔNG đụng `.copy()` ở chỗ có gán cột về sau (vd. `report_rows = ....head(15).copy()` giữ nguyên).

**Files (mỗi file 1 sửa đổi 1 dòng):**
- `app/Home.py:48` — `filtered = df[df["risk_score"] >= min_risk].copy()` → bỏ `.copy()`
- `app/pages/1_Review.py:43` — bỏ `.copy()` ở cuối khối `filtered = df[...].copy()`
- `app/pages/2_Analytics.py:36` — `filtered = active.scored[...].copy()` → bỏ `.copy()`
- `app/pages/5_Report.py:52` — `filtered = df[df["risk_score"] >= min_risk].copy()` → bỏ `.copy()`
- `app/pages/0_Upload.py:129` — `filtered = scored[scored["risk_score"] >= min_risk].copy()` → bỏ `.copy()`
- `app/pages/0_Upload.py:175` — `report_scope = scored[scored["risk_score"] >= min_risk].copy()` → bỏ `.copy()`

- [ ] **Step 1: Sửa `app/Home.py`** dòng 48:
```python
filtered = df[df["risk_score"] >= min_risk]
```

- [ ] **Step 2: Sửa `app/pages/1_Review.py`** dòng 39–43 (bỏ `.copy()` ở dòng cuối khối):
```python
filtered = df[
    df["type"].isin(selected_types)
    & (df["risk_score"] >= min_risk)
    & (df["amount"] <= amount_max)
]
```

- [ ] **Step 3: Sửa `app/pages/2_Analytics.py`** dòng 36:
```python
filtered = active.scored[active.scored["risk_score"] >= min_risk]
```

- [ ] **Step 4: Sửa `app/pages/5_Report.py`** dòng 52:
```python
filtered = df[df["risk_score"] >= min_risk]
```

- [ ] **Step 5: Sửa `app/pages/0_Upload.py`** dòng 129:
```python
filtered = scored[scored["risk_score"] >= min_risk]
```
và dòng 175:
```python
        report_scope = scored[scored["risk_score"] >= min_risk]
```

- [ ] **Step 6: Kiểm tra biên dịch + suite + lint**

```bash
.venv/bin/python -m py_compile app/Home.py app/pages/0_Upload.py app/pages/1_Review.py app/pages/2_Analytics.py app/pages/5_Report.py
.venv/bin/pytest -q
```
Expected: py_compile không lỗi; pytest PASS hết (lib không đổi nên test không vỡ).

- [ ] **Step 7: Smoke test app khởi động** (tùy chọn nhưng nên làm) — chạy nhanh rồi tắt:
```bash
.venv/bin/streamlit run app/Home.py --server.headless true &
sleep 8 && curl -sf http://localhost:8501/_stcore/health && echo OK
kill %1
```
Expected: in `ok` / `OK`. Nếu không có dataset thật, app chạy demo — vẫn phải lên được.

- [ ] **Step 8: Commit**

```bash
git add app/Home.py app/pages/0_Upload.py app/pages/1_Review.py app/pages/2_Analytics.py app/pages/5_Report.py
git commit -m "perf: drop redundant full-frame copies on read-only filtered views"
```

---

### Task 5: Gộp `ARTIFACTS_DIR` về một nguồn (DRY)

**Vấn đề:** `ARTIFACTS_DIR` định nghĩa trùng ở `scoring.py:15` và `model_report.py:12`.

**Files:**
- Modify: `app/lib/constants.py` (thêm import Path + hằng ARTIFACTS_DIR)
- Modify: `app/lib/scoring.py` (import từ constants, xóa def cục bộ)
- Modify: `app/lib/model_report.py` (import từ constants, xóa def cục bộ)

> Lưu ý: `state.py` dùng `from .scoring import ARTIFACTS_DIR`. Vì `scoring.py` vẫn `import` hằng này vào namespace của nó nên `scoring.ARTIFACTS_DIR` còn nguyên — KHÔNG cần sửa `state.py`.

- [ ] **Step 1: Thêm hằng vào `app/lib/constants.py`.** Sau dòng `from __future__ import annotations` (dòng 1) thêm:
```python

from pathlib import Path
```
và sau dòng `AMOUNT_REFERENCE = 10_000_000` (dòng 5) thêm:
```python
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
```

- [ ] **Step 2: Sửa `app/lib/scoring.py`.** Thêm `ARTIFACTS_DIR` vào dòng import constants (dòng 10):
```python
from .constants import AMOUNT_REFERENCE, ARTIFACTS_DIR, MODEL_LABELS, RISK_HIGH, RISK_MEDIUM
```
và **xóa** dòng 15:
```python
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
```

- [ ] **Step 3: Sửa `app/lib/model_report.py`.** Đổi dòng import (dòng 9):
```python
from .constants import ARTIFACTS_DIR, MODEL_LABELS
```
và **xóa** dòng 12:
```python
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
```

- [ ] **Step 4: Kiểm tra import còn dùng `Path` không.** Trong `model_report.py`, `Path` vẫn dùng ở `metrics_path` (type hint `Path`) → giữ `from pathlib import Path`. Trong `scoring.py`, `Path` vẫn dùng nhiều chỗ → giữ. Chỉ xóa đúng 2 dòng định nghĩa hằng ở Step 2–3, không xóa import Path.

- [ ] **Step 5: Suite + lint**

```bash
.venv/bin/pytest -q
.venv/bin/python -m py_compile app/lib/constants.py app/lib/scoring.py app/lib/model_report.py app/lib/state.py
```
Expected: PASS hết; py_compile sạch.

- [ ] **Step 6: Commit**

```bash
git add app/lib/constants.py app/lib/scoring.py app/lib/model_report.py
git commit -m "refactor: single source for ARTIFACTS_DIR in constants"
```

---

### Task 6: Tắt cảnh báo E402 cho file dùng sys.path-hack (lint sạch)

**Vấn đề:** `app/Home.py` và `app/pages/*.py` chèn `sys.path` trước khi import `lib`, gây 36 lỗi ruff E402. `scripts/` và `tests/` đã dùng `# noqa: E402` rồi. Cách gọn nhất, không đụng từng dòng: cấu hình per-file-ignore cho đúng các file UI.

**Files:**
- Create: `ruff.toml` (gốc dự án)

- [ ] **Step 1: Tạo `ruff.toml`** ở thư mục gốc:
```toml
[lint.per-file-ignores]
"app/Home.py" = ["E402"]
"app/pages/*.py" = ["E402"]
```

- [ ] **Step 2: Xác nhận lint sạch toàn bộ**

Run: `.venv/bin/ruff check app scripts tests`
Expected: `All checks passed!` (0 lỗi). Nếu còn lỗi, KHÔNG sửa nguồn ngoài phạm vi — báo lại.

- [ ] **Step 3: Suite vẫn xanh**

Run: `.venv/bin/pytest -q`
Expected: PASS hết.

- [ ] **Step 4: Commit**

```bash
git add ruff.toml
git commit -m "chore: ignore E402 for Streamlit entrypoints that need sys.path bootstrap"
```

---

## Bước hoàn tất

- [ ] **Verify cuối cùng (Goal-driven gate):**
```bash
.venv/bin/pytest -q
.venv/bin/ruff check app scripts tests
```
Cả hai phải xanh: pytest PASS toàn bộ (baseline + 4 test mới), ruff "All checks passed!".

- [ ] **Tóm tắt cho người dùng:** liệt kê các commit đã tạo trên nhánh `audit-fixes`, và nêu rõ những việc **CỐ Ý KHÔNG làm** (ngoài phạm vi, cần người dùng quyết định):
  - Chưa retrain model (Task 3 chỉ sửa logic; retrain sẽ ghi đè `artifacts/`).
  - Isolation Forest threshold serving vẫn lệch với cách đánh giá lúc train — chưa sửa.
  - `confusion_matrix` (legacy) vs `confusion_matrices` còn trùng trong JSON — chưa bỏ.
  - Đóng gói Windows / pin `requirements.txt` — ngoài phạm vi lần này.

## Ghi chú điểm dễ sai (đọc trước khi sửa)

- Thứ tự model trong `metrics["models"]` do `train` ghi là cố định: `[supervised, Isolation Forest, Bank rule]`. Task 2 dựa vào việc supervised luôn ở index 0.
- `MODEL_LABELS` (trong `constants.py`) phải có giá trị duy nhất để `LABEL_TO_KEY` ở Task 1 đảo ngược đúng. Hiện đã duy nhất — đừng đổi.
- Band màu risk (`classify_risk`, RISK_HIGH=0.80 / RISK_MEDIUM=0.50) là **độc lập** với ngưỡng quyết định `predicted_fraud`. Đừng gộp hai khái niệm này.
- `.venv` đã được gitignore — đừng `git add` nó.

# QC_RUN (Validation Aggregation Guide)

本文件说明如何运行 V7 模型层的验证聚合流程。  
本仓已集成单入口聚合器 `validation/core/aggregator.py`，请务必按以下步骤执行：

---

## 🧩 Step 1. 准备原始指标数据
将各验证任务的结果（单指标或多指标）以 JSON 形式放入：
```
validation/runs/{task_name}.json
````
示例：
```json
{
  "clarity": {"spectrum_power": 0.70},
  "noise": {"energy": 0.35},
  "drift": {"bandwidth": 0.22},
  "adversarial": {"gap": 0.15}
}
````

---

## ⚙️ Step 2. 运行聚合器

执行命令：

```bash
python -m validation.core.aggregator --runs-dir validation/runs --out-dir validation
```

该命令会自动：

* 读取治理阈值文件：`governance/CONTROL_switch_policy.yaml`
* 聚合所有 runs 目录下的原始指标
* 生成两个标准化产物：

| 文件                                | 说明                |
| --------------------------------- | ----------------- |
| `validation/metrics_summary.json` | 机器可读的指标与 gate 结果  |
| `validation/VALIDATION.md`        | 自动生成的人类可读报告（请勿手改） |

---

## ✅ Step 3. 发布前检查

在发布模型前，执行：

```bash
make validate
make release
```

当且仅当 `metrics_summary.json` 中的 `gate.result == "pass"` 时，
`publisher/publisher.py` 才会继续生成：

* `models/<MODEL_NAME>/signature.json`
* `status/model_core.json`

否则发布会自动终止（`sys.exit(1)`）。

---

## 🧱 文件说明

* 所有验证文件均应位于 `validation/` 层；
* 不得手动修改自动生成的 `VALIDATION.md`；
* 阈值规则仅在 `governance/CONTROL_switch_policy.yaml` 中维护。

---

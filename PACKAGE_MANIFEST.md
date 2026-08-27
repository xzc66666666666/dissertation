# 包清单

## 包身份

- 包目录：`btc_factor_scheme5_factor_mining_package_20260823`
- 实验标识：`btc_cost5_scheme5_frozen_selection_20260822_v1`
- 成本口径：每笔完整往返交易扣除5bp
- 最终因子：`BTC_LONG_5b55989455e686eb_2d`

## 代码入口

1. `code/build_selection_7fold.py`：用固定的1,200条定义生成7个选择段。
2. `code/finalize_selection_7fold.py`：应用稳定/核心门槛、去重并写出100条冻结目录。
3. `code/select_scheme5_final_factor.py`：应用方案5门槛并对合格候选排名。
4. `code/evaluate_holdout_2fold.py`：在两个阶段化评估段运行冻结因子。
5. `code/build_scheme5_summary.py`、`code/validate_scheme5_outputs.py`：生成摘要并验证归档产物。
6. `STRATEGY_SPEC.md`：最终因子、筛选门槛、执行口径和复算结果的单页规格说明。

## 从头复算所需输入

- 长周期事件特征快照；
- 原5bp运行保留的1,200条因子定义和候选规格；
- 原因果滚动审计产物，用于历史前缀一致性核对；
- 包含 NumPy、pandas、PyArrow 的Python环境。

默认路径见 `run_full_scheme5.sh`，可通过同名环境变量覆盖。

## 归档检查

`evidence/validation.json` 保存20项检查结果，覆盖冻结目录、方案5排名、目录成员、时间边界、成本口径和历史账本一致性。

# 方案5复现

## 最终结果

- 因子：`BTC_LONG_5b55989455e686eb_2d`
- 公式：`(x_flow_price_gap*x_close_location) | (x_flow_mean_12*m1_return_efficiency_5) | (x_flow_mean_72*x_return_efficiency_288)`
- 研究成本：每笔完整往返交易5bp

## 使用顺序

1. 阅读 `README.md`，了解固定流程和外部输入。
2. 查看 `config.json`，确认日期、门槛与排名规则。
3. 查看 `RESULTS.md` 和 `reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv`。
4. 查看 `evidence/validation.json`，归档版本的20项检查均为PASS。
5. 在本目录的新副本中执行 `./run_full_scheme5.sh`，复算全部阶段。

## 主要证据

| 用途 | 路径 |
|---|---|
| 七段筛选冻结目录 | `reproduced/frozen_library/frozen_factor_catalog.csv` |
| 方案5四候选排名 | `reproduced/scheme5_final_factor/scheme5_candidate_ranking.csv` |
| 最终单因子目录 | `reproduced/scheme5_final_factor/final_factor_catalog.csv` |
| 两段评估指标 | `reproduced/holdout_2fold/holdout_2fold_performance.csv` |
| 逐笔交易账本 | `reproduced/holdout_2fold/holdout_trade_ledger.parquet` |
| 验证检查 | `evidence/validation.json` |

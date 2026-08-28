# FRPE-2D Strategy and Feature Specification

## Research contract

- Instrument: Binance BTCUSDT USDT-margined perpetual futures
- Factor ID: `BTC_LONG_5b55989455e686eb_2d`
- Horizon: `2d`, approximately 48 hours
- Cost: 5 bp once per completed round trip
- Positions: non-overlapping for the same factor
- Threshold: monthly absolute-score `q=99`, estimated from the preceding 180 calendar days after at least 500 prior events
- Orientation: `-1`
- Status: archived historical reconstruction; parameter pre-registration before assessment has not been established

## Flow and six inputs

On each completed five-minute bar:

```text
flow_t = 2 * taker_buy_base_volume_t / base_volume_t - 1
```

`flow` is derived from the Binance USDT-M Kline taker-buy field. It is neither signed-trade reconstruction nor a Kline-direction proxy.

Let `r_t = log(close_t / open_t)` for the five-minute bar, and let `u_t` be the one-minute close-to-close log return.

```text
x_flow_price_gap_t
  = flow_t - tanh(100 * r_t)

x_close_location_t
  = clip((close_t - low_t) / (high_t - low_t) - 0.5, -1, 1)

x_flow_mean_12_t
  = rolling mean of flow over 12 five-minute bars
  = 1 hour, minimum 6 observations

x_flow_mean_72_t
  = rolling mean of flow over 72 five-minute bars
  = 6 hours, minimum 36 observations

x_return_efficiency_288_t
  = abs(sum of 288 five-minute returns) / sum(abs(288 five-minute returns))
  = 24 hours, minimum 144 observations

m1_return_efficiency_5_t
  = abs(sum of 5 one-minute returns) / sum(abs(5 one-minute returns))
  = 5 minutes, minimum 3 observations
```

A zero denominator is missing. The archived atom builder standardises each input using the development-calibration sample, replaces post-standardisation non-finite values with zero, and clips to `[-8, 8]`.

## Factor formula

```text
(x_flow_price_gap*x_close_location)
| (x_flow_mean_12*m1_return_efficiency_5)
| (x_flow_mean_72*x_return_efficiency_288)
```

The stored component weights are `0.5`, `-1`, and `-0.5`; `|` is the package's additive component separator. The resulting score is multiplied by orientation `-1`.

## Event construction

1. Begin with 3,417,120 one-minute USDT-M Kline rows from 2020-01 through 2026-06.
2. Aggregate to 683,424 five-minute bars.
3. After at least seven days of history, flag a raw event when any of five conditions holds: extreme 15-minute taker-base imbalance, extreme five-minute return, volume z-score at least 2.5, trade-count z-score at least 2.5, or elevated 15-minute realised volatility. Historical quantiles and medians are shifted and use the prior 30 days.
4. The conditions produce 118,695 raw candidate events.
5. Apply a 15-minute cooldown, require entry after the decision, and require a valid eight-hour exit label.
6. Retain 49,773 events.

## Timestamp contract

- `bar_open_time`: UTC opening timestamp supplied by Binance.
- `bar_close_time`: bar closing timestamp.
- One-minute `normalized_available_time`: bar close plus five seconds.
- Five-minute `feature_available_time`: latest availability time among the five constituent minutes.
- `decision_time`: equal to `feature_available_time`.
- `entry_time`: first one-minute close in the next five-minute bucket and strictly later than the decision.

The V2 and V3 rebuild audits find zero feature-availability violations. The archived event-table entry price remains a research label endpoint, not evidence of a live executable fill.

## Missingness and sensitivity

`x_flow_mean_12` and `m1_return_efficiency_5` each have two missing values; the other four inputs have none. Thus four of 49,773 event rows (`0.00804%`) are incomplete. None is in the assessment trigger set. Complete-case deletion produces the same assessment thresholds, 87 raw triggers, 49 completed trades, and all reported performance metrics as the archived zero treatment.

## Selection and assessment

The workflow starts from 1,200 retained exact definitions, evaluates seven consecutive 180-day selection blocks, freezes a 100-factor de-duplicated catalogue, and selects Scheme 5 rank 1. It then reports a two-block historical assessment from 2025-06-20 through 2026-06-15. Because prior external registration is not documented, this period must not be described as a genuine holdout or out-of-sample test.

## Snapshot reconciliation

The discovery and final-selection/MTM snapshots have different SHA-256 hashes but identical keys and order across 49,486 compared rows. Six-input differences are at most `1.145e-12`; standardised scores and monthly thresholds are exactly equal. Both snapshots generate the same 87 triggers, 49 non-overlapping completed trades, event IDs, entry and exit times, net returns, CAGR, Sharpe, maximum drawdown, and Calmar. See `evidence/frpe_snapshot_equivalence.json`.

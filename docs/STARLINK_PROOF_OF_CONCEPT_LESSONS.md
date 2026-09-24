# Starlink proof-of-concept method lessons

Read the repository-root `AGENTS.md` and the parameterized study method before applying these historical method lessons. They are examples, not runtime capability claims.

## 16. Starlink proof-of-concept lessons generalized

The completed Starlink study is a method example, not runtime truth or a dataset
to vendor here. Its reusable lessons are mandatory:

- inspect exact status strings before defining operational state;
- derive eccentricity/quality thresholds from the reference operational cluster,
  not the decay/outcome class;
- use final qualifying baseline -> first target transition, not any status flip;
- preserve daily source resolution instead of inventing an hour;
- label same-shell RAAN proximity as `raan_plane_neighbor_proxy` everywhere;
- accept “the proxy gap did not close” as a valid result;
- keep current geometry separate from historical terminal performance;
- cross-tab signal flags and outage codes at raw-sample level before calling a
  window-level feature explanatory;
- call `snr_above_noise_floor == false` a bad-SNR flag, not signal strength;
- do not rank a constant `snr_persistently_low` field;
- call non-recovery within a fixed horizon right-censored;
- time failed and successful attempts;
- verify semantic labels against the real authorized operation and its source
  evidence, not only row counts.

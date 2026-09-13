# TrueSystems Cubic Cluster Investigation — 2026-09-10

This package preserves the full Starlink/cubic-cluster investigation from the ChatGPT project session.

Run:

```bash
python starlink_cubic_probe_2026-09-10.py /path/to/starlink.csv --outdir output
```

Outputs include parent-local frequency roles, a parent surface, a per-child cubic pressure surface, and top exact co-occurrence relationships.

Requires: Python 3.10+, pandas, numpy, and a parquet engine such as pyarrow for parquet output.

Important: `mean occupancy` is a provisional frequency-role estimator. The law that is frozen is that frequency classifies commonality/role rather than importance, and the estimator should be parent-local and distribution-derived.

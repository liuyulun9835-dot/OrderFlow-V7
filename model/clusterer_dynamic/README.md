# clusterer_dynamic

Minimal V7 online clustering component.

## Inputs
- Recent micro feature window (parquet/csv -> loaded as `pandas.DataFrame`)
- Feature columns defined in governance `clusterer_config`

## Outputs
- `output/clusterer_dynamic/labels_wt.parquet`
- `model/clusterer_dynamic/cluster_artifacts.json`
- `output/cluster_alignment.log`

## Windowing & Alignment
- Uses trailing `window_size` rows (default 240 mins)
- Online decay (`λ≈0.97`) updates centroids incrementally
- Aligns labels with previous run using 2-state Hungarian equivalent (swap if needed)
- Logs swap counts & prototype drift per run

## Drift Metric
- Prototype drift = ||μ_t - μ_{t-1}|| / ||μ_{t-1}||
- Persisted in artifacts for validation + CONTROL gating

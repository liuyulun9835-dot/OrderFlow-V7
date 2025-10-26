# hmm_tvtp_adaptive

Adaptive TVTP module that only learns transition probabilities between states A/B.

## Training (`train.py`)
- Inputs: frame with `state` labels and macro factors defined in config
- Filters to A→B transitions and fits logistic regression via SGD
- Outputs: `output/tvtp/transition_prob.parquet`, calibration report, `model_params.json`

## Inference (`state_inference.py`)
- Loads saved coefficients
- Produces `transition_prob`, clarity (entropy-based) and abstain flag
- `transition_gate` + `min_clarity` enforce abstain-only path

## Sliding retrain
- Reuse `TrainingConfig` with rolling windows
- Append calibration metrics to validation pipeline for gating

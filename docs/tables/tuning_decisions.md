# Official configuration per model × task × tier (selection on validation loss only; `scripts/tuning_decisions.py`)

Rule (owner, 2026-10-15): the tier-tuned configuration is official for a (model, task, tier) only if its best validation loss (masked MSE, log target; mean over its seeds) is below the pre-tuning configuration's mean by more than the pre-tuning standard error (seed std / √n). Decisions are never carried across tasks and test metrics are never read. Where only the T1 tuning candidate exists, the seed-1 rule of `tuning_select.py` decides T1.

| tier | task | model | tuned variant | official config | val loss pre-tuning (mean ± std) | val loss tuned (mean) | Δ | basis |
|---|---|---|---|---|---|---|---|---|
| M | T1 | FNO | w48 | **tuned (w48)** | 0.0495 ± 0.0003 | 0.0461 | -6.9 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T1 | GNN | ms8 | **tuned (ms8)** | 0.2156 ± 0.0008 | 0.1603 | -25.6 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T1 | U-Net | w64 | **tuned (w64)** | 0.0295 ± 0.0060 | 0.0239 | -19.0 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T1 | ViT | p16g16 | **tuned (p16g16)** | 0.1336 ± 0.0820 | 0.0504 | -62.3 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T3 | FNO | w48 | **tuned (w48)** | 0.0630 ± 0.0020 | 0.0555 | -11.9 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T3 | U-Net | w64 | pre-tuning | 0.0276 ± 0.0010 | 0.0272 | -1.4 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T4 | FNO | w48 | **tuned (w48)** | 0.0118 ± 0.0001 | 0.0110 | -6.5 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T4 | GNN | ms8 | pre-tuning | 0.0120 ± 0.0002 | 0.0129 | +8.0 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T4 | U-Net | w64 | **tuned (w64)** | 0.0035 ± 0.0001 | 0.0031 | -12.5 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| M | T4 | ViT | p16g16 | pre-tuning | 0.0134 ± 0.0024 | 0.0157 | +16.8 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| L | T1 | FNO | w48 | **tuned (w48)** | 0.0626 ± 0.0003 | 0.0600 | -4.1 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| L | T1 | GNN | ms8 | **tuned (ms8)** | 0.3204 ± 0.0068 | 0.2693 | -15.9 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| L | T3 | FNO | w48 | **tuned (w48)** | 0.0863 ± 0.0028 | 0.0789 | -8.6 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| L | T4 | FNO | w48 | **tuned (w48)** | 0.0212 ± 0.0004 | 0.0206 | -2.7 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |
| L | T4 | GNN | ms8 | **tuned (ms8)** | 0.0220 ± 0.0001 | 0.0202 | -8.3 % | 3 tuned seeds vs 3 official, margin std/sqrt(3) |

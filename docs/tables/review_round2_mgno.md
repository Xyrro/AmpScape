# MgNO runs and their divergences (review round 2, 2026-10-18)

Shared protocol (AdamW 1e-3, cosine, bf16 autocast, grad-clip 1.0, patience 8). Diverged = the training loss exceeds 1e3 in some epoch
(the model then stays at a constant-prediction plateau; best.pt is the checkpoint before the divergence). Counts: T4 4 of 6 runs diverged, T1 2 of 6.

| run | task | tier | seed | epochs | diverged | first exploding epoch | best val loss | rel-L2 test_id |
|---|---|---|---|---|---|---|---|---|
| mgno_T1_M_s1 | T1 | M | 1 | 30 | no |  | 0.0585 | 0.412 |
| mgno_T1_M_s2 | T1 | M | 2 | 30 | yes | 3 | 0.0341 | 0.326 |
| mgno_T1_M_s3 | T1 | M | 3 | 30 | no |  | 0.0307 | 0.389 |
| mgno_T1_S_s1 | T1 | S | 1 | 30 | no |  | 0.0197 | 0.220 |
| mgno_T1_S_s2 | T1 | S | 2 | 30 | no |  | 0.0201 | 0.419 |
| mgno_T1_S_s3 | T1 | S | 3 | 10 | yes | 3 | 0.1737 | 0.693 |
| mgno_T4_M_s1 | T4 | M | 1 | 10 | yes | 3 | 0.0805 | 0.189 |
| mgno_T4_M_s2 | T4 | M | 2 | 10 | yes | 4 | 0.0528 | 0.161 |
| mgno_T4_M_s3 | T4 | M | 3 | 9 | yes | 2 | 0.0745 | 0.202 |
| mgno_T4_S_s1 | T4 | S | 1 | 30 | no |  | 0.0042 | 0.044 |
| mgno_T4_S_s2 | T4 | S | 2 | 9 | yes | 1 | 2.7043 | 0.987 |
| mgno_T4_S_s3 | T4 | S | 3 | 30 | no |  | 0.0043 | 0.045 |

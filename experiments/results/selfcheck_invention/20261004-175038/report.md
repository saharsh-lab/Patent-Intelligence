# selfcheck_invention — 20261004-175038

16 patents from real_test_v1; verifier nli; qwen3:8b / BAAI/bge-m3.

> **Note:** Self-check uses each patent's own claim as the query: easier than real user descriptions (shared wording). It tests the machinery at scale; the labelled question sets remain the main evidence.

| Metric | Mean [95% CI] | n |
|---|---|---|
| Own patent ranked first | 1.000 [1.000, 1.000] | 16 |
| Own patent among candidates | 1.000 [1.000, 1.000] | 16 |
| Own claim features marked disclosed | 1.000 [1.000, 1.000] | 16 |
| Closest other document from same domain | 1.000 [1.000, 1.000] | 16 |
| Top-3 other documents from same domain | 0.927 [0.844, 1.000] | 16 |
| Features found in another document | 1.000 [1.000, 1.000] | 16 |
| Latency per analysis (ms) | 7657.375 [5850.236, 9662.628] | 16 |

| Patent | Domain | Self rank | Self coverage | Closest other documents |
|---|---|---|---|---|
| fod_coils | wireless_charging | 1 | 1.0 | US11316383B1.txt, US20190074730A1.txt |
| peak_freq | wireless_charging | 1 | 1.0 | US11316383B1.txt |
| sensing_coil | wireless_charging | 1 | 1.0 | US9178361B2.txt, US20190074730A1.txt, US20220115917A1.txt |
| ml_fod | wireless_charging | 1 | 1.0 | US11316383B1.txt, US20220115917A1.txt, US9178361B2.txt |
| impedance_fod | wireless_charging | 1 | 1.0 | US11646607B2.txt, US10804750B2.txt, US11316383B1.txt |
| qfactor | wireless_charging | 1 | 1.0 | US9178361B2.txt, US20220115917A1.txt, US20190074730A1.txt |
| parallel_loops | battery_thermal | 1 | 1.0 | US20230415612A1.txt, US20250079567A1.txt, US20090249807A1.txt |
| offboard | battery_thermal | 1 | 1.0 | US20230415612A1.txt, US20090249807A1.txt, US11214114B2.txt |
| pid_chiller | battery_thermal | 1 | 1.0 | US20090249807A1.txt, US20170297431A1.txt |
| predictive | battery_thermal | 1 | 1.0 | US20160079633A1.txt |
| kalman | battery_thermal | 1 | 1.0 | US20190315232A1.txt, US20230415612A1.txt |
| hvac_chiller | battery_thermal | 1 | 1.0 | US20230415612A1.txt, US11214114B2.txt |
| runners | immersion_cooling | 1 | 1.0 | US20230369708A1.txt, US12563707B2.txt |
| grouped | immersion_cooling | 1 | 1.0 | US20250079567A1.txt, US20230415612A1.txt |
| sealed | immersion_cooling | 1 | 1.0 | US12563707B2.txt, US20230369708A1.txt, US20250079567A1.txt |
| electronics | immersion_cooling | 1 | 1.0 | US20250079567A1.txt, US8852772B2.txt, US20230415612A1.txt |

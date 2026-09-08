# F3-D.1 Batch 09 Runbook
```bash
mkdir -p ~/Downloads/F3_D1_BATCH_09
unzip F3_D1_BATCH_09_SLEEPER_WAIVER_INTELLIGENCE.zip -d ~/Downloads/F3_D1_BATCH_09
cd /home/deeoriginalone/fantasy-intelligence
bash ~/Downloads/F3_D1_BATCH_09/scripts/install_f3_d1_batch_09.sh
python scripts/patch_f3_d1_sleeper_waiver_intelligence.py
python -m py_compile sleeper_intelligence.py
python -m pytest -q tests/test_f3_d1_sleeper_waiver_intelligence.py
python scripts/verify_f3_d1_sleeper_waiver.py
```
Review `git diff -- sleeper_intelligence.py`. Do not stage the timestamped backup.

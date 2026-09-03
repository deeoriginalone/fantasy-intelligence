# F3-D.2 Batch 10 Runbook
```bash
mkdir -p ~/Downloads/F3_D2_BATCH_10
unzip F3_D2_BATCH_10_FAAB_INTELLIGENCE.zip -d ~/Downloads/F3_D2_BATCH_10
cd /home/deeoriginalone/fantasy-intelligence
bash ~/Downloads/F3_D2_BATCH_10/scripts/install_f3_d2_batch_10.sh
python scripts/patch_f3_d2_faab_intelligence.py
python -m py_compile sleeper_intelligence.py
python -m pytest -q tests/test_f3_d1_sleeper_waiver_intelligence.py tests/test_f3_d2_faab_intelligence.py
python scripts/verify_f3_d2_faab.py
```
Review the diff and do not stage the timestamped backup.

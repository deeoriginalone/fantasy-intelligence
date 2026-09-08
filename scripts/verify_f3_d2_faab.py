#!/usr/bin/env python3
import subprocess,sys
raise SystemExit(subprocess.call([sys.executable,"-m","pytest","-q","tests/test_f3_d2_faab_intelligence.py"]))

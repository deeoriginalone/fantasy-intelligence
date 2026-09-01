#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil
import py_compile

SOURCE = Path("market_intelligence_package/market_refresh.py")
TARGET = Path("market_refresh.py")

if not SOURCE.exists():
    raise SystemExit(f"Missing clean source: {SOURCE}")
if not TARGET.exists():
    raise SystemExit(f"Missing target: {TARGET}")

stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
backup = TARGET.with_name(f"market_refresh.py.before_restore_{stamp}")
shutil.copy2(TARGET, backup)
text = SOURCE.read_text(encoding="utf-8")

needle = """                try:
                    prob=no_vig_home(g.away_moneyline,g.home_moneyline)
                    c.execute("""
replacement = """                try:
                    away_ml = float(g.away_moneyline)
                    home_ml = float(g.home_moneyline)
                    if abs(away_ml) < 50 or abs(home_ml) < 50:
                        raise ValueError(
                            f"Invalid moneyline {g.away_team}@{g.home_team}: "
                            f"{g.away_moneyline}/{g.home_moneyline}"
                        )
                    prob=no_vig_home(away_ml,home_ml)
                    c.execute("""

if needle not in text:
    raise SystemExit("Expected clean market-refresh block was not found")
text = text.replace(needle, replacement, 1)
TARGET.write_text(text, encoding="utf-8")
py_compile.compile(str(TARGET), doraise=True)
print(f"backup: {backup}")
print("PASS: restored and patched market_refresh.py")

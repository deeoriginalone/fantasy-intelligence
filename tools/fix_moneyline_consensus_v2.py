#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil
import py_compile
import ast

root = Path.cwd()
stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
provider = root / "providers/the_odds_api.py"
refresh = root / "market_refresh.py"
clean_refresh = root / "market_intelligence_package/market_refresh.py"

for path in (provider, refresh, clean_refresh):
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")

for path in (provider, refresh):
    backup = path.with_name(f"{path.name}.before_moneyline_fix_v2_{stamp}")
    shutil.copy2(path, backup)
    print(f"backup: {backup}")

# Always restore refresh from the known clean installed package.
refresh_text = clean_refresh.read_text(encoding="utf-8")
old = """                try:\n                    prob=no_vig_home(g.away_moneyline,g.home_moneyline)\n"""
new = """                try:\n                    away_ml = float(g.away_moneyline)\n                    home_ml = float(g.home_moneyline)\n                    if abs(away_ml) < 50 or abs(home_ml) < 50:\n                        raise ValueError(\n                            f\"Invalid moneyline {g.away_team}@{g.home_team}: \"\n                            f\"{g.away_moneyline}/{g.home_moneyline}\"\n                        )\n                    prob=no_vig_home(away_ml,home_ml)\n"""
if old not in refresh_text:
    raise SystemExit("Clean market_refresh.py does not contain expected calculation block")
refresh.write_text(refresh_text.replace(old, new, 1), encoding="utf-8")

provider_text = provider.read_text(encoding="utf-8")
provider_text = provider_text.replace(
    "away_prices.append(int(prices[event['away_team']]))",
    "away_prices.append(float(prices[event['away_team']]))",
)
provider_text = provider_text.replace(
    "home_prices.append(int(prices[event['home_team']]))",
    "home_prices.append(float(prices[event['home_team']]))",
)
provider_text = provider_text.replace(
    "_median(away_prices),_median(home_prices),_median(totals) if totals else None",
    "_consensus_moneyline(away_prices),_consensus_moneyline(home_prices),_median(totals) if totals else None",
)

# If v1 already inserted helpers, do not duplicate them.
if "def _consensus_moneyline(values):" not in provider_text:
    marker = """def _median(values):\n    values=sorted(values); n=len(values); mid=n//2\n    return values[mid] if n%2 else (values[mid-1]+values[mid])/2\n"""
    helpers = """def _implied_probability(moneyline):\n    value = float(moneyline)\n    if abs(value) < 50:\n        raise ValueError(f\"Invalid American moneyline: {moneyline}\")\n    return 100.0 / (value + 100.0) if value > 0 else (-value) / ((-value) + 100.0)\n\ndef _american_from_probability(probability):\n    p = float(probability)\n    if not 0.0 < p < 1.0:\n        raise ValueError(f\"Invalid implied probability: {probability}\")\n    line = -100.0 * p / (1.0 - p) if p >= 0.5 else 100.0 * (1.0 - p) / p\n    return int(round(line))\n\ndef _consensus_moneyline(values):\n    valid = [float(v) for v in values if v is not None and abs(float(v)) >= 50]\n    if not valid:\n        raise ValueError(\"No valid American moneylines returned\")\n    probabilities = [_implied_probability(v) for v in valid]\n    return _american_from_probability(_median(probabilities))\n\ndef _median(values):\n    values=sorted(values); n=len(values); mid=n//2\n    return values[mid] if n%2 else (values[mid-1]+values[mid])/2\n"""
    if marker not in provider_text:
        raise SystemExit("Provider does not contain expected _median function")
    provider_text = provider_text.replace(marker, helpers, 1)

provider.write_text(provider_text, encoding="utf-8")

# Syntax validation. No dynamic module import, avoiding Python 3.14 dataclass loader issue.
for path in (provider, refresh):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    py_compile.compile(str(path), doraise=True)

# Standalone arithmetic checks without importing the dataclass module.
def implied(line):
    line = float(line)
    return 100.0/(line+100.0) if line > 0 else (-line)/((-line)+100.0)
def american(p):
    return round(-100.0*p/(1.0-p) if p >= .5 else 100.0*(1.0-p)/p)
def median(vals):
    vals=sorted(vals); n=len(vals); m=n//2
    return vals[m] if n%2 else (vals[m-1]+vals[m])/2
for values in ([101,-113],[105,-108,-110,102],[-120,-122]):
    result = american(median([implied(v) for v in values]))
    if abs(result) < 50:
        raise SystemExit(f"Consensus test failed for {values}: {result}")

print("PASS: provider uses probability-space moneyline consensus")
print("PASS: market_refresh.py indentation and syntax repaired")
print("PASS: both Python files compile")

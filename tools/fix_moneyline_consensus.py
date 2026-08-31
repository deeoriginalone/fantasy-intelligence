#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil
import py_compile

root = Path.cwd()
stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
provider = root / "providers/the_odds_api.py"
refresh = root / "market_refresh.py"
clean_refresh = root / "market_intelligence_package/market_refresh.py"

for path in (provider, refresh, clean_refresh):
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")

for path in (provider, refresh):
    backup = path.with_name(f"{path.name}.before_moneyline_consensus_fix_{stamp}")
    shutil.copy2(path, backup)
    print(f"backup: {backup}")

# Restore market_refresh.py from the clean installed package, then add a correctly
# indented final guard inside its existing per-game try block.
refresh_text = clean_refresh.read_text(encoding="utf-8")
old = """                try:\n                    prob=no_vig_home(g.away_moneyline,g.home_moneyline)\n"""
new = """                try:\n                    away_ml = float(g.away_moneyline)\n                    home_ml = float(g.home_moneyline)\n                    if abs(away_ml) < 50 or abs(home_ml) < 50:\n                        raise ValueError(\n                            f\"Invalid moneyline {g.away_team}@{g.home_team}: \"\n                            f\"{g.away_moneyline}/{g.home_moneyline}\"\n                        )\n                    prob=no_vig_home(away_ml,home_ml)\n"""
if old not in refresh_text:
    raise SystemExit("Expected clean market_refresh.py calculation block not found")
refresh.write_text(refresh_text.replace(old, new, 1), encoding="utf-8")

provider_text = provider.read_text(encoding="utf-8")
old_append_away = "away_prices.append(int(prices[event['away_team']]))"
old_append_home = "home_prices.append(int(prices[event['home_team']]))"
provider_text = provider_text.replace(old_append_away, "away_prices.append(float(prices[event['away_team']]))")
provider_text = provider_text.replace(old_append_home, "home_prices.append(float(prices[event['home_team']]))")

old_game = "_median(away_prices),_median(home_prices),_median(totals) if totals else None"
new_game = "_consensus_moneyline(away_prices),_consensus_moneyline(home_prices),_median(totals) if totals else None"
if old_game not in provider_text:
    raise SystemExit("Expected MarketGame consensus block not found in provider")
provider_text = provider_text.replace(old_game, new_game, 1)

marker = """def _median(values):\n    values=sorted(values); n=len(values); mid=n//2\n    return values[mid] if n%2 else (values[mid-1]+values[mid])/2\n"""
replacement = """def _implied_probability(moneyline):\n    value = float(moneyline)\n    if abs(value) < 50:\n        raise ValueError(f\"Invalid American moneyline: {moneyline}\")\n    return 100.0 / (value + 100.0) if value > 0 else (-value) / ((-value) + 100.0)\n\ndef _american_from_probability(probability):\n    p = float(probability)\n    if not 0.0 < p < 1.0:\n        raise ValueError(f\"Invalid implied probability: {probability}\")\n    line = -100.0 * p / (1.0 - p) if p >= 0.5 else 100.0 * (1.0 - p) / p\n    return int(round(line))\n\ndef _consensus_moneyline(values):\n    valid = [float(v) for v in values if v is not None and abs(float(v)) >= 50]\n    if not valid:\n        raise ValueError(\"No valid American moneylines returned\")\n    probabilities = [_implied_probability(v) for v in valid]\n    return _american_from_probability(_median(probabilities))\n\ndef _median(values):\n    values=sorted(values); n=len(values); mid=n//2\n    return values[mid] if n%2 else (values[mid-1]+values[mid])/2\n"""
if marker not in provider_text:
    raise SystemExit("Expected _median function not found in provider")
provider.write_text(provider_text.replace(marker, replacement, 1), encoding="utf-8")

py_compile.compile(str(provider), doraise=True)
py_compile.compile(str(refresh), doraise=True)

# Lightweight deterministic checks. Arithmetic averaging of +101 and -113
# used to produce -6; probability-space consensus must remain a valid line.
import importlib.util
spec = importlib.util.spec_from_file_location("odds_provider_fixed", provider)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for values in ([101, -113], [105, -108, -110, 102], [-120, -122]):
    line = module._consensus_moneyline(values)
    if abs(line) < 50:
        raise SystemExit(f"Consensus test failed for {values}: {line}")
print("PASS: provider consensus uses implied-probability space")
print("PASS: invalid near-zero moneylines cannot reach no-vig calculation")
print("PASS: market_refresh.py and provider compile")

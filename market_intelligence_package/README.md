# Market Intelligence Package

Automated weekly straight-up recommendations using NFL moneylines/totals, Elo, and situational adjustments. Crowd percentages are not required.

## Install
```bash
python market_intelligence_package/install_market_intelligence.py /home/deeoriginalone/fantasy-intelligence
cd /home/deeoriginalone/fantasy-intelligence
cp .env.market.example .env.market
```
Set `ODDS_API_KEY` directly in `.env.market`, then protect it with `chmod 600 .env.market` and add `.env.market` to `.gitignore`.

## Dry run
```bash
set -a; source .env.market; set +a
python market_refresh.py --dry-run
```

## Live refresh
```bash
python market_refresh.py
```
Open `/market-intelligence` after restarting Flask.

The package reads provider request headers when available and stores request cost and remaining credits in PostgreSQL. Dashboard views use cached rows and do not call the provider.

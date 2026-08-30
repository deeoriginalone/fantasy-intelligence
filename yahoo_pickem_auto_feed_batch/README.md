# Yahoo Pick'em Auto Feed

Automatic provider framework for crowd percentages and market odds. It does not scrape Yahoo or invent data. Configure approved normalized JSON endpoints in `.env.pickem`, then run `python pickem_auto_feed.py --dry-run` and `python pickem_auto_feed.py`.

## Install
```bash
python yahoo_pickem_auto_feed_batch/install_pickem_auto_feed.py /home/deeoriginalone/fantasy-intelligence
cp .env.pickem.example .env.pickem
```

## Validate configuration
```bash
set -a; source .env.pickem; set +a
python pickem_auto_feed.py --dry-run
```

## Run
```bash
python pickem_auto_feed.py
```

## Scheduler
Systemd templates are included under `scheduler/`. Copy them to `/etc/systemd/system/` only if that matches your server operations policy, then enable `pickem-refresh.timer`.

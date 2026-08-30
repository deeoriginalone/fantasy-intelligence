# Pick'em Input Center

Adds an in-dashboard form at `/pickem/inputs` so weekly Yahoo percentages and American moneylines can be entered without editing CSV files. The form converts both moneylines to a no-vig home probability, saves PostgreSQL inputs, and redirects to the Pick'em Center, which generates predictions.

## Install

```bash
python yahoo_pickem_input_center_batch/install_pickem_input_center.py /home/deeoriginalone/fantasy-intelligence
```

## Verify

```bash
python -m py_compile pickem_inputs_routes.py app.py
```

Restart the Flask service and visit `/pickem/inputs`.

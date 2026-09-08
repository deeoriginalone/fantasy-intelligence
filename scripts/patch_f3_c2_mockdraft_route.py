#!/usr/bin/env python3
"""Patch app.py with guarded mock-draft recommendation publication.

The patch is anchor-based, creates a backup, and refuses partial or repeated
application. Runtime enforcement is enabled only when
F3_READINESS_REPORT_PATH points to an existing readiness JSON report.
If the variable is set but loading fails, recommendations fail closed.
"""

from datetime import datetime, timezone
from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

import_anchor = "from sleeper_recommendation_overlay import build_recommendation_overlay\n"
imports = (
    "from services.draft_recommendation_publication import "
    "DraftRecommendationPublicationService\n"
    "from services.readiness_report_io import load_readiness_report\n"
)
old_route = "    recs=mock_recommendations(cur,(d[0],d[2],d[3],d[4],d[5],d[9])) if d[8]!='complete' else []\n"
new_route = """    raw_recs=mock_recommendations(cur,(d[0],d[2],d[3],d[4],d[5],d[9])) if d[8]!='complete' else []
    readiness_path=os.environ.get('F3_READINESS_REPORT_PATH','').strip()
    recommendation_publication=None
    if readiness_path:
        try:
            readiness_report=load_readiness_report(readiness_path)
            recommendation_publication=DraftRecommendationPublicationService().guard(
                raw_recs, readiness_report,
                metadata={'draft_id':draft_id,'current_pick':d[9]},
            )
            recs=list(recommendation_publication.recommendations)
        except Exception as exc:
            app.logger.exception('Unable to enforce draft recommendation publication gate')
            recs=[]
            recommendation_publication={
                'publish_allowed':False,
                'status':'BLOCKED',
                'blockers':['READINESS_GATE_ERROR'],
                'error':str(exc),
            }
    else:
        recs=raw_recs
"""
old_render = "    return render_template('mockdraft_live.html',title=d[1],draft=d,recommendations=recs,recent_picks=recent,counts=counts,current_round=current_round,current_slot=current_slot,next_pick=next_pick,strategy_profile=STRATEGY_PROFILES.get(d[2],STRATEGY_PROFILES[DEFAULT_STRATEGY]))\n"
new_render = "    return render_template('mockdraft_live.html',title=d[1],draft=d,recommendations=recs,recommendation_publication=recommendation_publication,recent_picks=recent,counts=counts,current_round=current_round,current_slot=current_slot,next_pick=next_pick,strategy_profile=STRATEGY_PROFILES.get(d[2],STRATEGY_PROFILES[DEFAULT_STRATEGY]))\n"

if imports in text or "recommendation_publication=recommendation_publication" in text:
    raise SystemExit("ERROR: F3-C.2 patch appears to be already applied")
for label, anchor in (("import", import_anchor), ("route", old_route), ("render", old_render)):
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"ERROR: Expected exactly one {label} anchor, found {count}")
if "import os\n" not in text:
    raise SystemExit("ERROR: app.py does not contain the expected 'import os' dependency")

backup = Path(f"app.py.before_f3c2_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
backup.write_text(text, encoding="utf-8")
text = text.replace(import_anchor, import_anchor + imports)
text = text.replace(old_route, new_route)
text = text.replace(old_render, new_render)
APP.write_text(text, encoding="utf-8")
print(f"Patched: {APP}")
print(f"Backup: {backup}")

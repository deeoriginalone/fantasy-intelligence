import os
import psycopg
from psycopg.rows import dict_row
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .simulator import DATABASE_URL, STRATEGIES, simulate, run_many

mocklab_bp=Blueprint("mocklab",__name__,template_folder="templates")

@mocklab_bp.get("/mocklab")
def index():
    with psycopg.connect(DATABASE_URL,row_factory=dict_row) as conn:
        drafts=conn.execute("SELECT * FROM mock_drafts ORDER BY created_at DESC LIMIT 20").fetchall()
        size=conn.execute("SELECT COALESCE(team_count,12) team_count FROM league_info LIMIT 1").fetchone()["team_count"]
    return render_template("mocklab.html",drafts=drafts,strategies=STRATEGIES,league_size=size)

@mocklab_bp.post("/mocklab/run")
def run():
    slot=int(request.form.get("slot",1)); strategy=request.form.get("strategy","balanced"); runs=int(request.form.get("runs",1))
    try:
        result=run_many(min(max(runs,1),1000),slot,strategy)
        flash(f"Completed {result['runs']} drafts. Average grade: {result['average_grade']}","success")
    except Exception as e: flash(str(e),"danger")
    return redirect(url_for("mocklab.index"))

@mocklab_bp.get("/mocklab/<int:draft_id>")
def detail(draft_id):
    with psycopg.connect(DATABASE_URL,row_factory=dict_row) as conn:
        draft=conn.execute("SELECT * FROM mock_drafts WHERE id=%s",(draft_id,)).fetchone()
        picks=conn.execute("SELECT * FROM mock_picks WHERE draft_id=%s ORDER BY overall_pick",(draft_id,)).fetchall()
    return render_template("mocklab_detail.html",draft=draft,picks=picks)

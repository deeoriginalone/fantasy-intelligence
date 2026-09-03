from services.draft_recommendation_service import rank_candidates as rank_draft_candidates
from survival_calibration import build_comparison as build_survival_comparison, create_blueprint as survival_calibration_blueprint, persist as persist_survival_comparison
from monte_carlo_survival import blueprint as monte_carlo_survival_blueprint, enhance as enhance_monte_carlo_survival, persist as persist_monte_carlo_survival
from recommendation_explainer import build_explanation, blueprint as recommendation_blueprint, persist as persist_explanation
from draft_operations_hardening import blueprint,track,undo
from draft_state_hardening import build_hardened_sync, create_blueprint
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from auth import admin_required, csrf_required, ensure_csrf_token
from config import Config
from draft_readiness import build_draft_readiness, validate_runtime
from draft_health_routes import create_draft_health_blueprint
from scarcity_model import calculate_dynamic_scarcity, scarcity_distribution
from candidate_filter import filter_candidate_pool
from model_calibration import model_health
from adaptive_draft_reconciliation import apply_calibrated_reconciliation
from draft_outcome_tracker import log_and_resolve
from draft_accuracy_routes import create_draft_accuracy_blueprint
from draft_outcome_health import create_outcome_health_blueprint
from post_draft_transition import create_post_draft_blueprint
from sleeper_opponent_forecast import reconcile_opponent_forecast
from dynamic_need_model import calculate_dynamic_need
from balanced_recommendation_score import calculate_balanced_score
from recommendation_engine_audit import audit_recommendation_candidates
from draft_decision_plan import build_decision_plan, fuse_decision_plan
from reconciled_draft_decision import reconcile_draft_now_wait
from draft_coach_sleeper_fusion import fuse_sleeper_context
from player_survival_probability import estimate_player_survival
from sleeper_recommendation_overlay import build_recommendation_overlay
from services.roster_slots import build_roster_slots
from services.draft_recommendation_publication import DraftRecommendationPublicationService
from services.readiness_report_io import load_readiness_report
from sleeper_draft_signals import build_sleeper_draft_signals
from sleeper_intelligence_routes import create_sleeper_intelligence_blueprint
from sleeper_hub import create_sleeper_hub_blueprint
from owner_operations import create_owner_operations_blueprint
from season_sandbox import create_sandbox_blueprint
from werkzeug.utils import secure_filename
from services.sleeper_service import (
    get_league,
    get_users,
    get_rosters,
    get_draft,
    get_draft_picks,
    get_all_players,
)
import os
import re
import unicodedata
import random

import psycopg2

from services.import_rankings import import_rankings
from market_routes import market_bp
from survivor_routes import survivor_bp
from intelligence_operations_routes import create_intelligence_operations_blueprint
from draft_events.runtime import process_runtime_picks


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

@app.context_processor
def inject_csrf_token():
    return {"csrf_token": lambda: ensure_csrf_token()}

@app.before_request
def _ensure_session_csrf():
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        ensure_csrf_token()

app.register_blueprint(market_bp)
app.register_blueprint(survivor_bp)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SLEEPER_LEAGUE_ID = Config.SLEEPER_LEAGUE_ID
SLEEPER_DRAFT_ID = Config.SLEEPER_DRAFT_ID
MONTE_CARLO_SIMULATIONS = 500

# Strategic final-roster targets used by the Draft Agent.
# K and DEF remain outside this offensive recommendation model.
STRATEGY_PROFILES = {
    "BEST_AVAILABLE": {
        "label": "Best Available",
        "description": "No positional bias. Let value, need, scarcity, and tiers decide.",
    },
    "HERO_RB": {
        "label": "Hero RB",
        "description": "Prioritize an elite running back early, then build wide receiver depth.",
    },
    "ZERO_RB": {
        "label": "Zero RB",
        "description": "Prioritize wide receivers and tight end early; delay running back.",
    },
    "WR_HEAVY": {
    "label": "WR Heavy",
    "description": (
        "Use wide receiver as the preferred early-round tiebreaker "
        "while preserving best-player-available flexibility."
        ),
    },
    "ELITE_TE": {
        "label": "Elite TE",
        "description": "Aggressively target a premium tight end in the first four rounds.",
    },
}
DEFAULT_STRATEGY = "BEST_AVAILABLE"


def get_strategy_bonus(strategy, position, current_round):
    if strategy == "WR_HEAVY":
        if current_round <= 5 and position == "WR":
            return 18
        return 0

    if strategy == "HERO_RB":
        if current_round <= 3 and position == "RB":
            return 50
        if current_round <= 3 and position == "WR":
            return 15
        return 0

    if strategy == "ZERO_RB":
        if current_round <= 5 and position == "WR":
            return 50
        if current_round <= 5 and position == "TE":
            return 25
        if current_round <= 5 and position == "RB":
            return -25
        return 0

    if strategy == "ELITE_TE":
        if current_round <= 4 and position == "TE":
            return 75
        return 0

    return 0


ROSTER_TARGETS = {
    "QB": 2,
    "RB": 5,
    "WR": 5,
    "TE": 2,
}


MOCK_ROSTER_TARGETS = {
    "QB": 2,
    "RB": 4,
    "WR": 4,
    "TE": 2,
    "K": 1,
    "DEF": 1,
}

def get_db_connection():
    return psycopg2.connect(**Config.db_kwargs())


def get_local_league():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT league_name, team_name, teams, scoring_type
        FROM league_info
        LIMIT 1
        """
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_player_tier(overall_rank):
    """Group overall ranks into draft-value tiers."""
    if overall_rank <= 12:
        return 1
    if overall_rank <= 24:
        return 2
    if overall_rank <= 50:
        return 3
    if overall_rank <= 100:
        return 4
    return 5

def get_actual_player_tier(player):
    """
    Prefer imported VBD tier from database.
    Fallback to rank-based tier if missing.
    """
    try:
        tier = player[7]
        if tier is not None:
            tier = int(tier)
            if 1 <= tier <= 20:
                return tier
    except (IndexError, TypeError, ValueError):
        pass

    return get_player_tier(player[0])


def build_pick_forecast(available_players, scarcity):
    """Estimate availability at the user's next Sleeper pick."""
    forecast = {
        "current_pick": 0,
        "next_pick": None,
        "picks_until_next": None,
        "projected_gone": {position: 0 for position in ["QB", "RB", "WR", "TE"]},
        "projected_remaining": dict(scarcity),
    }

    try:
        draft = get_draft(SLEEPER_DRAFT_ID)
        users = get_users(SLEEPER_LEAGUE_ID) or []
        rosters = get_rosters(SLEEPER_LEAGUE_ID) or []
        picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        forecast["current_pick"] = len(picks)

        owner_ids = {
            str(user.get("user_id"))
            for user in users
            if user.get("is_owner") is True
        }
        my_roster_ids = {
            roster.get("roster_id")
            for roster in rosters
            if str(roster.get("owner_id")) in owner_ids
        }

        slot_to_roster = draft.get("slot_to_roster_id") or {}
        my_slot = next(
            (
                int(slot)
                for slot, roster_id in slot_to_roster.items()
                if roster_id in my_roster_ids
            ),
            None,
        )
        teams = int((draft.get("settings") or {}).get("teams") or 0)
        rounds = int((draft.get("settings") or {}).get("rounds") or 0)

        if my_slot and teams and rounds:
            own_picks = []
            for round_number in range(1, rounds + 1):
                if draft.get("type") == "snake" and round_number % 2 == 0:
                    slot_in_round = teams - my_slot + 1
                else:
                    slot_in_round = my_slot
                own_picks.append((round_number - 1) * teams + slot_in_round)

            next_pick = next(
                (pick for pick in own_picks if pick > forecast["current_pick"]),
                None,
            )
            forecast["next_pick"] = next_pick

            if next_pick is not None:
                picks_until_next = max(0, next_pick - forecast["current_pick"] - 1)
                forecast["picks_until_next"] = picks_until_next

                projected_players = available_players[:picks_until_next]
                for player in projected_players:
                    position = player[2]
                    if position in forecast["projected_gone"]:
                        forecast["projected_gone"][position] += 1

                forecast["projected_remaining"] = {
                    position: max(
                        0,
                        scarcity.get(position, 0)
                        - forecast["projected_gone"].get(position, 0),
                    )
                    for position in ["QB", "RB", "WR", "TE"]
                }
    except Exception as exc:
        forecast["error"] = str(exc)

    return forecast


def build_league_tendencies():
    """Summarize positional behavior from completed Sleeper draft picks."""
    positions = ["QB", "RB", "WR", "TE"]
    result = {
        "counts": {position: 0 for position in positions},
        "percentages": {position: 0.0 for position in positions},
        "bias": {position: "LOW" for position in positions},
        "bonus": {position: 0 for position in positions},
        "total": 0,
        "sample_status": "NO DATA",
        "expected_next_run": None,
    }

    try:
        picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        for pick in picks:
            metadata = pick.get("metadata") or {}
            position = metadata.get("position")
            if position in result["counts"]:
                result["counts"][position] += 1
                result["total"] += 1

        if result["total"] == 0:
            return result

        if result["total"] < 10:
            result["sample_status"] = "EARLY SAMPLE"
        elif result["total"] < 30:
            result["sample_status"] = "DEVELOPING"
        else:
            result["sample_status"] = "ESTABLISHED"

        for position in positions:
            count = result["counts"][position]
            percentage = round(count / result["total"] * 100, 1)
            result["percentages"][position] = percentage

            if percentage >= 40:
                result["bias"][position] = "HIGH"
                result["bonus"][position] = 25
            elif percentage >= 25:
                result["bias"][position] = "MEDIUM"
                result["bonus"][position] = 12
            else:
                result["bias"][position] = "LOW"
                result["bonus"][position] = 0

        result["expected_next_run"] = max(
            positions,
            key=lambda position: (
                result["percentages"][position],
                result["counts"][position],
            ),
        )
    except Exception as exc:
        result["error"] = str(exc)

    return result


def build_opponent_forecast(available_players, scarcity, league_tendencies=None):
    """Simulate picks before the user's next turn using opponent roster needs."""
    league_tendencies = league_tendencies or {"bonus": {}}

    result = {
        "current_pick": 0,
        "next_pick": None,
        "picks_until_next": None,
        "teams_before_next_pick": [],
        "position_pressure": {
            position: 0 for position in ["QB", "RB", "WR", "TE"]
        },
        "teams_needing_position": {
            position: 0 for position in ["QB", "RB", "WR", "TE"]
        },
        "projected_gone": {
            position: 0 for position in ["QB", "RB", "WR", "TE"]
        },
        "projected_remaining": dict(scarcity),
        "projected_picks": [],
    }

    try:
        draft = get_draft(SLEEPER_DRAFT_ID)
        users = get_users(SLEEPER_LEAGUE_ID) or []
        rosters = get_rosters(SLEEPER_LEAGUE_ID) or []
        picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        result["current_pick"] = len(picks)

        users_by_id = {
            str(user.get("user_id")): user for user in users
        }
        team_by_roster = {}
        my_roster_ids = set()
        for sleeper_roster in rosters:
            roster_id = sleeper_roster.get("roster_id")
            owner_id = str(sleeper_roster.get("owner_id") or "")
            user = users_by_id.get(owner_id, {})
            metadata = user.get("metadata") or {}
            team_by_roster[roster_id] = (
                metadata.get("team_name")
                or user.get("display_name")
                or f"Roster {roster_id}"
            )
            if user.get("is_owner") is True:
                my_roster_ids.add(roster_id)

        slot_to_roster = {
            int(slot): roster_id
            for slot, roster_id in (draft.get("slot_to_roster_id") or {}).items()
        }
        roster_to_slot = {
            roster_id: slot for slot, roster_id in slot_to_roster.items()
        }
        teams = int((draft.get("settings") or {}).get("teams") or 0)
        rounds = int((draft.get("settings") or {}).get("rounds") or 0)
        my_roster_id = next(iter(my_roster_ids), None)
        my_slot = roster_to_slot.get(my_roster_id)

        if not (teams and rounds and my_slot):
            return result

        own_pick_numbers = []
        for round_number in range(1, rounds + 1):
            if draft.get("type") == "snake" and round_number % 2 == 0:
                slot_in_round = teams - my_slot + 1
            else:
                slot_in_round = my_slot
            own_pick_numbers.append(
                (round_number - 1) * teams + slot_in_round
            )

        result["next_pick"] = next(
            (
                pick_number
                for pick_number in own_pick_numbers
                if pick_number > result["current_pick"]
            ),
            None,
        )
        if result["next_pick"] is None:
            return result

        result["picks_until_next"] = max(
            0,
            result["next_pick"] - result["current_pick"] - 1,
        )

        roster_counts = {
            roster_id: {
                position: 0 for position in ["QB", "RB", "WR", "TE"]
            }
            for roster_id in roster_to_slot
        }
        drafted_names = set()
        for pick in picks:
            roster_id = pick.get("roster_id")
            metadata = pick.get("metadata") or {}
            position = metadata.get("position")
            if roster_id in roster_counts and position in roster_counts[roster_id]:
                roster_counts[roster_id][position] += 1
            first_name = (metadata.get("first_name") or "").strip()
            last_name = (metadata.get("last_name") or "").strip()
            full_name = " ".join(
                part for part in [first_name, last_name] if part
            ).strip()
            if full_name:
                drafted_names.add(full_name.lower())

        simulated_pool = [
            player
            for player in available_players
            if player[1].lower() not in drafted_names
            and player[2] in ROSTER_TARGETS
        ]

        future_pick_numbers = range(
            result["current_pick"] + 1,
            result["next_pick"],
        )
        teams_seen = set()

        for overall_pick in future_pick_numbers:
            round_number = ((overall_pick - 1) // teams) + 1
            position_in_round = ((overall_pick - 1) % teams) + 1
            if draft.get("type") == "snake" and round_number % 2 == 0:
                draft_slot = teams - position_in_round + 1
            else:
                draft_slot = position_in_round

            roster_id = slot_to_roster.get(draft_slot)
            if roster_id is None or not simulated_pool:
                continue

            team_name = team_by_roster.get(roster_id, f"Roster {roster_id}")
            if roster_id not in teams_seen:
                result["teams_before_next_pick"].append(team_name)
                teams_seen.add(roster_id)

            counts = roster_counts.setdefault(
                roster_id,
                {position: 0 for position in ROSTER_TARGETS},
            )
            need_pressure = {
                position: int(
                    max(0, target - counts.get(position, 0))
                    / target
                    * 100
                ) if target else 0
                for position, target in ROSTER_TARGETS.items()
            }

            for position, pressure in need_pressure.items():
                if pressure >= 60:
                    result["teams_needing_position"][position] += 1

            candidate_window = simulated_pool[:40]
            best_player = max(
                candidate_window,
                key=lambda player: (
                    max(0, 101 - player[0])
                    + need_pressure.get(player[2], 0)
                    + (league_tendencies.get("bonus") or {}).get(player[2], 0)
                    + (
                        35
                        if counts.get(player[2], 0) == 0
                        and player[2] in ["QB", "TE"]
                        else 0
                    )
                ),
            )
            simulated_pool.remove(best_player)
            position = best_player[2]
            counts[position] = counts.get(position, 0) + 1
            result["projected_gone"][position] += 1
            result["position_pressure"][position] += need_pressure.get(position, 0)
            result["projected_picks"].append(
                {
                    "overall_pick": overall_pick,
                    "team": team_name,
                    "player": best_player[1],
                    "position": position,
                    "rank": best_player[0],
                }
            )

        result["projected_remaining"] = {
            position: max(
                0,
                scarcity.get(position, 0)
                - result["projected_gone"].get(position, 0),
            )
            for position in ["QB", "RB", "WR", "TE"]
        }

        for position in result["position_pressure"]:
            projected = result["projected_gone"][position]
            needy_teams = result["teams_needing_position"][position]
            result["position_pressure"][position] = (
                projected * 25 + needy_teams * 10
            )

    except Exception as exc:
        result["error"] = str(exc)

    return result


def build_draft_now_wait_analysis(
    recommendation,
    top_recommendations,
    pick_forecast,
    tier_counts,
    need_score,
):
    """Estimate whether the recommended player can survive until the next pick."""
    analysis = {
        "decision": "DRAFT NOW",
        "risk_level": "HIGH",
        "survival_probability": 0,
        "next_pick": pick_forecast.get("next_pick"),
        "picks_until_next": pick_forecast.get("picks_until_next"),
        "reasons": [],
    }

    if not recommendation:
        analysis.update(
            decision="NO RECOMMENDATION",
            risk_level="UNKNOWN",
            survival_probability=0,
        )
        analysis["reasons"].append("No available recommendation could be scored.")
        return analysis

    if not pick_forecast.get("next_pick"):
        analysis.update(
            decision="DRAFT NOW",
            risk_level="UNKNOWN",
            survival_probability=0,
        )
        analysis["reasons"].append(
            "Sleeper has not exposed a usable next-pick forecast."
        )
        return analysis

    player_name = recommendation[1]
    position = recommendation[2]
    overall_rank = recommendation[0]
    picks_until_next = int(pick_forecast.get("picks_until_next") or 0)
    projected_picks = pick_forecast.get("projected_picks") or []
    projected_names = {
        str(pick.get("player") or "").lower()
        for pick in projected_picks
    }
    projected_position_picks = int(
        (pick_forecast.get("projected_gone") or {}).get(position, 0)
    )
    needy_teams = int(
        (pick_forecast.get("teams_needing_position") or {}).get(position, 0)
    )

    tier = get_actual_player_tier(recommendation)
    tier_remaining = int(tier_counts.get(position, {}).get(tier, 0))

    score = 82
    if player_name.lower() in projected_names:
        score -= 65
        analysis["reasons"].append(
            "The opponent model projects this player to be selected before your next pick."
        )
    if overall_rank <= picks_until_next + 3:
        score -= 25
        analysis["reasons"].append(
            "Overall rank places the player inside the expected selection window."
        )
    if projected_position_picks >= 2:
        score -= min(30, projected_position_picks * 10)
        analysis["reasons"].append(
            f"The model projects {projected_position_picks} {position} selections before your next pick."
        )
    if needy_teams >= 3:
        score -= min(20, needy_teams * 4)
        analysis["reasons"].append(
            f"{needy_teams} opponents show meaningful {position} demand."
        )
    if tier_remaining <= 2:
        score -= 30
        analysis["reasons"].append(
            f"Only {tier_remaining} Tier-{tier} {position} players remain."
        )
    elif tier_remaining <= 4:
        score -= 15
        analysis["reasons"].append(
            f"The current Tier-{tier} {position} group is nearly depleted."
        )
    if need_score.get(position, 0) >= 75:
        score -= 10
        analysis["reasons"].append(
            f"{position} remains a major roster need."
        )

    score = max(0, min(100, score))
    analysis["survival_probability"] = score

    if score <= 35:
        analysis["decision"] = "DRAFT NOW"
        analysis["risk_level"] = "HIGH"
    elif score <= 65:
        analysis["decision"] = "LEAN DRAFT NOW"
        analysis["risk_level"] = "MEDIUM"
    else:
        analysis["decision"] = "WAIT MAY BE SAFE"
        analysis["risk_level"] = "LOW"

    if not analysis["reasons"]:
        analysis["reasons"].append(
            "Opponent demand and tier pressure are currently limited."
        )

    return analysis


def run_monte_carlo_availability(
    available_players,
    top_recommendations,
    pick_forecast,
    league_tendencies,
    simulations=MONTE_CARLO_SIMULATIONS,
):
    """Estimate Top-5 availability using weighted, reproducible simulations."""
    results = {
        "simulations": simulations,
        "picks_until_next": int(pick_forecast.get("picks_until_next") or 0),
        "players": [],
        "status": "READY",
    }

    if not top_recommendations:
        results["status"] = "NO CANDIDATES"
        return results

    if not pick_forecast.get("next_pick"):
        results["status"] = "NO NEXT PICK"
        return results

    picks_until_next = results["picks_until_next"]
    if picks_until_next <= 0:
        for candidate in top_recommendations:
            player = candidate["player"]
            results["players"].append(
                {
                    "player": player[1],
                    "position": player[2],
                    "rank": player[0],
                    "available_count": simulations,
                    "availability_pct": 100.0,
                    "risk": "LOW",
                }
            )
        return results

    offensive_pool = [
        player
        for player in available_players
        if player[2] in ROSTER_TARGETS
    ]
    targets = {
        candidate["player"][1]: candidate
        for candidate in top_recommendations
    }
    survived = {name: 0 for name in targets}

    league_bonus = league_tendencies.get("bonus") or {}
    pressure = pick_forecast.get("position_pressure") or {}
    projected_gone = pick_forecast.get("projected_gone") or {}
    seed_value = (
        int(pick_forecast.get("current_pick") or 0) * 1009
        + len(offensive_pool) * 37
        + picks_until_next
    )
    rng = random.Random(seed_value)

    for _ in range(simulations):
        pool = list(offensive_pool)
        drafted_names = set()

        for pick_index in range(picks_until_next):
            if not pool:
                break

            candidate_window = pool[: min(60, len(pool))]
            weights = []
            for player in candidate_window:
                rank, _, position, _ = player[:4]
                rank_weight = max(2, 125 - min(rank, 123))
                tendency_weight = league_bonus.get(position, 0)
                pressure_weight = int(pressure.get(position, 0) / 5)
                run_weight = projected_gone.get(position, 0) * 5
                tier = get_actual_player_tier(player)
                tier_remaining = sum(
                    1
                    for pool_player in pool
                    if pool_player[2] == position
                    and get_actual_player_tier(pool_player) == tier
                )
                tier_weight = 20 if tier_remaining <= 2 else 8 if tier_remaining <= 4 else 0
                noise = rng.uniform(0.85, 1.15)
                weights.append(
                    max(
                        1.0,
                        (
                            rank_weight
                            + tendency_weight
                            + pressure_weight
                            + run_weight
                            + tier_weight
                        )
                        * noise,
                    )
                )

            chosen = rng.choices(candidate_window, weights=weights, k=1)[0]
            pool.remove(chosen)
            drafted_names.add(chosen[1])

        for player_name in targets:
            if player_name not in drafted_names:
                survived[player_name] += 1

    for candidate in top_recommendations:
        player = candidate["player"]
        player_name = player[1]
        availability_pct = round(
            survived[player_name] / simulations * 100,
            1,
        )
        if availability_pct <= 25:
            risk = "HIGH"
        elif availability_pct <= 55:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        results["players"].append(
            {
                "player": player_name,
                "position": player[2],
                "rank": player[0],
                "available_count": survived[player_name],
                "availability_pct": availability_pct,
                "risk": risk,
            }
        )

    return results


def build_value_gap_analysis(
    top_recommendations,
    recommendation_candidates,
    monte_carlo,
):
    """Compare current candidate value with the next option at that position."""
    simulation_by_name = {
        player["player"]: player
        for player in (monte_carlo.get("players") or [])
    }
    analysis = {
        "players": [],
        "best_action": None,
        "status": "READY",
    }

    if not top_recommendations:
        analysis["status"] = "NO CANDIDATES"
        return analysis

    candidates_by_position = {
        position: [] for position in ROSTER_TARGETS
    }
    for candidate in recommendation_candidates:
        position = candidate["player"][2]
        if position in candidates_by_position:
            candidates_by_position[position].append(candidate)

    for candidate in top_recommendations:
        player = candidate["player"]
        player_name = player[1]
        position = player[2]
        position_options = candidates_by_position.get(position, [])
        option_index = next(
            (
                index
                for index, option in enumerate(position_options)
                if option["player"][1] == player_name
            ),
            None,
        )
        next_option = (
            position_options[option_index + 1]
            if option_index is not None
            and option_index + 1 < len(position_options)
            else None
        )

        current_score = candidate["draft_score"]
        next_score = next_option["draft_score"] if next_option else 0
        value_gap = max(0, current_score - next_score)
        simulation = simulation_by_name.get(player_name, {})
        availability_pct = float(simulation.get("availability_pct", 100.0))
        urgency_score = round(
            value_gap + (100.0 - availability_pct) * 0.5,
            1,
        )

        if urgency_score >= 60:
            urgency = "HIGH"
            action = "DRAFT NOW"
        elif urgency_score >= 30:
            urgency = "MEDIUM"
            action = "LEAN DRAFT NOW"
        else:
            urgency = "LOW"
            action = "WAIT MAY BE SAFE"

        row = {
            "player": player_name,
            "position": position,
            "rank": player[0],
            "current_score": current_score,
            "next_option": next_option["player"][1] if next_option else None,
            "next_option_score": next_score,
            "value_gap": value_gap,
            "availability_pct": availability_pct,
            "urgency_score": urgency_score,
            "urgency": urgency,
            "action": action,
        }
        analysis["players"].append(row)

    analysis["players"].sort(
        key=lambda row: (-row["urgency_score"], row["rank"])
    )
    analysis["best_action"] = (
        analysis["players"][0] if analysis["players"] else None
    )
    return analysis


def build_round_plan(
    active_strategy,
    current_round,
    position_counts,
    roster_targets,
):
    """Build an explainable round-by-round plan for the active strategy."""
    plans = {
        "BEST_AVAILABLE": [
            (1, ["RB", "WR"], "Take the strongest elite value."),
            (2, ["RB", "WR", "TE"], "Preserve value while filling a core starter."),
            (3, ["RB", "WR"], "Build running back and wide receiver depth."),
            (4, ["QB", "TE", "RB", "WR"], "Address premium onesie value if available."),
            (5, ["RB", "WR"], "Continue building flexible depth."),
            (6, ["QB", "TE", "RB", "WR"], "Fill remaining offensive gaps."),
        ],
        "WR_HEAVY": [
            (1, ["WR"], "Prefer an elite wide receiver when value is comparable."),
            (2, ["WR", "RB"], "Add another premium receiver or capture clear RB value."),
            (3, ["WR", "RB"], "Build pass-catching strength without forcing position."),
            (4, ["WR", "TE", "QB"], "Use WR as the tiebreaker and monitor premium onesies."),
            (5, ["WR", "RB"], "Add receiver depth or take the strongest value."),
            (6, ["RB", "QB", "TE", "WR"], "Fill remaining starter needs and value gaps."),
        ],
        "HERO_RB": [
            (1, ["RB"], "Secure an elite anchor running back."),
            (2, ["WR"], "Begin building wide receiver depth."),
            (3, ["WR"], "Add another starting-caliber wide receiver."),
            (4, ["WR", "TE"], "Continue receiver depth or capture tight end value."),
            (5, ["QB", "WR"], "Consider quarterback value without forcing it."),
            (6, ["RB", "WR"], "Add depth behind the hero running back."),
        ],
        "ZERO_RB": [
            (1, ["WR", "TE"], "Open with an elite receiver or premium tight end."),
            (2, ["WR", "TE"], "Continue building pass-catching advantage."),
            (3, ["WR"], "Add another high-volume wide receiver."),
            (4, ["WR", "QB", "TE"], "Capture elite onesie value or receiver depth."),
            (5, ["RB", "WR"], "Begin considering value running backs."),
            (6, ["RB"], "Build the first running back wave."),
        ],
        "ELITE_TE": [
            (1, ["TE", "RB", "WR"], "Take an elite tight end if value supports it."),
            (2, ["TE", "RB", "WR"], "Finish the premium tight end objective or take value."),
            (3, ["RB", "WR"], "Build core running back and receiver starters."),
            (4, ["RB", "WR"], "Continue core position depth."),
            (5, ["QB", "RB", "WR"], "Consider quarterback or best core value."),
            (6, ["RB", "WR"], "Add flexible offensive depth."),
        ],
    }

    selected = plans.get(active_strategy, plans["BEST_AVAILABLE"])
    rows = []
    for round_number, preferred_positions, objective in selected:
        target_met = all(
            position_counts.get(position, 0)
            >= min(1, roster_targets.get(position, 1))
            for position in preferred_positions
        )

        if round_number < current_round:
            status = "COMPLETE" if target_met else "MISSED"
        elif round_number == current_round:
            status = "ACTIVE"
        else:
            status = "UPCOMING"

        rows.append(
            {
                "round": round_number,
                "positions": preferred_positions,
                "objective": objective,
                "status": status,
            }
        )

    next_objective = next(
        (row for row in rows if row["round"] >= current_round),
        None,
    )
    target_progress = {
        position: {
            "current": position_counts.get(position, 0),
            "target": target,
            "remaining": max(0, target - position_counts.get(position, 0)),
        }
        for position, target in roster_targets.items()
    }

    return {
        "strategy": active_strategy,
        "current_round": current_round,
        "rounds": rows,
        "next_objective": next_objective,
        "target_progress": target_progress,
    }


def build_expected_value_analysis(
    top_recommendations,
    recommendation_candidates,
    monte_carlo,
):
    """Estimate the recommendation value lost by waiting until the next pick."""
    simulation_by_name = {
        row["player"]: row
        for row in (monte_carlo.get("players") or [])
    }
    candidates_by_position = {
        position: [] for position in ROSTER_TARGETS
    }
    for candidate in recommendation_candidates:
        position = candidate["player"][2]
        if position in candidates_by_position:
            candidates_by_position[position].append(candidate)

    result = {
        "players": [],
        "highest_value_at_risk": None,
        "status": "READY",
    }
    if not top_recommendations:
        result["status"] = "NO CANDIDATES"
        return result

    for candidate in top_recommendations:
        player = candidate["player"]
        player_name = player[1]
        position = player[2]
        current_value = float(candidate["draft_score"])
        position_options = candidates_by_position.get(position, [])

        option_index = next(
            (
                index
                for index, option in enumerate(position_options)
                if option["player"][1] == player_name
            ),
            None,
        )
        fallback = (
            position_options[option_index + 1]
            if option_index is not None
            and option_index + 1 < len(position_options)
            else None
        )
        fallback_name = fallback["player"][1] if fallback else None
        fallback_value = float(fallback["draft_score"]) if fallback else 0.0

        simulation = simulation_by_name.get(player_name, {})
        availability_pct = float(simulation.get("availability_pct", 100.0))
        survival_probability = max(0.0, min(1.0, availability_pct / 100.0))

        expected_future_value = round(
            survival_probability * current_value
            + (1.0 - survival_probability) * fallback_value,
            1,
        )
        expected_value_loss = round(
            max(0.0, current_value - expected_future_value),
            1,
        )
        ev_priority_score = round(current_value + expected_value_loss, 1)

        if expected_value_loss >= 60:
            value_risk = "HIGH"
            action = "DRAFT NOW"
        elif expected_value_loss >= 25:
            value_risk = "MEDIUM"
            action = "LEAN DRAFT NOW"
        else:
            value_risk = "LOW"
            action = "WAIT MAY BE SAFE"

        result["players"].append(
            {
                "player": player_name,
                "position": position,
                "rank": player[0],
                "current_value": round(current_value, 1),
                "availability_pct": round(availability_pct, 1),
                "fallback_player": fallback_name,
                "fallback_value": round(fallback_value, 1),
                "expected_future_value": expected_future_value,
                "expected_value_loss": expected_value_loss,
                "ev_priority_score": ev_priority_score,
                "value_risk": value_risk,
                "action": action,
            }
        )

    result["players"].sort(
        key=lambda row: (
            -row["expected_value_loss"],
            -row["ev_priority_score"],
            row["rank"],
        )
    )
    result["highest_value_at_risk"] = (
        result["players"][0] if result["players"] else None
    )
    return result


def build_draft_coach_summary(
    recommendation,
    top_recommendations,
    recommendation_reasons,
    draft_now_wait,
    expected_value_analysis,
    monte_carlo,
    active_strategy,
    current_round,
    pick_forecast,
):
    """Create one concise, explainable draft-coach recommendation."""
    summary = {
        "player": None,
        "position": None,
        "rank": None,
        "draft_score": 0,
        "decision": "NO RECOMMENDATION",
        "confidence": 0,
        "confidence_label": "UNKNOWN",
        "strategy": active_strategy,
        "round": current_round,
        "next_pick": pick_forecast.get("next_pick"),
        "picks_until_next": pick_forecast.get("picks_until_next"),
        "availability_pct": None,
        "value_at_risk": 0,
        "reasons": list(recommendation_reasons[:5]),
    }

    if not recommendation or not top_recommendations:
        summary["reasons"].append("No available player could be scored.")
        return summary

    winner = top_recommendations[0]
    summary.update(
        player=recommendation[1],
        position=recommendation[2],
        rank=recommendation[0],
        draft_score=winner["draft_score"],
        decision=draft_now_wait.get("decision", "DRAFT NOW"),
    )

    simulation = next(
        (
            row
            for row in (monte_carlo.get("players") or [])
            if row["player"] == recommendation[1]
        ),
        None,
    )
    if simulation:
        summary["availability_pct"] = simulation["availability_pct"]

    ev_row = next(
        (
            row
            for row in (expected_value_analysis.get("players") or [])
            if row["player"] == recommendation[1]
        ),
        None,
    )
    if ev_row:
        summary["value_at_risk"] = ev_row["expected_value_loss"]

    score_component = min(35, max(0, winner["draft_score"] / 10))
    scarcity_component = min(15, winner.get("scarcity_score", 0) * 0.15)
    tier_component = min(15, winner.get("tier_bonus", 0) * 0.15)
    value_component = min(20, summary["value_at_risk"] * 0.25)

    availability_component = 0
    if summary["availability_pct"] is not None:
        availability_component = min(
            15,
            (100 - summary["availability_pct"]) * 0.15,
        )

    confidence = round(
        score_component
        + scarcity_component
        + tier_component
        + value_component
        + availability_component
    )
    summary["confidence"] = max(0, min(100, confidence))

    if summary["confidence"] >= 80:
        summary["confidence_label"] = "HIGH"
    elif summary["confidence"] >= 60:
        summary["confidence_label"] = "MEDIUM"
    else:
        summary["confidence_label"] = "LOW"

    if summary["availability_pct"] is not None:
        summary["reasons"].append(
            f"Estimated next-pick availability: "
            f"{summary['availability_pct']}%."
        )
    if summary["value_at_risk"] >= 25:
        summary["reasons"].append(
            f"Waiting puts approximately {summary['value_at_risk']} "
            "recommendation points at risk."
        )

    # Preserve order while removing repeated messages.
    summary["reasons"] = list(dict.fromkeys(summary["reasons"]))[:6]
    return summary


def fetch_available_players(cur):
    cur.execute(
        """
        SELECT p.ranking, p.player_name, p.position, p.nfl_team
        FROM players p
        WHERE NOT EXISTS (
            SELECT 1
            FROM league_rosters lr
            WHERE lr.player_name = p.player_name
        )
          AND NOT EXISTS (
            SELECT 1
            FROM draft_board db
            WHERE db.player_name = p.player_name
              AND db.drafted = true
        )
        ORDER BY p.ranking
        """
    )
    return cur.fetchall()


def normalize_player_name(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def ensure_sleeper_sync_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sleeper_player_map (
            sleeper_player_id VARCHAR(50) PRIMARY KEY,
            sleeper_name VARCHAR(255),
            normalized_name VARCHAR(255),
            position VARCHAR(20),
            nfl_team VARCHAR(20),
            local_player_name VARCHAR(255),
            matched BOOLEAN DEFAULT FALSE,
            synced_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sleeper_draft_picks (
            id SERIAL PRIMARY KEY,
            draft_id VARCHAR(50),
            roster_id INTEGER,
            round_num INTEGER,
            pick_no INTEGER,
            player_id VARCHAR(50),
            player_name VARCHAR(255),
            synced_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        ALTER TABLE sleeper_draft_picks
        ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP DEFAULT NOW()
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sleeper_draft_pick_number_uidx
        ON sleeper_draft_picks (draft_id, pick_no)
        """
    )


def sync_sleeper_player_map():
    sleeper_players = get_all_players() or {}
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        ensure_sleeper_sync_tables(cur)

        cur.execute("SELECT player_name FROM players")
        local_names = [row[0] for row in cur.fetchall()]
        local_by_normalized = {
            normalize_player_name(name): name
            for name in local_names
        }

        matched = 0
        for player_id, player in sleeper_players.items():
            full_name = (
                player.get("full_name")
                or " ".join(
                    part
                    for part in [player.get("first_name"), player.get("last_name")]
                    if part
                )
            ).strip()
            normalized = normalize_player_name(full_name)
            local_player_name = local_by_normalized.get(normalized)
            is_matched = local_player_name is not None
            matched += int(is_matched)

            cur.execute(
                """
                INSERT INTO sleeper_player_map (
                    sleeper_player_id, sleeper_name, normalized_name,
                    position, nfl_team, local_player_name, matched, synced_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (sleeper_player_id)
                DO UPDATE SET
                    sleeper_name = EXCLUDED.sleeper_name,
                    normalized_name = EXCLUDED.normalized_name,
                    position = EXCLUDED.position,
                    nfl_team = EXCLUDED.nfl_team,
                    local_player_name = EXCLUDED.local_player_name,
                    matched = EXCLUDED.matched,
                    synced_at = NOW()
                """,
                (
                    str(player_id),
                    full_name,
                    normalized,
                    player.get("position"),
                    player.get("team"),
                    local_player_name,
                    is_matched,
                ),
            )

        conn.commit()
        return {
            "sleeper_players": len(sleeper_players),
            "matched_to_rankings": matched,
            "unmatched": len(sleeper_players) - matched,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def sync_sleeper_draft_picks():
    picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
    users = get_users(SLEEPER_LEAGUE_ID) or []
    rosters = get_rosters(SLEEPER_LEAGUE_ID) or []

    # F3-A.2 runtime audit persistence. Existing roster/board sync remains authoritative.
    f3a2_event_pipeline = process_runtime_picks(
        get_db_connection,
        picks,
        SLEEPER_LEAGUE_ID,
        SLEEPER_DRAFT_ID,
        rosters,
    )

    users_by_id = {str(user.get("user_id")): user for user in users}
    team_by_roster_id = {}
    my_roster_ids = set()

    for sleeper_roster in rosters:
        roster_id = sleeper_roster.get("roster_id")
        owner_id = str(sleeper_roster.get("owner_id") or "")
        user = users_by_id.get(owner_id, {})
        metadata = user.get("metadata") or {}
        display_name = user.get("display_name") or f"Roster {roster_id}"
        team_by_roster_id[roster_id] = metadata.get("team_name") or display_name
        if user.get("is_owner") is True:
            my_roster_ids.add(roster_id)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        ensure_sleeper_sync_tables(cur)

        matched = 0
        my_team_picks = 0

        for pick in picks:
            metadata = pick.get("metadata") or {}
            player_id = str(pick.get("player_id") or "")
            roster_id = pick.get("roster_id")
            pick_no = pick.get("pick_no")
            round_num = pick.get("round")

            cur.execute(
                """
                SELECT local_player_name, sleeper_name, position
                FROM sleeper_player_map
                WHERE sleeper_player_id = %s
                LIMIT 1
                """,
                (player_id,),
            )
            mapped_player = cur.fetchone()

            if mapped_player:
                local_player_name, sleeper_name, mapped_position = mapped_player
            else:
                first_name = (metadata.get("first_name") or "").strip()
                last_name = (metadata.get("last_name") or "").strip()
                sleeper_name = " ".join(
                    part for part in [first_name, last_name] if part
                ).strip() or player_id
                local_player_name = None
                mapped_position = metadata.get("position")

            if not local_player_name:
                normalized = normalize_player_name(sleeper_name)
                cur.execute(
                    """
                    SELECT player_name, position
                    FROM players
                    WHERE REGEXP_REPLACE(
                        LOWER(player_name), '[^a-z0-9]', '', 'g'
                    ) = %s
                    LIMIT 1
                    """,
                    (normalized,),
                )
                local_player = cur.fetchone()
                if local_player:
                    local_player_name, mapped_position = local_player

            stored_name = local_player_name or sleeper_name
            cur.execute(
                """
                INSERT INTO sleeper_draft_picks (
                    draft_id, roster_id, round_num, pick_no,
                    player_id, player_name, synced_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (draft_id, pick_no)
                DO UPDATE SET
                    roster_id = EXCLUDED.roster_id,
                    round_num = EXCLUDED.round_num,
                    player_id = EXCLUDED.player_id,
                    player_name = EXCLUDED.player_name,
                    synced_at = NOW()
                """,
                (
                    SLEEPER_DRAFT_ID, roster_id, round_num, pick_no,
                    player_id, stored_name,
                ),
            )

            if not local_player_name:
                continue

            matched += 1
            cur.execute(
                """
                INSERT INTO draft_board (player_name, starred, drafted)
                VALUES (%s, false, true)
                ON CONFLICT (player_name)
                DO UPDATE SET drafted = true
                """,
                (local_player_name,),
            )

            team_name = team_by_roster_id.get(roster_id, f"Roster {roster_id}")
            cur.execute(
                """
                INSERT INTO league_teams (team_name)
                VALUES (%s)
                ON CONFLICT DO NOTHING
                """,
                (team_name,),
            )
            cur.execute(
                """
                INSERT INTO league_rosters (team_name, player_name, position)
                SELECT %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM league_rosters WHERE player_name = %s
                )
                """,
                (team_name, local_player_name, mapped_position, local_player_name),
            )

            if roster_id in my_roster_ids:
                my_team_picks += 1
                cur.execute(
                    """
                    INSERT INTO my_roster (player_name, position)
                    SELECT %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM my_roster WHERE player_name = %s
                    )
                    """,
                    (local_player_name, mapped_position, local_player_name),
                )

        conn.commit()
        return {
            "draft_id": SLEEPER_DRAFT_ID,
            "received": len(picks),
            "stored": len(picks),
            "matched_to_rankings": matched,
            "my_team_picks": my_team_picks,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.route("/")
def dashboard():
    league = get_local_league()

    if league is None:
        return render_template(
            "dashboard.html",
            title="Fantasy Intelligence Dashboard",
            league_name="Fantasy Intelligence",
            team_name="Not configured",
            teams="Not configured",
            scoring_type="Not configured",
        )

    return render_template(
        "dashboard.html",
        title="Fantasy Intelligence Dashboard",
        league_name=league[0],
        team_name=league[1],
        teams=league[2],
        scoring_type=league[3],
    )


@app.route("/predraft")
def predraft():
    """Render the slot-five Predraft Intelligence Lab."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ranking,
            player_name,
            UPPER(position),
            nfl_team,
            projected_points,
            tier,
            adp,
            bye_week,
            injury_status
        FROM players
        WHERE UPPER(position) IN ('QB', 'RB', 'WR', 'TE')
        ORDER BY ranking NULLS LAST, player_name
        """
    )
    all_players = cur.fetchall()

    cur.execute(
        """
        SELECT
            COUNT(id),
            COUNT(projected_points),
            COUNT(tier)
        FROM players
        """
    )
    total_players, projection_count, tier_count = cur.fetchone()

    cur.close()
    conn.close()

    def player_dict(row):
        return {
            "ranking": row[0],
            "name": row[1],
            "position": row[2],
            "team": row[3] or "FA",
            "projection": float(row[4] or 0),
            "tier": int(row[5]) if row[5] is not None else None,
            "adp": float(row[6]) if row[6] is not None else None,
            "bye_week": row[7],
            "injury_status": row[8] or "Healthy / Not listed",
        }

    players = [player_dict(row) for row in all_players]
    by_position = {
        position: [player for player in players if player["position"] == position]
        for position in ["QB", "RB", "WR", "TE"]
    }
    top_by_position = {
        position: position_players[:10]
        for position, position_players in by_position.items()
    }
    tier_one = [
        player
        for player in players
        if player["tier"] == 1
    ]
    tier_two = [
        player
        for player in players
        if player["tier"] == 2
    ]

    draft_slot = 5
    league_size = 10
    rounds = 14
    pick_roadmap = []
    for round_number in range(1, rounds + 1):
        slot_in_round = (
            league_size - draft_slot + 1
            if round_number % 2 == 0
            else draft_slot
        )
        overall_pick = (round_number - 1) * league_size + slot_in_round
        pick_roadmap.append(
            {
                "round": round_number,
                "slot": slot_in_round,
                "overall": overall_pick,
                "label": f"{round_number}.{slot_in_round:02d}",
            }
        )

    first_pick_window = [
        player
        for player in players
        if player["ranking"] is not None and player["ranking"] <= 10
    ]
    second_pick_window = [
        player
        for player in players
        if player["ranking"] is not None and 11 <= player["ranking"] <= 22
    ]
    third_pick_window = [
        player
        for player in players
        if player["ranking"] is not None and 20 <= player["ranking"] <= 32
    ]

    readiness = {
        "total_players": int(total_players or 0),
        "projection_count": int(projection_count or 0),
        "tier_count": int(tier_count or 0),
        "projection_pct": round(
            (projection_count or 0) / max(total_players or 1, 1) * 100,
            1,
        ),
        "tier_pct": round(
            (tier_count or 0) / max(total_players or 1, 1) * 100,
            1,
        ),
        "simulations": 30000,
        "strategy": "WR Heavy",
        "draft_slot": draft_slot,
    }

    return render_template(
        "predraft.html",
        title="Predraft Intelligence Lab",
        readiness=readiness,
        pick_roadmap=pick_roadmap,
        tier_one=tier_one,
        tier_two=tier_two,
        top_by_position=top_by_position,
        first_pick_window=first_pick_window,
        second_pick_window=second_pick_window,
        third_pick_window=third_pick_window,
    )


@app.route("/imports", methods=["GET"])
def imports():
    return render_template("imports.html", title="Imports")


@app.route("/imports", methods=["POST"])
@admin_required
def imports_upload():
    uploaded_file = request.files.get("file")

    if uploaded_file is None or not uploaded_file.filename:
        return "No file selected", 400

    filename = secure_filename(uploaded_file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    uploaded_file.save(filepath)
    import_rankings(filepath)

    return f"Imported: {filename}"


@app.route("/agents")
def agents():
    return render_template("agents.html", title="Agents")


@app.route("/draftcenter")
def draftcenter():
    return render_template("draftcenter.html", title="Draft Center")


@app.route("/draftboard/strategy", methods=["POST"])
@admin_required
def set_draft_strategy():
    strategy = request.form.get("strategy", DEFAULT_STRATEGY)
    if strategy not in STRATEGY_PROFILES:
        strategy = DEFAULT_STRATEGY
    session["draft_strategy"] = strategy
    return redirect(url_for("draftboard"))


def get_draftboard_player_tier(player):
    """Return stored positional tier, with rank-tier fallback."""
    return get_actual_player_tier(player)


def calculate_draftboard_tier_gap(
    available_players,
    position,
    current_tier,
):
    """
    Calculate the full-season projection drop from the floor of
    the current positional tier to the ceiling of the next tier.

    Returns None when usable projection or next-tier data is absent.
    """
    current_projections = []
    next_projections = []

    for player in available_players:
        if player[2] != position:
            continue

        try:
            projection = float(player[6] or 0)
        except (IndexError, TypeError, ValueError):
            continue

        if projection <= 0:
            continue

        player_tier = get_draftboard_player_tier(player)

        if player_tier == current_tier:
            current_projections.append(projection)
        elif player_tier == current_tier + 1:
            next_projections.append(projection)

    if not current_projections or not next_projections:
        return None

    current_tier_floor = min(current_projections)
    next_tier_ceiling = max(next_projections)

    return round(
        max(0.0, current_tier_floor - next_tier_ceiling),
        2,
    )


def calculate_draftboard_tier_bonus(
    players_left_in_tier,
    tier_gap,
):
    """
    Weight a tier cliff by both remaining supply and the actual
    projected-point loss to the next positional tier.
    """
    if tier_gap is None:
        if players_left_in_tier <= 2:
            return 15
        if players_left_in_tier <= 4:
            return 8
        return 0

    if players_left_in_tier <= 2 and tier_gap >= 50:
        return 35

    if players_left_in_tier <= 3 and tier_gap >= 25:
        return 20

    if players_left_in_tier <= 4 and tier_gap >= 10:
        return 8

    return 0


@app.route("/draftboard")
def draftboard():
    sleeper_sync_status = None
    sleeper_sync_error = None
    try:
        sleeper_sync_status = sync_sleeper_draft_picks()
    except Exception as exc:
        sleeper_sync_error = str(exc)
        app.logger.warning("Sleeper draft-pick sync failed: %s", exc)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            p.ranking,
            p.player_name,
            p.position,
            p.nfl_team,
            COALESCE(d.starred, false),
            (
                COALESCE(d.drafted, false)
                OR EXISTS (
                    SELECT 1
                    FROM league_rosters lr
                    WHERE lr.player_name = p.player_name
                )
            ) AS drafted,
            COALESCE(p.projected_points, 0) AS projected_points,
            p.tier AS stored_tier,
            COALESCE(p.adp, 999) AS adp
        FROM players p
        LEFT JOIN draft_board d
            ON p.player_name = d.player_name
        ORDER BY p.ranking
        """
    )
    players = cur.fetchall()

    cur.execute(
        """
        SELECT id, player_name, position, COALESCE(slot, '')
        FROM my_roster
        WHERE player_name IS NOT NULL
          AND BTRIM(player_name) <> ''
        ORDER BY drafted_at, id
        """
    )
    roster = cur.fetchall()

    sleeper_draft_signals = build_sleeper_draft_signals(cur, SLEEPER_LEAGUE_ID, season=2026, user_slot=5)


    

    cur.close()
    conn.close()

    roster_names = {player[1] for player in roster}
    available_players = [
        player
        for player in players
        if not player[5] and player[1] not in roster_names
    ]

    scarcity = {}

    for position in ["QB", "RB", "WR", "TE"]:

        remaining = [
            p
            for p in available_players
            if p[2] == position
        ]

        scarcity[position] = len(remaining)

    scarcity_labels = {}

    for position, count in scarcity.items():

        if count <= 20:
            scarcity_labels[position] = "HIGH"

        elif count <= 50:
            scarcity_labels[position] = "MEDIUM"

        else:
            scarcity_labels[position] = "LOW"

    scarcity_score = {}

    for position, label in scarcity_labels.items():
        if label == "HIGH":
            scarcity_score[position] = 100
        elif label == "MEDIUM":
            scarcity_score[position] = 50
        else:
            scarcity_score[position] = 25

    tier_counts = {}
    for position in ["QB", "RB", "WR", "TE"]:
        position_tiers = {
            get_draftboard_player_tier(player)
            for player in available_players
            if player[2] == position
        }

        tier_counts[position] = {
            tier: sum(
                1
                for player in available_players
                if player[2] == position
                and get_draftboard_player_tier(player) == tier
            )
            for tier in position_tiers
        }

    best_available = available_players[0] if available_players else None
    position_leaders = {
        position: next(
            (player for player in available_players if player[2] == position),
            None,
        )
        for position in ["QB", "RB", "WR", "TE"]
    }
    draft_targets = [player for player in available_players if player[4]]
    drafted_count = sum(1 for player in players if player[5])
    roster_slots, bench = build_roster_slots(roster)

    position_counts = {position: 0 for position in ROSTER_TARGETS}
    for roster_player in roster:
        position = roster_player[2]
        if position in position_counts:
            position_counts[position] += 1

    roster_progress = {
        position: {
            "current": position_counts[position],
            "target": target,
            "missing": max(0, target - position_counts[position]),
        }
        for position, target in ROSTER_TARGETS.items()
    }

    needed_positions = []

    for slot, roster_player in roster_slots.items():

        if roster_player is not None:
            continue

        if slot == "FLEX":

            for position in ["RB", "WR", "TE"]:

                if position not in needed_positions:
                    needed_positions.append(position)

        else:

            position = slot.rstrip("12")

            if position not in needed_positions:
                needed_positions.append(position)

    need_score = {}

    for position, target in ROSTER_TARGETS.items():
        current = position_counts[position]
        missing = max(0, target - current)
        need_score[position] = int((missing / target) * 100) if target else 0

    tier_alert = None
    tier_alert_position = None
    tier_alert_tier = None
    tier_alert_remaining = None

    tier_risks = []
    for position in needed_positions:
        leader = next(
            (player for player in available_players if player[2] == position),
            None,
        )
        if leader:
            leader_tier = get_draftboard_player_tier(leader)
            remaining_in_tier = tier_counts[position].get(leader_tier, 0)
            if remaining_in_tier <= 3:
                tier_risks.append(
                    (remaining_in_tier, leader_tier, position)
                )

    if tier_risks:
        (
            tier_alert_remaining,
            tier_alert_tier,
            tier_alert_position,
        ) = min(tier_risks)
        tier_alert = (
            f"Only {tier_alert_remaining} Tier-{tier_alert_tier} "
            f"{tier_alert_position} players remain."
        )

    tier_bonus = {position: 0 for position in ROSTER_TARGETS}
    tier_risk_details = {}

    for position in ROSTER_TARGETS:
        leader = next(
            (player for player in available_players if player[2] == position),
            None,
        )
        if not leader:
            continue

        leader_tier = get_draftboard_player_tier(leader)
        remaining_in_tier = tier_counts[position].get(leader_tier, 0)
        tier_risk_details[position] = {
            "tier": leader_tier,
            "remaining": remaining_in_tier,
        }

        position_tier_gap = calculate_draftboard_tier_gap(
            available_players,
            position,
            leader_tier,
        )
        tier_risk_details[position]["gap"] = position_tier_gap
        tier_bonus[position] = calculate_draftboard_tier_bonus(
            remaining_in_tier,
            position_tier_gap,
        )

    # League tendencies must exist before candidate scoring uses league bonuses.
    league_tendencies = build_league_tendencies()

    active_strategy = session.get(
        "draft_strategy",
        DEFAULT_STRATEGY,
    )
    if active_strategy not in STRATEGY_PROFILES:
        active_strategy = DEFAULT_STRATEGY

    completed_picks = 0
    league_size = 10

    try:
        current_sleeper_picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        completed_picks = len(current_sleeper_picks)

        draft_details = get_draft(SLEEPER_DRAFT_ID)
        league_size = int(
            (draft_details.get("settings") or {}).get("teams") or 10
        )
    except Exception as exc:
        app.logger.warning(
            "Unable to determine Sleeper draft round: %s",
            exc,
        )

    current_round = (completed_picks // max(league_size, 1)) + 1

    recommendation_pool, candidate_pool_audit = filter_candidate_pool(
        available_players,
        current_round=current_round,
    )

    round_plan = build_round_plan(
        active_strategy,
        current_round,
        position_counts,
        ROSTER_TARGETS,
    )

    recommendation_candidates = []

    for player in recommendation_pool:
        position = player[2]
        if position not in ROSTER_TARGETS:
            continue

        player_rank_score = max(0, 101 - player[0])
        legacy_need_score = need_score.get(position, 0)
        dynamic_need = calculate_dynamic_need(
            position, current_round, position_counts, ROSTER_TARGETS, active_strategy,
        )
        player_need_score = dynamic_need["score"]
        legacy_scarcity_score = scarcity_score.get(position, 0)
        dynamic_scarcity = calculate_dynamic_scarcity(
            player, recommendation_pool, current_round, sleeper_draft_signals,
        )
        player_scarcity_score = dynamic_scarcity["score"]
        player_tier = get_draftboard_player_tier(player)
        players_left_in_tier = tier_counts[position].get(player_tier, 0)

        player_tier_gap = calculate_draftboard_tier_gap(
            recommendation_pool,
            position,
            player_tier,
        )
        player_tier_bonus = calculate_draftboard_tier_bonus(
            players_left_in_tier,
            player_tier_gap,
        )

        player_strategy_bonus = get_strategy_bonus(
            active_strategy,
            position,
            current_round,
        )
        player_league_bonus = (
            league_tendencies.get("bonus") or {}
        ).get(position, 0)
        balanced_score = calculate_balanced_score(
            player[0], player_need_score, player_scarcity_score,
            player_tier_bonus, player_strategy_bonus, player_league_bonus,
        )
        player_draft_score = balanced_score["total"]

        recommendation_candidates.append(
            {
                "player": player,
                "rank_score": player_rank_score,
                "legacy_need_score": legacy_need_score,
                "need_details": dynamic_need,
                "need_score": player_need_score,
                "legacy_scarcity_score": legacy_scarcity_score,
                "scarcity_details": dynamic_scarcity,
                "scarcity_score": player_scarcity_score,
                "tier": player_tier,
                "tier_remaining": players_left_in_tier,
                "tier_gap": player_tier_gap,
                "tier_bonus": player_tier_bonus,
                "strategy_bonus": player_strategy_bonus,
                "league_bonus": player_league_bonus,
                "weighted_components": balanced_score,
                "draft_score": player_draft_score,
            }
        )

    recommendation_candidates.sort(
        key=lambda candidate: (
            -candidate["draft_score"],
            candidate["player"][0],
        )
    )
    top_recommendations = recommendation_candidates[:5]
    recommendation_engine_audit = audit_recommendation_candidates(
        recommendation_candidates
    )
    recommendation_engine_audit["candidate_pool"] = candidate_pool_audit
    recommendation_engine_audit["scarcity_distribution"] = scarcity_distribution(recommendation_candidates)
    recommendation_engine_audit=audit_recommendation_candidates(
    recommendation_candidates
    )

    print("RECOMMENDATION AUDIT")
    print(recommendation_engine_audit)

    sleeper_recommendation_overlay = build_recommendation_overlay(
        top_recommendations,
        sleeper_draft_signals,
    )

    player_survival = estimate_player_survival(
        top_recommendations,
        sleeper_draft_signals,
    )
    team_recommendation = (
        top_recommendations[0]["player"]
        if top_recommendations
        else best_available
    )

    rank_score = 0
    agent_draft_score = 0

    if top_recommendations:
        rank_score = top_recommendations[0]["rank_score"]
        agent_draft_score = top_recommendations[0]["draft_score"]

    recommendation_reasons = []

    if team_recommendation:
        recommended_position = team_recommendation[2]
        target = ROSTER_TARGETS.get(recommended_position, 0)
        current = position_counts.get(recommended_position, 0)

        if need_score.get(recommended_position, 0) >= 75:
            recommendation_reasons.append(
                f"{recommended_position} is a major roster need "
                f"({current} of {target} target players rostered)."
            )
        elif need_score.get(recommended_position, 0) >= 40:
            recommendation_reasons.append(
                f"{recommended_position} depth is still below target "
                f"({current} of {target})."
            )
        else:
            recommendation_reasons.append(
                f"{recommended_position} is near the strategic roster target "
                f"({current} of {target})."
            )

        risk = tier_risk_details.get(recommended_position)
        if risk and tier_bonus.get(recommended_position, 0) > 0:
            recommendation_reasons.append(
                f"Only {risk['remaining']} Tier-{risk['tier']} "
                f"{recommended_position} players remain."
            )

        if rank_score >= 75:
            recommendation_reasons.append(
                "Elite overall value remains available."
            )
        elif rank_score >= 40:
            recommendation_reasons.append(
                "The player still offers strong overall value."
            )

        if scarcity_score.get(recommended_position, 0) >= 50:
            recommendation_reasons.append(
                f"Available {recommended_position} depth is shrinking."
            )

    strategy_bonus_for_pick = 0
    if team_recommendation:
        strategy_bonus_for_pick = get_strategy_bonus(
            active_strategy,
            team_recommendation[2],
            current_round,
        )
        if strategy_bonus_for_pick > 0:
            recommendation_reasons.append(
                f"{STRATEGY_PROFILES[active_strategy]['label']} strategy adds "
                f"{strategy_bonus_for_pick} points for "
                f"{team_recommendation[2]} in round {current_round}."
            )
        elif strategy_bonus_for_pick < 0:
            recommendation_reasons.append(
                f"{STRATEGY_PROFILES[active_strategy]['label']} strategy applies "
                f"a {abs(strategy_bonus_for_pick)}-point early-round penalty to "
                f"{team_recommendation[2]}."
            )

    league_bonus_for_pick = 0
    if team_recommendation:
        recommended_position = team_recommendation[2]
        league_bonus_for_pick = (
            league_tendencies.get("bonus") or {}
        ).get(recommended_position, 0)
        position_bias = (
            league_tendencies.get("bias") or {}
        ).get(recommended_position, "LOW")
        position_share = (
            league_tendencies.get("percentages") or {}
        ).get(recommended_position, 0)

        if position_bias == "HIGH":
            recommendation_reasons.append(
                f"This league is drafting {recommended_position} aggressively "
                f"({position_share}% of completed offensive picks)."
            )
        elif position_bias == "MEDIUM":
            recommendation_reasons.append(
                f"League demand for {recommended_position} is elevated "
                f"({position_share}% of completed offensive picks)."
            )

    recommended_tier = (
        get_draftboard_player_tier(team_recommendation)
        if team_recommendation
        else None
    )
    recommended_tier_remaining = (
        tier_counts.get(
            team_recommendation[2],
            {},
        ).get(
            recommended_tier,
            0,
        )
        if team_recommendation and recommended_tier
        else 0
    )
    pick_forecast = build_opponent_forecast(
        recommendation_pool,
        scarcity,
        league_tendencies,
    )

    pick_forecast = reconcile_opponent_forecast(
        pick_forecast,
        sleeper_draft_signals,
    )

    monte_carlo = run_monte_carlo_availability(
        recommendation_pool,
        top_recommendations,
        pick_forecast,
        league_tendencies,
    )

    # === Monte Carlo survival batch 4B ===
    monte_carlo = enhance_monte_carlo_survival(monte_carlo, pick_forecast, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), top_recommendations)
    monte_carlo["run_id"] = persist_monte_carlo_survival(get_db_connection, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), monte_carlo)

    expected_value_analysis = build_expected_value_analysis(
        top_recommendations,
        recommendation_candidates,
        monte_carlo,
    )

    value_gap_analysis = build_value_gap_analysis(
        top_recommendations,
        recommendation_candidates,
        monte_carlo,
    )

    draft_now_wait = build_draft_now_wait_analysis(
        team_recommendation,
        top_recommendations,
        pick_forecast,
        tier_counts,
        need_score,
    )

    draft_now_wait = reconcile_draft_now_wait(
        draft_now_wait, team_recommendation, monte_carlo,
        expected_value_analysis, player_survival, sleeper_draft_signals,
    )

    health_conn = get_db_connection()
    health_cur = health_conn.cursor()
    current_model_health = model_health(health_cur)
    health_cur.close()
    health_conn.close()
    draft_now_wait = apply_calibrated_reconciliation(draft_now_wait, current_model_health)

    draft_decision_plan = build_decision_plan(
        team_recommendation, top_recommendations, expected_value_analysis,
        monte_carlo, player_survival, sleeper_recommendation_overlay, draft_now_wait,
    )

    if team_recommendation and expected_value_analysis.get("players"):
        recommended_ev = next(
            (
                row
                for row in expected_value_analysis["players"]
                if row["player"] == team_recommendation[1]
            ),
            None,
        )
        if recommended_ev and recommended_ev["expected_value_loss"] >= 25:
            recommendation_reasons.append(
                f"Expected-value analysis estimates "
                f"{recommended_ev['expected_value_loss']} points of value at risk "
                "if you wait until the next pick."
            )

    if team_recommendation and value_gap_analysis.get("players"):
        recommended_gap = next(
            (
                row
                for row in value_gap_analysis["players"]
                if row["player"] == team_recommendation[1]
            ),
            None,
        )
        if recommended_gap and recommended_gap["value_gap"] >= 30:
            recommendation_reasons.append(
                f"Value-gap analysis shows a {recommended_gap['value_gap']}-point "
                f"drop to the next {recommended_gap['position']} option."
            )

    if team_recommendation and monte_carlo.get("players"):
        recommended_simulation = next(
            (
                player
                for player in monte_carlo["players"]
                if player["player"] == team_recommendation[1]
            ),
            None,
        )
        if recommended_simulation:
            availability_pct = recommended_simulation["availability_pct"]
            if availability_pct <= 25:
                recommendation_reasons.append(
                    f"Monte Carlo estimates only a {availability_pct}% chance "
                    "the player reaches your next pick."
                )
            elif availability_pct >= 70:
                recommendation_reasons.append(
                    f"Monte Carlo estimates a {availability_pct}% chance "
                    "the player remains available at your next pick."
                )

    if team_recommendation and pick_forecast.get("next_pick"):
        recommended_position = team_recommendation[2]
        projected_position_picks = pick_forecast["projected_gone"].get(
            recommended_position, 0
        )
        needy_opponents = pick_forecast["teams_needing_position"].get(
            recommended_position, 0
        )
        if projected_position_picks > 0:
            recommendation_reasons.append(
                f"Opponent model projects {projected_position_picks} "
                f"{recommended_position} selection(s) before your next pick."
            )
        if needy_opponents >= 2:
            recommendation_reasons.append(
                f"Opponent demand before the next pick is elevated: "
                f"{needy_opponents} teams still need {recommended_position} depth."
            )

    draft_coach = build_draft_coach_summary(
        team_recommendation,
        top_recommendations,
        recommendation_reasons,
        draft_now_wait,
        expected_value_analysis,
        monte_carlo,
        active_strategy,
        current_round,
        pick_forecast,
    )

    draft_coach = fuse_sleeper_context(
        draft_coach,
        sleeper_draft_signals,
        sleeper_recommendation_overlay,
        player_survival,
    )

    draft_coach = fuse_decision_plan(draft_coach, draft_decision_plan)

    
    readiness_conn = get_db_connection()
    readiness_cur = readiness_conn.cursor()
    draft_readiness = build_draft_readiness(readiness_cur, SLEEPER_LEAGUE_ID, 2026, sleeper_draft_signals, current_model_health)
    draft_validation = validate_runtime(recommendation_candidates, sleeper_draft_signals, current_model_health)
    readiness_cur.close()
    readiness_conn.close()

    # === Recommendation explainability batch 4A ===
    recommendation_explanation = build_explanation(top_recommendations, player_survival, expected_value_analysis, draft_decision_plan)
    # === Survival calibration batch 4B.1 ===
    survival_comparison = build_survival_comparison(recommendation_explanation, monte_carlo, player_survival)
    survival_comparison["comparison_id"] = persist_survival_comparison(get_db_connection, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), survival_comparison)
    if survival_comparison.get("available"):
        recommendation_explanation["survival_comparison"] = survival_comparison
        if survival_comparison.get("severity") == "HIGH":
            recommendation_explanation.setdefault("warnings", []).append(survival_comparison["message"])
    recommendation_explanation["audit_id"] = persist_explanation(get_db_connection, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), recommendation_explanation)

    draft_outcome_status = log_and_resolve(get_db_connection, SLEEPER_LEAGUE_ID, 2026, team_recommendation, sleeper_draft_signals, draft_now_wait, monte_carlo, player_survival, expected_value_analysis, draft_decision_plan)


    return render_template(
        "draftboard.html",
        draft_readiness=draft_readiness,
        draft_validation=draft_validation,
        candidate_pool_audit=candidate_pool_audit,
        model_health=current_model_health,
        draft_outcome_status=draft_outcome_status,
        recommendation_explanation=recommendation_explanation,
        survival_comparison=survival_comparison,
        draft_decision_plan=draft_decision_plan,
        player_survival=player_survival,
        sleeper_recommendation_overlay=sleeper_recommendation_overlay,
        sleeper_draft_signals=sleeper_draft_signals,
        title="My Draft Board",
        players=players,
        available_players=available_players,
        best_available=best_available,
        position_leaders=position_leaders,
        draft_targets=draft_targets,
        drafted_count=drafted_count,
        roster=roster,
        roster_slots=roster_slots,
        bench=bench,
        team_recommendation=team_recommendation,
        top_recommendations=top_recommendations,
        recommendation_engine_audit=recommendation_engine_audit,
        strategy_profiles=STRATEGY_PROFILES,
        active_strategy=active_strategy,
        strategy_profile=STRATEGY_PROFILES[active_strategy],
        current_round=current_round,
        round_plan=round_plan,
        strategy_bonus_for_pick=strategy_bonus_for_pick,
        recommendation_candidates=recommendation_candidates,
        scarcity=scarcity,
        scarcity_labels=scarcity_labels,
        scarcity_score=scarcity_score,
        need_score=need_score,
        tier_alert=tier_alert,
        roster_targets=ROSTER_TARGETS,
        position_counts=position_counts,
        roster_progress=roster_progress,
        tier_bonus=tier_bonus,
        tier_risk_details=tier_risk_details,
        recommendation_reasons=recommendation_reasons,
        tier_counts=tier_counts,
        tier_alert_position=tier_alert_position,
        tier_alert_tier=tier_alert_tier,
        tier_alert_remaining=tier_alert_remaining,
        recommended_tier=recommended_tier,
        recommended_tier_remaining=recommended_tier_remaining,
        pick_forecast=pick_forecast,
        league_tendencies=league_tendencies,
        league_bonus_for_pick=league_bonus_for_pick,
        draft_now_wait=draft_now_wait,
        monte_carlo=monte_carlo,
        value_gap_analysis=value_gap_analysis,
        expected_value_analysis=expected_value_analysis,
        draft_coach=draft_coach,
        rank_score=rank_score,
        agent_draft_score=agent_draft_score,
        sleeper_sync_status=sleeper_sync_status,
        sleeper_sync_error=sleeper_sync_error,
    )


@app.route("/draftboard/toggle-star", methods=["POST"])
@admin_required
def toggle_star():
    player_name = request.form.get("player_name", "").strip()
    if not player_name:
        return redirect(url_for("draftboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO draft_board (player_name, starred, drafted)
        VALUES (%s, true, false)
        ON CONFLICT (player_name)
        DO UPDATE SET starred = NOT draft_board.starred
        """,
        (player_name,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("draftboard"))


@app.route("/draftboard/toggle-drafted", methods=["POST"])
@admin_required
def toggle_drafted():
    player_name = request.form.get("player_name", "").strip()
    if not player_name:
        return redirect(url_for("draftboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO draft_board (player_name, starred, drafted)
        VALUES (%s, false, true)
        ON CONFLICT (player_name)
        DO UPDATE SET drafted = NOT draft_board.drafted
        """,
        (player_name,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("draftboard"))


@app.route("/draftboard/add-to-team", methods=["POST"])
@admin_required
def add_to_team():
    player_name = request.form.get("player_name", "").strip()
    position = request.form.get("position", "").strip().upper()

    if not player_name or not position:
        return redirect(url_for("draftboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO my_roster (player_name, position)
        SELECT %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM my_roster WHERE player_name = %s
        )
        """,
        (player_name, position, player_name),
    )
    cur.execute(
        """
        INSERT INTO draft_board (player_name, starred, drafted)
        VALUES (%s, false, true)
        ON CONFLICT (player_name)
        DO UPDATE SET drafted = true
        """,
        (player_name,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("draftboard"))


@app.route("/draftboard/remove-from-team", methods=["POST"])
@admin_required
def remove_from_team():
    roster_id = request.form.get("roster_id", "").strip()
    if roster_id.isdigit():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM my_roster WHERE id = %s", (int(roster_id),))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("draftboard"))


@app.route("/position/<position>")
def position_rankings(position):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ranking, player_name, nfl_team
        FROM players
        WHERE position = %s
        ORDER BY ranking
        """,
        (position.upper(),),
    )
    players = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        "position.html",
        title=f"{position.upper()} Rankings",
        players=players,
    )


def build_league_overview():
    """Build a ten-roster league view directly from Sleeper."""
    league = get_league(SLEEPER_LEAGUE_ID) or {}
    users = get_users(SLEEPER_LEAGUE_ID) or []
    rosters = get_rosters(SLEEPER_LEAGUE_ID) or []
    draft = get_draft(SLEEPER_DRAFT_ID) or {}
    users_by_id = {str(u.get("user_id")): u for u in users if u.get("user_id")}
    slot_by_roster = {
        int(roster_id): int(slot)
        for slot, roster_id in (draft.get("slot_to_roster_id") or {}).items()
        if str(roster_id).isdigit() and str(slot).isdigit()
    }
    teams = []
    for roster in sorted(rosters, key=lambda r: int(r.get("roster_id") or 999)):
        roster_id = int(roster.get("roster_id") or 0)
        owner_id = str(roster.get("owner_id") or "")
        user = users_by_id.get(owner_id)
        metadata = (user or {}).get("metadata") or {}
        display_name = (user or {}).get("display_name")
        team_name = metadata.get("team_name") or display_name or f"Roster {roster_id} - Awaiting Manager"
        settings = roster.get("settings") or {}
        teams.append({
            "roster_id": roster_id,
            "team_name": team_name,
            "display_name": display_name or "Awaiting Manager",
            "claimed": user is not None,
            "is_owner": bool((user or {}).get("is_owner")),
            "draft_slot": slot_by_roster.get(roster_id),
            "players": len(roster.get("players") or []),
            "wins": int(settings.get("wins") or 0),
            "losses": int(settings.get("losses") or 0),
            "ties": int(settings.get("ties") or 0),
        })
    league_settings = league.get("settings") or {}
    scoring = league.get("scoring_settings") or {}
    draft_settings = draft.get("settings") or {}
    owner_team = next((team for team in teams if team["is_owner"]), None)
    return {
        "league_id": league.get("league_id") or SLEEPER_LEAGUE_ID,
        "league_name": league.get("name") or "Fantasy Intelligence Champions League",
        "season": league.get("season") or "2026",
        "status": str(league.get("status") or "pre_draft").replace("_", " ").title(),
        "sport": str(league.get("sport") or "nfl").upper(),
        "total_rosters": int(league.get("total_rosters") or league_settings.get("num_teams") or 10),
        "joined_managers": sum(1 for team in teams if team["claimed"]),
        "open_rosters": sum(1 for team in teams if not team["claimed"]),
        "playoff_teams": int(league_settings.get("playoff_teams") or 0),
        "faab_budget": int(league_settings.get("waiver_budget") or 0),
        "trade_review_days": int(league_settings.get("trade_review_days") or 0),
        "reserve_slots": int(league_settings.get("reserve_slots") or 0),
        "full_ppr": float(scoring.get("rec") or 0) == 1.0,
        "draft_id": draft.get("draft_id") or SLEEPER_DRAFT_ID,
        "draft_type": str(draft.get("type") or "snake").title(),
        "draft_status": str(draft.get("status") or "pre_draft").replace("_", " ").title(),
        "draft_rounds": int(draft_settings.get("rounds") or league_settings.get("draft_rounds") or 0),
        "owner_slot": (owner_team or {}).get("draft_slot") or 5,
        "teams": teams,
    }


@app.route("/league")
@app.route("/league-overview")
def league_manager():
    try:
        return render_template("league_overview.html", title="League Overview", overview=build_league_overview(), sync_error=None)
    except Exception as exc:
        app.logger.exception("Unable to build Sleeper league overview")
        return render_template("league_overview.html", title="League Overview", overview=None, sync_error=str(exc)), 503


@app.route("/league/sync-teams", methods=["POST"])
@admin_required
def sync_league_teams():
    overview = build_league_overview()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM league_teams
            WHERE team_name = 'My Team'
               OR team_name ~ '^Team [0-9]+$'
               OR team_name ~ '^Roster [0-9]+ - Awaiting Manager$'
        """)
        for team in overview["teams"]:
            cur.execute("INSERT INTO league_teams (team_name) VALUES (%s) ON CONFLICT DO NOTHING", (team["team_name"],))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("league_manager"))


@app.route("/league/add-team", methods=["POST"])
@admin_required
def add_league_team():
    team_name = request.form.get("team_name", "").strip()
    if team_name:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO league_teams (team_name) VALUES (%s) ON CONFLICT DO NOTHING",
            (team_name,),
        )
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("league_manager"))


@app.route("/league/delete-team", methods=["POST"])
@admin_required
def delete_league_team():
    team_id = request.form.get("team_id", "").strip()
    if team_id.isdigit():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM league_teams WHERE id = %s", (int(team_id),))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("league_manager"))


@app.route("/rosters")
def league_rosters():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, team_name FROM league_teams ORDER BY id")
    teams = cur.fetchall()
    cur.execute(
        """
        SELECT id, team_name, player_name, position, drafted_at
        FROM league_rosters
        ORDER BY drafted_at, id
        """
    )
    roster_rows = cur.fetchall()
    cur.close()
    conn.close()

    rosters_by_team = []
    for team_id, team_name in teams:
        rosters_by_team.append(
            {
                "team_id": team_id,
                "team_name": team_name,
                "players": [row for row in roster_rows if row[1] == team_name],
            }
        )

    return render_template(
        "rosters.html",
        title="League Rosters",
        rosters_by_team=rosters_by_team,
    )


@app.route("/trackdraft", methods=["GET", "POST"])
@admin_required
def track_draft():
    return track(request,get_db_connection,fetch_available_players,SLEEPER_DRAFT_ID)


@app.route("/trackdraft/undo", methods=["POST"])
@admin_required
def undo_draft_pick():
    return undo(request,get_db_connection,SLEEPER_DRAFT_ID)


@app.route("/test-sleeper", methods=["POST"])
@admin_required
def test_sleeper():

    league_id = Config.SLEEPER_LEAGUE_ID

    league = get_league(league_id)

    return jsonify(league)


@app.route("/test-sleeper-users", methods=["POST"])
@admin_required
def test_sleeper_users():

    league_id = Config.SLEEPER_LEAGUE_ID

    return jsonify(
        get_users(league_id)
    )


@app.route("/test-sleeper-rosters", methods=["POST"])
@admin_required
def test_sleeper_rosters():

    league_id = Config.SLEEPER_LEAGUE_ID

    return jsonify(
        get_rosters(league_id)
    )

@app.route("/create-sleeper-tables", methods=["POST"])
@admin_required
def create_sleeper_tables():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sleeper_teams (
        id SERIAL PRIMARY KEY,
        sleeper_user_id VARCHAR(50) UNIQUE,
        display_name VARCHAR(255),
        team_name VARCHAR(255),
        avatar VARCHAR(255),
        league_id VARCHAR(50),
        is_owner BOOLEAN DEFAULT FALSE
    )
    """)

    conn.commit()

    cur.close()
    conn.close()

    return "Sleeper tables created successfully!"

@app.route("/sleeper-sync", methods=["POST"])
@admin_required
def sleeper_sync():

    league_id = Config.SLEEPER_LEAGUE_ID

    users = get_users(league_id)

    conn = get_db_connection()
    cur = conn.cursor()

    imported = 0

    for user in users:

        metadata = user.get("metadata") or {}

        team_name = metadata.get(
            "team_name",
            user["display_name"]
        )

        cur.execute("""
        INSERT INTO sleeper_teams (
            sleeper_user_id,
            display_name,
            team_name,
            avatar,
            league_id,
            is_owner
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (sleeper_user_id)
        DO UPDATE SET
            display_name = EXCLUDED.display_name,
            team_name = EXCLUDED.team_name,
            avatar = EXCLUDED.avatar
        """, (
            user["user_id"],
            user["display_name"],
            team_name,
            user.get("avatar"),
            user["league_id"],
            user.get("is_owner", False)
        ))

        imported += 1

    conn.commit()

    cur.close()
    conn.close()

    return f"Imported {imported} Sleeper teams successfully!"

@app.route("/sleeper-teams")
def sleeper_teams():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            display_name,
            team_name,
            is_owner
        FROM sleeper_teams
        ORDER BY team_name
    """)

    teams = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "sleeper_teams.html",
        teams=teams
    )

@app.route("/test-draft")
def test_draft():

    draft_id = "1398094331272794112"

    return jsonify(
        get_draft(draft_id)
    )


@app.route("/sleeper/players/sync", methods=["POST"])
@admin_required
def sleeper_player_map_sync():
    try:
        return jsonify(sync_sleeper_player_map())
    except Exception:
        app.logger.exception("Sleeper player-map sync failed")
        return jsonify({"error": "sync failed"}), 500


@app.route("/sleeper/draft-picks/sync", methods=["POST"])
@admin_required
def sleeper_draft_picks_sync():
    try:
        return jsonify(sync_sleeper_draft_picks())
    except Exception:
        app.logger.exception("Sleeper draft-pick sync failed")
        return jsonify({"error": "sync failed"}), 500


@app.route("/test-draft-picks", methods=["POST"])
@admin_required
def test_draft_picks():

    draft_id = Config.SLEEPER_DRAFT_ID

    return jsonify(
        get_draft_picks(draft_id)
    )

@app.route("/create-draft-tables", methods=["POST"])
@admin_required
def create_draft_tables():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sleeper_drafts (
        draft_id VARCHAR(50) PRIMARY KEY,
        league_id VARCHAR(50),
        season VARCHAR(10),
        draft_type VARCHAR(25),
        rounds INTEGER,
        teams INTEGER,
        status VARCHAR(25)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sleeper_draft_picks (
        id SERIAL PRIMARY KEY,
        pick_id VARCHAR(50) UNIQUE,
        draft_id VARCHAR(50),
        round_num INTEGER,
        pick_no INTEGER,
        roster_id INTEGER,
        player_id VARCHAR(50),
        player_name VARCHAR(255)
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

    return "Draft tables created successfully!"

@app.route("/draft-sync", methods=["POST"])
@admin_required
def draft_sync():

    draft = get_draft(
        Config.SLEEPER_DRAFT_ID
    )

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO sleeper_drafts (
        draft_id,
        league_id,
        season,
        draft_type,
        rounds,
        teams,
        status
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (draft_id)
    DO UPDATE SET
        status = EXCLUDED.status
    """, (
        draft["draft_id"],
        draft["league_id"],
        draft["season"],
        draft["type"],
        draft["settings"]["rounds"],
        draft["settings"]["teams"],
        draft["status"]
    ))

    conn.commit()

    cur.close()
    conn.close()

    return "Draft synced successfully!"

@app.route("/create-draft-picks-table", methods=["POST"])
@admin_required
def create_draft_picks_table():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sleeper_draft_picks (
        id SERIAL PRIMARY KEY,
        sleeper_pick_id VARCHAR(50) UNIQUE,
        draft_id VARCHAR(50),
        roster_id INTEGER,
        round_num INTEGER,
        pick_no INTEGER,
        player_id VARCHAR(50),
        player_name VARCHAR(255),
        synced_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn.commit()

    cur.close()
    conn.close()

    return "Draft picks table created!"

@app.route("/agent/recommendation", methods=["POST"])
@admin_required
def draft_recommendation():

    conn = get_db_connection()
    cur = conn.cursor()

    players = fetch_available_players(cur)

    cur.close()
    conn.close()

    if not players:
        return {
            "recommendation": None
        }

    best = players[0]

    return {
        "player": best[1],
        "position": best[2],
        "rank": best[0]
    }







def ensure_mock_tables(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS mock_drafts (
        id SERIAL PRIMARY KEY, draft_name VARCHAR(255) NOT NULL,
        strategy VARCHAR(50) NOT NULL, teams INTEGER NOT NULL DEFAULT 10,
        rounds INTEGER NOT NULL DEFAULT 14, draft_position INTEGER NOT NULL DEFAULT 1,
        mode VARCHAR(25) NOT NULL DEFAULT 'quick', automation_mode VARCHAR(25) NOT NULL DEFAULT 'advisory',
        status VARCHAR(25) NOT NULL DEFAULT 'active', current_pick INTEGER NOT NULL DEFAULT 0,
        paused BOOLEAN NOT NULL DEFAULT FALSE, overall_grade VARCHAR(5), roster_score NUMERIC(10,2),
        created_at TIMESTAMP DEFAULT NOW())""")
    for sql in [
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS mode VARCHAR(25) NOT NULL DEFAULT 'quick'",
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS automation_mode VARCHAR(25) NOT NULL DEFAULT 'advisory'",
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS status VARCHAR(25) NOT NULL DEFAULT 'active'",
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS current_pick INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS paused BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS overall_grade VARCHAR(5)",
        "ALTER TABLE mock_drafts ADD COLUMN IF NOT EXISTS roster_score NUMERIC(10,2)",
    ]: cur.execute(sql)
    cur.execute("""CREATE TABLE IF NOT EXISTS mock_picks (
        id SERIAL PRIMARY KEY, draft_id INTEGER NOT NULL REFERENCES mock_drafts(id) ON DELETE CASCADE,
        round_num INTEGER NOT NULL, pick_no INTEGER NOT NULL, draft_slot INTEGER,
        team_name VARCHAR(255) NOT NULL, player_name VARCHAR(255) NOT NULL,
        position VARCHAR(20), nfl_team VARCHAR(20), overall_rank INTEGER,
        draft_score NUMERIC(10,2) DEFAULT 0, strategy_bonus NUMERIC(10,2) DEFAULT 0,
        source VARCHAR(25) NOT NULL DEFAULT 'ai', created_at TIMESTAMP DEFAULT NOW())""")
    for sql in [
        "ALTER TABLE mock_picks ADD COLUMN IF NOT EXISTS draft_slot INTEGER",
        "ALTER TABLE mock_picks ADD COLUMN IF NOT EXISTS nfl_team VARCHAR(20)",
        "ALTER TABLE mock_picks ADD COLUMN IF NOT EXISTS overall_rank INTEGER",
        "ALTER TABLE mock_picks ADD COLUMN IF NOT EXISTS strategy_bonus NUMERIC(10,2) DEFAULT 0",
        "ALTER TABLE mock_picks ADD COLUMN IF NOT EXISTS source VARCHAR(25) NOT NULL DEFAULT 'ai'",
        "ALTER TABLE mock_picks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
    ]: cur.execute(sql)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS mock_pick_unique ON mock_picks(draft_id,pick_no)")


def mock_slot_for_pick(pick_no, teams):
    round_num=((pick_no-1)//teams)+1; pos=((pick_no-1)%teams)+1
    return teams-pos+1 if round_num%2==0 else pos


def mock_counts(cur,draft_id,slot):
    counts={p:0 for p in MOCK_ROSTER_TARGETS}
    cur.execute("SELECT position,COUNT(*) FROM mock_picks WHERE draft_id=%s AND draft_slot=%s GROUP BY position",(draft_id,slot))
    for pos,count in cur.fetchall():
        if pos in counts: counts[pos]=count
    return counts


def mock_pool(cur, draft_id):
    cur.execute(
        """
        SELECT ranking, player_name, UPPER(position), nfl_team,
               projected_points, tier, adp, id
        FROM players p
        WHERE UPPER(position) IN ('QB', 'RB', 'WR', 'TE', 'K', 'DEF')
          AND NOT EXISTS (
              SELECT 1 FROM mock_picks mp
              WHERE mp.draft_id = %s
                AND mp.player_name = p.player_name
          )
        ORDER BY ranking NULLS LAST, player_name
        """,
        (draft_id,),
    )
    return list(cur.fetchall())


def mock_eligible_pool(pool, counts, round_num, rounds):
    """Exclude K/DEF early and require both in the final two rounds."""
    offensive = [p for p in pool if p[2] in ("QB", "RB", "WR", "TE")]
    if round_num <= max(1, rounds - 2):
        return offensive

    missing_special = [
        pos for pos in ("K", "DEF")
        if counts.get(pos, 0) < MOCK_ROSTER_TARGETS[pos]
    ]
    rounds_remaining = max(1, rounds - round_num + 1)
    if missing_special and rounds_remaining <= len(missing_special):
        required = [p for p in pool if p[2] in missing_special]
        if required:
            return required

    late_pool = [p for p in pool if p[2] in MOCK_ROSTER_TARGETS]
    return late_pool or offensive


def mock_score(player, pool, counts, strategy, round_num):
    rank, name, pos, team = player[:4]
    target = MOCK_ROSTER_TARGETS[pos]
    need = int(max(0, target - counts.get(pos, 0)) / max(target, 1) * 100)
    try:
        tier = int(player[5]) if len(player) > 5 and player[5] is not None else get_player_tier(rank)
    except (TypeError, ValueError):
        tier = get_player_tier(rank)

    remaining = 0
    for pool_player in pool:
        if pool_player[2] != pos:
            continue
        try:
            pool_tier = int(pool_player[5]) if len(pool_player) > 5 and pool_player[5] is not None else get_player_tier(pool_player[0])
        except (TypeError, ValueError):
            pool_tier = get_player_tier(pool_player[0])
        remaining += int(pool_tier == tier)

    tier_bonus = 35 if remaining <= 2 else 15 if remaining <= 4 else 0
    strategy_bonus = get_strategy_bonus(strategy, pos, round_num)
    starter_targets = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
    starter_bonus = 20 if counts.get(pos, 0) < starter_targets[pos] else 0
    rank_score = max(0, 101 - (rank or 9999))
    total = rank_score + need + tier_bonus + strategy_bonus + starter_bonus
    return {"total": total, "need": need, "tier_bonus": tier_bonus, "strategy_bonus": strategy_bonus}


def mock_recommendations(cur, draft, limit=8):
    draft_id, strategy, teams, rounds, user_slot, current_pick = draft
    pool = mock_pool(cur, draft_id)
    counts = mock_counts(cur, draft_id, user_slot)
    round_num = (current_pick // teams) + 1
    ranked = rank_draft_candidates(pool, counts, strategy, round_num, rounds, MOCK_ROSTER_TARGETS, get_player_tier, get_strategy_bonus, limit)
    return [item.as_legacy() for item in ranked]


def insert_mock_pick(cur,draft_id,pick_no,slot,player,score,source):
    teams_name="My Mock Team" if source in ('user','autopilot') else f"AI Team {slot}"
    round_num=None
    cur.execute("SELECT teams FROM mock_drafts WHERE id=%s",(draft_id,)); teams=cur.fetchone()[0]
    round_num=((pick_no-1)//teams)+1
    cur.execute("""INSERT INTO mock_picks(draft_id,round_num,pick_no,draft_slot,team_name,
        player_name,position,nfl_team,overall_rank,draft_score,strategy_bonus,source)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(draft_id,pick_no) DO NOTHING""",
        (draft_id,round_num,pick_no,slot,teams_name,player[1],player[2],player[3],player[0],score["total"],score["strategy_bonus"],source))


def advance_mock_ai(cur, draft_id):
    cur.execute(
        "SELECT strategy,teams,rounds,draft_position,current_pick,paused,automation_mode FROM mock_drafts WHERE id=%s",
        (draft_id,),
    )
    row = cur.fetchone()
    if not row:
        return
    strategy, teams, rounds, user_slot, current_pick, paused, automation = row
    max_pick = teams * rounds
    while current_pick < max_pick and not paused:
        next_pick = current_pick + 1
        slot = mock_slot_for_pick(next_pick, teams)
        if slot == user_slot and automation != "autopilot":
            break
        pool = mock_pool(cur, draft_id)
        if not pool:
            break
        counts = mock_counts(cur, draft_id, slot)
        round_num = ((next_pick - 1) // teams) + 1
        use_strategy = strategy if slot == user_slot else "BEST_AVAILABLE"
        eligible = mock_eligible_pool(pool, counts, round_num, rounds)
        candidates = [(mock_score(p, pool, counts, use_strategy, round_num), p) for p in eligible[:60]]
        if not candidates:
            break
        score, player = max(candidates, key=lambda item: (item[0]["total"], -(item[1][0] or 9999)))
        insert_mock_pick(cur, draft_id, next_pick, slot, player, score, "autopilot" if slot == user_slot else "ai")
        current_pick = next_pick
        cur.execute("UPDATE mock_drafts SET current_pick=%s WHERE id=%s", (current_pick, draft_id))
    if current_pick >= max_pick:
        cur.execute("UPDATE mock_drafts SET status='complete' WHERE id=%s", (draft_id,))


def mock_grade_simple(counts):
    values = []
    rows = []
    for pos, target in MOCK_ROSTER_TARGETS.items():
        score = min(100, round(counts.get(pos, 0) / max(target, 1) * 100))
        values.append(score)
        grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
        rows.append({"position": pos, "count": counts.get(pos, 0), "target": target, "score": score, "grade": grade})
    overall = round(sum(values) / len(values)) if values else 0
    grade = "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 60 else "F"
    return overall, grade, rows


@app.route('/mockdraft')
def mock_draft_lab():
    conn=get_db_connection();cur=conn.cursor();ensure_mock_tables(cur);conn.commit()
    cur.execute("SELECT id,draft_name,strategy,teams,rounds,draft_position,mode,automation_mode,status,current_pick,overall_grade,roster_score,created_at FROM mock_drafts ORDER BY id DESC LIMIT 30")
    drafts=cur.fetchall();cur.close();conn.close()
    return render_template('mockdraft.html',title='Mock Draft Lab',drafts=drafts,strategy_profiles=STRATEGY_PROFILES)


@app.route('/mockdraft/start',methods=['POST'])
@admin_required
def start_mock_draft():
    teams=max(4,min(16,int(request.form.get('teams',10))));rounds=max(4,min(20,int(request.form.get('rounds',14))))
    slot=max(1,min(teams,int(request.form.get('draft_position',1))));strategy=request.form.get('strategy',DEFAULT_STRATEGY)
    if strategy not in STRATEGY_PROFILES:strategy=DEFAULT_STRATEGY
    mode=request.form.get('mode','interactive');automation=request.form.get('automation_mode','advisory')
    if automation not in ('advisory','approval','autopilot'):automation='advisory'
    name=request.form.get('draft_name','').strip() or f"{STRATEGY_PROFILES[strategy]['label']} Interactive Mock"
    conn=get_db_connection();cur=conn.cursor();ensure_mock_tables(cur)
    cur.execute("INSERT INTO mock_drafts(draft_name,strategy,teams,rounds,draft_position,mode,automation_mode,status,current_pick) VALUES(%s,%s,%s,%s,%s,%s,%s,'active',0) RETURNING id",(name,strategy,teams,rounds,slot,mode,automation));did=cur.fetchone()[0]
    advance_mock_ai(cur,did);conn.commit();cur.close();conn.close()
    return redirect(url_for('mock_draft_live',draft_id=did))


@app.route('/mockdraft/live/<int:draft_id>')
def mock_draft_live(draft_id):
    conn=get_db_connection();cur=conn.cursor();ensure_mock_tables(cur);advance_mock_ai(cur,draft_id);conn.commit()
    cur.execute("SELECT id,draft_name,strategy,teams,rounds,draft_position,mode,automation_mode,status,current_pick,paused FROM mock_drafts WHERE id=%s",(draft_id,));d=cur.fetchone()
    if not d:cur.close();conn.close();return 'Mock draft not found',404
    raw_recs=mock_recommendations(cur,(d[0],d[2],d[3],d[4],d[5],d[9])) if d[8]!='complete' else []
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
    cur.execute("SELECT round_num,pick_no,draft_slot,team_name,player_name,position,nfl_team,overall_rank,draft_score,source FROM mock_picks WHERE draft_id=%s ORDER BY pick_no DESC LIMIT 25",(draft_id,));recent=cur.fetchall()
    counts=mock_counts(cur,draft_id,d[5]);cur.close();conn.close()
    next_pick=d[9]+1; current_round=((next_pick-1)//d[3])+1; current_slot=mock_slot_for_pick(next_pick,d[3]) if next_pick<=d[3]*d[4] else None
    return render_template('mockdraft_live.html',title=d[1],draft=d,recommendations=recs,recommendation_publication=recommendation_publication,recent_picks=recent,counts=counts,current_round=current_round,current_slot=current_slot,next_pick=next_pick,strategy_profile=STRATEGY_PROFILES.get(d[2],STRATEGY_PROFILES[DEFAULT_STRATEGY]))


@app.route('/mockdraft/live/<int:draft_id>/pick',methods=['POST'])
@admin_required
def mock_draft_pick(draft_id):
    player_name=request.form.get('player_name','').strip();conn=get_db_connection();cur=conn.cursor();ensure_mock_tables(cur)
    cur.execute("SELECT strategy,teams,rounds,draft_position,current_pick,paused FROM mock_drafts WHERE id=%s",(draft_id,));d=cur.fetchone()
    if not d:cur.close();conn.close();return 'Mock draft not found',404
    strategy,teams,rounds,user_slot,current_pick,paused=d;next_pick=current_pick+1
    if paused or next_pick>teams*rounds or mock_slot_for_pick(next_pick,teams)!=user_slot:
        cur.close();conn.close();return redirect(url_for('mock_draft_live',draft_id=draft_id))
    pool=mock_pool(cur,draft_id);player=next((x for x in pool if x[1]==player_name),None)
    if player:
        score=mock_score(player,pool,mock_counts(cur,draft_id,user_slot),strategy,((next_pick-1)//teams)+1)
        insert_mock_pick(cur,draft_id,next_pick,user_slot,player,score,'user');cur.execute("UPDATE mock_drafts SET current_pick=%s WHERE id=%s",(next_pick,draft_id));advance_mock_ai(cur,draft_id);conn.commit()
    cur.close();conn.close();return redirect(url_for('mock_draft_live',draft_id=draft_id))


@app.route('/mockdraft/live/<int:draft_id>/toggle-pause',methods=['POST'])
@admin_required
def toggle_mock_pause(draft_id):
    conn=get_db_connection();cur=conn.cursor();cur.execute("UPDATE mock_drafts SET paused=NOT paused WHERE id=%s",(draft_id,));conn.commit();cur.close();conn.close();return redirect(url_for('mock_draft_live',draft_id=draft_id))


@app.route('/mockdraft/<int:draft_id>')
def mock_draft_result(draft_id):
    conn=get_db_connection();cur=conn.cursor();ensure_mock_tables(cur)
    cur.execute("SELECT id,draft_name,strategy,teams,rounds,draft_position,mode,automation_mode,status,current_pick,overall_grade,roster_score,created_at FROM mock_drafts WHERE id=%s",(draft_id,));d=cur.fetchone()
    if not d:cur.close();conn.close();return 'Mock draft not found',404
    cur.execute("SELECT round_num,pick_no,draft_slot,team_name,player_name,position,nfl_team,overall_rank,draft_score,strategy_bonus,source FROM mock_picks WHERE draft_id=%s ORDER BY pick_no",(draft_id,));picks=cur.fetchall();mine=[x for x in picks if x[2]==d[5]]
    counts=mock_counts(cur,draft_id,d[5]);score,grade,position_grades=mock_grade_simple(counts)
    cur.execute("UPDATE mock_drafts SET overall_grade=%s,roster_score=%s WHERE id=%s",(grade,score,draft_id));conn.commit();cur.close();conn.close()
    return render_template('mockdraft_result.html',title=d[1],draft=d,picks=picks,user_picks=mine,position_grades=position_grades,roster_score=score,overall_grade=grade,best_pick=max(mine,key=lambda x:float(x[8] or 0),default=None),strategy_profile=STRATEGY_PROFILES.get(d[2],STRATEGY_PROFILES[DEFAULT_STRATEGY]))


@app.route('/mockdraft/<int:draft_id>/delete',methods=['POST'])
@admin_required
def delete_mock_draft(draft_id):
    conn=get_db_connection();cur=conn.cursor();cur.execute("DELETE FROM mock_drafts WHERE id=%s",(draft_id,));conn.commit();cur.close();conn.close();return redirect(url_for('mock_draft_lab'))

# === Draft state hardening batch 1 ===
_original_sync_sleeper_draft_picks = sync_sleeper_draft_picks
sync_sleeper_draft_picks = build_hardened_sync(_original_sync_sleeper_draft_picks, get_db_connection, get_draft, get_draft_picks, SLEEPER_LEAGUE_ID, SLEEPER_DRAFT_ID)
app.register_blueprint(create_blueprint(get_db_connection, get_draft, SLEEPER_LEAGUE_ID, SLEEPER_DRAFT_ID))
# === End draft state hardening batch 1 ===

# === Draft operations hardening batch 2 ===
app.register_blueprint(blueprint(get_db_connection,SLEEPER_DRAFT_ID))
# === End draft operations hardening batch 2 ===
# === Recommendation explainability batch 4A route ===
app.register_blueprint(recommendation_blueprint(get_db_connection, SLEEPER_DRAFT_ID))
# === Monte Carlo survival batch 4B route ===
app.register_blueprint(monte_carlo_survival_blueprint(get_db_connection, SLEEPER_DRAFT_ID))
# === Survival calibration batch 4B.1 route ===
app.register_blueprint(survival_calibration_blueprint(get_db_connection, SLEEPER_DRAFT_ID))
app.register_blueprint(create_sandbox_blueprint(get_db_connection))

app.register_blueprint(create_owner_operations_blueprint(get_db_connection, get_league, get_users, get_rosters, get_all_players, normalize_player_name))


app.register_blueprint(create_sleeper_hub_blueprint(get_db_connection))

app.register_blueprint(create_sleeper_intelligence_blueprint(get_db_connection))

app.register_blueprint(create_draft_accuracy_blueprint(get_db_connection))
app.register_blueprint(create_outcome_health_blueprint(get_db_connection))
app.register_blueprint(create_intelligence_operations_blueprint(get_db_connection))
app.register_blueprint(create_post_draft_blueprint(get_db_connection, get_draft, SLEEPER_LEAGUE_ID, SLEEPER_DRAFT_ID, 2026))

app.register_blueprint(create_draft_health_blueprint(get_db_connection, SLEEPER_LEAGUE_ID, 2026, build_sleeper_draft_signals, model_health))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)


# Test Inventory

tests/test_f3_d5_waiver_action_route.py
tests/test_yahoo_pickem.py
tests/test_weekly_lineup_intelligence.py
tests/test_f4_d_trade_target_center.py
tests/test_f3_c1_publication_gate.py
tests/test_verify_f3_b31_postgres_parity.py
tests/test_db_config_contract.py
tests/test_f3_b1_replay_validation.py
tests/test_weekly_lineup_template.py
tests/test_readiness.py
tests/test_survivor_intelligence.py
tests/test_f2r_a_local_identity.py
tests/test_failed_event_retry.py
tests/test_f4_d_trade_target_center_contract.py
tests/test_mock_draft_synchronization.py
tests/test_integrity_integration.py
tests/test_recommendation_explainer.py
tests/test_phase_f_draft_sandbox.py
tests/test_f3_b3_live_reconciliation.py
tests/test_f3_b4_readiness.py
tests/test_f3_d4_waiver_action_integration.py
tests/test_f3_d5_waiver_action_template.py
tests/test_draft_hq_snapshot_integrity.py
tests/test_f4_b_matchup_intelligence.py
tests/test_model_calibration.py
tests/test_batch_b_outcome_intelligence.py
tests/test_phase_f2_integration.py
tests/test_f3_d5_waiver_action_publication.py
tests/test_f3a2_runtime.py
tests/test_survival_calibration.py
tests/test_security_and_validation.py
tests/test_f3a1_repository_integration.py
tests/test_monte_carlo_survival.py
tests/test_mock_draft_state_consistency.py
tests/test_import.py
tests/test_f4_e_playoff_intelligence.py
tests/test_integrity_freshness.py
tests/test_draft_operations_hardening.py
tests/test_draft_recommendation_service.py
tests/test_f3_b31_migration_contract.py
tests/test_draftboard_polling.py
tests/test_f4_ab_command_center_contract.py
tests/test_draft_state_hardening.py
tests/test_batch_a_validation_hardening.py
tests/test_f4_c_decision_ranking.py
tests/test_f3_d3_waiver_action_plan.py
tests/test_f3_b31_postgres_parity.py
tests/test_trade_intelligence_template.py
tests/test_f4_e_playoff_template.py
tests/test_batch_d_intelligence_operations.py
tests/test_trade_intelligence.py
tests/test_draft_environment_rotation.py
tests/test_f3_c2_draft_recommendation_publication.py
tests/test_f2r_c_identity_bridge.py
tests/test_f3_d1_sleeper_waiver_intelligence.py
tests/test_batch_c_post_draft_transition.py
tests/test_draft_day_readiness.py
tests/test_f3_b2_reconciliation.py
tests/test_f3_d2_faab_intelligence.py
tests/test_integrity_service.py
tests/test_draft_event_pipeline.py


## Pytest Collection

============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/deeoriginalone/fantasy-intelligence
configfile: pytest.ini
testpaths: tests
collected 24 items / 50 errors

<Dir fantasy-intelligence>
  <Dir tests>
    <Module test_batch_a_validation_hardening.py>
      <Function test_sources_parse>
      <Function test_publication_gate>
    <Module test_batch_c_post_draft_transition.py>
      <Function test_ready_when_identity_counts_and_invariants_pass>
      <Function test_remote_draft_must_be_complete>
      <Function test_count_mismatch_blocks_transition>
      <Function test_finalize_is_idempotent_when_state_is_active>
      <Function test_finalize_materializes_and_transitions>
    <Module test_db_config_contract.py>
      <Function test_config_db_kwargs_returns_expected_fields>
      <Function test_pickem_store_uses_centralized_config>
      <Function test_main_app_and_pickem_store_resolve_same_settings>
      <Function test_fi_db_values_do_not_redirect_active_pickem_store>
      <Function test_missing_required_db_configuration_raises_controlled_error>
      <Function test_psycopg_connect_is_not_called_with_real_db>
    <Module test_f3_b31_migration_contract.py>
      <Function test_clean_install_keeps_event_log_unconstrained_and_selection_state_unique>
      <Function test_upgrade_drops_only_obsolete_event_log_constraints_idempotently>
    <Module test_f3_d5_waiver_action_template.py>
      <Function test_blocked_state_renders_reason>
      <Function test_plan_renders_f3_d4_fields_without_unknown_bid>
    <Module test_f4_ab_command_center_contract.py>
      <Function test_gm_template_contract>
      <Function test_owner_integration_contract>
    <Module test_f4_d_trade_target_center_contract.py>
      <Function test_template_contract>
      <Function test_route_contract>
    <Module test_f4_e_playoff_template.py>
      <Function test_playoff_template_renders_and_has_no_submission_endpoint>
    <Module test_trade_intelligence_template.py>
      <Function test_trade_template_renders_and_has_no_submission_endpoint>
    <Module test_weekly_lineup_template.py>
      <Function test_template_renders_decisions_and_has_no_form>

==================================== ERRORS ====================================
_________ ERROR collecting tests/test_batch_b_outcome_intelligence.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_batch_b_outcome_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_batch_b_outcome_intelligence.py:3: in <module>
    from draft.draft_outcome_health import build_outcome_health
E   ModuleNotFoundError: No module named 'draft'
________ ERROR collecting tests/test_batch_d_intelligence_operations.py ________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_batch_d_intelligence_operations.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_batch_d_intelligence_operations.py:2: in <module>
    from intelligence.intelligence_explainability import build_explanation
E   ModuleNotFoundError: No module named 'intelligence'
______________ ERROR collecting tests/test_draft_day_readiness.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_day_readiness.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_day_readiness.py:1: in <module>
    from draft.draft_readiness import build_reconciliation
E   ModuleNotFoundError: No module named 'draft'
__________ ERROR collecting tests/test_draft_environment_rotation.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_environment_rotation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_environment_rotation.py:5: in <module>
    from draft.draft_state_hardening import rotate_draft_environment
E   ModuleNotFoundError: No module named 'draft'
_____________ ERROR collecting tests/test_draft_event_pipeline.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_event_pipeline.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_event_pipeline.py:3: in <module>
    from draft_events.models import DraftEvent
E   ModuleNotFoundError: No module named 'draft_events'
__________ ERROR collecting tests/test_draft_hq_snapshot_integrity.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_hq_snapshot_integrity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_hq_snapshot_integrity.py:1: in <module>
    from draft.draft_hq_integrity import build_draft_hq_integrity
E   ModuleNotFoundError: No module named 'draft'
__________ ERROR collecting tests/test_draft_operations_hardening.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_operations_hardening.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_operations_hardening.py:1: in <module>
    from draft.draft_operations_hardening import invariants
E   ModuleNotFoundError: No module named 'draft'
_________ ERROR collecting tests/test_draft_recommendation_service.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_recommendation_service.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_recommendation_service.py:2: in <module>
    from services.draft_recommendation_service import Candidate, rank_candidates
E   ModuleNotFoundError: No module named 'services'
_____________ ERROR collecting tests/test_draft_state_hardening.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_state_hardening.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_state_hardening.py:4: in <module>
    from draft.draft_state_hardening import (
E   ModuleNotFoundError: No module named 'draft'
______________ ERROR collecting tests/test_draftboard_polling.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draftboard_polling.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draftboard_polling.py:3: in <module>
    import app as app_module
E   ModuleNotFoundError: No module named 'app'
_____________ ERROR collecting tests/test_f2r_a_local_identity.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f2r_a_local_identity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f2r_a_local_identity.py:1: in <module>
    from phase_f.models import DraftState
E   ModuleNotFoundError: No module named 'phase_f'
_____________ ERROR collecting tests/test_f2r_c_identity_bridge.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f2r_c_identity_bridge.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f2r_c_identity_bridge.py:2: in <module>
    from phase_f.identity_cache import IdentityCache
E   ModuleNotFoundError: No module named 'phase_f'
____________ ERROR collecting tests/test_f3_b1_replay_validation.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_b1_replay_validation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_b1_replay_validation.py:12: in <module>
    from draft_events.models import DraftEvent
E   ModuleNotFoundError: No module named 'draft_events'
_____________ ERROR collecting tests/test_f3_b2_reconciliation.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_b2_reconciliation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_b2_reconciliation.py:7: in <module>
    from draft_events.models import DraftEvent
E   ModuleNotFoundError: No module named 'draft_events'
____________ ERROR collecting tests/test_f3_b31_postgres_parity.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_b31_postgres_parity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_b31_postgres_parity.py:14: in <module>
    from draft_events.models import DraftEvent
E   ModuleNotFoundError: No module named 'draft_events'
___________ ERROR collecting tests/test_f3_b3_live_reconciliation.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_b3_live_reconciliation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_b3_live_reconciliation.py:7: in <module>
    from draft_events.live_reconciliation import LiveSleeperReconciliationService
E   ModuleNotFoundError: No module named 'draft_events'
________________ ERROR collecting tests/test_f3_b4_readiness.py ________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_b4_readiness.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_b4_readiness.py:7: in <module>
    from draft_events.readiness import (
E   ModuleNotFoundError: No module named 'draft_events'
____________ ERROR collecting tests/test_f3_c1_publication_gate.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_c1_publication_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_c1_publication_gate.py:7: in <module>
    from draft_events.readiness import (
E   ModuleNotFoundError: No module named 'draft_events'
____ ERROR collecting tests/test_f3_c2_draft_recommendation_publication.py _____
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_c2_draft_recommendation_publication.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_c2_draft_recommendation_publication.py:7: in <module>
    from draft_events.readiness import (
E   ModuleNotFoundError: No module named 'draft_events'
_______ ERROR collecting tests/test_f3_d1_sleeper_waiver_intelligence.py _______
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_d1_sleeper_waiver_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_d1_sleeper_waiver_intelligence.py:1: in <module>
    from sleeper_intelligence import available_trending, waiver_candidates
E   ModuleNotFoundError: No module named 'sleeper_intelligence'
____________ ERROR collecting tests/test_f3_d2_faab_intelligence.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_d2_faab_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_d2_faab_intelligence.py:1: in <module>
    from sleeper_intelligence import estimate_faab, waiver_candidates
E   ModuleNotFoundError: No module named 'sleeper_intelligence'
___________ ERROR collecting tests/test_f3_d3_waiver_action_plan.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_d3_waiver_action_plan.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_d3_waiver_action_plan.py:1: in <module>
    from sleeper_intelligence import build_waiver_action_plans, identify_drop_candidates
E   ModuleNotFoundError: No module named 'sleeper_intelligence'
________ ERROR collecting tests/test_f3_d4_waiver_action_integration.py ________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_d4_waiver_action_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_d4_waiver_action_integration.py:1: in <module>
    from services.roster_slots import build_roster_slots
E   ModuleNotFoundError: No module named 'services'
________ ERROR collecting tests/test_f3_d5_waiver_action_publication.py ________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_d5_waiver_action_publication.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_d5_waiver_action_publication.py:3: in <module>
    from services.waiver_action_publication import build_waiver_publication
E   ModuleNotFoundError: No module named 'services'
___________ ERROR collecting tests/test_f3_d5_waiver_action_route.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3_d5_waiver_action_route.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3_d5_waiver_action_route.py:4: in <module>
    from sleeper_intelligence_routes import (
E   ModuleNotFoundError: No module named 'sleeper_intelligence_routes'
__________ ERROR collecting tests/test_f3a1_repository_integration.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3a1_repository_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3a1_repository_integration.py:2: in <module>
    from draft_events.repository_integration import RepositoryCallbacks
E   ModuleNotFoundError: No module named 'draft_events'
_________________ ERROR collecting tests/test_f3a2_runtime.py __________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f3a2_runtime.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f3a2_runtime.py:3: in <module>
    from draft_events.runtime import process_runtime_picks
E   ModuleNotFoundError: No module named 'draft_events'
___________ ERROR collecting tests/test_f4_b_matchup_intelligence.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f4_b_matchup_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f4_b_matchup_intelligence.py:1: in <module>
    from services.matchup_intelligence import build_matchup_intelligence
E   ModuleNotFoundError: No module named 'services'
_____________ ERROR collecting tests/test_f4_c_decision_ranking.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f4_c_decision_ranking.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f4_c_decision_ranking.py:4: in <module>
    from services.decision_ranking import (
E   ModuleNotFoundError: No module named 'services'
___________ ERROR collecting tests/test_f4_d_trade_target_center.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f4_d_trade_target_center.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f4_d_trade_target_center.py:1: in <module>
    from services.trade_target_center import build_trade_target_center, opportunity_score
E   ModuleNotFoundError: No module named 'services'
___________ ERROR collecting tests/test_f4_e_playoff_intelligence.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_f4_e_playoff_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f4_e_playoff_intelligence.py:1: in <module>
    from services.playoff_intelligence import build_playoff_intelligence, standings_order
E   ModuleNotFoundError: No module named 'services'
______________ ERROR collecting tests/test_failed_event_retry.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_failed_event_retry.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_failed_event_retry.py:4: in <module>
    from draft_events.models import DraftEvent
E   ModuleNotFoundError: No module named 'draft_events'
______________ ERROR collecting tests/test_integrity_freshness.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_integrity_freshness.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_integrity_freshness.py:2: in <module>
    from services.integrity import build_freshness_report,build_integrity_report,calculate_confidence_score,calculate_freshness
E   ModuleNotFoundError: No module named 'services'
_____________ ERROR collecting tests/test_integrity_integration.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_integrity_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_integrity_integration.py:1: in <module>
    from services.matchup_intelligence import build_matchup_intelligence
E   ModuleNotFoundError: No module named 'services'
_______________ ERROR collecting tests/test_integrity_service.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_integrity_service.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_integrity_service.py:1: in <module>
    from services.integrity import (
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_mock_draft_state_consistency.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_mock_draft_state_consistency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mock_draft_state_consistency.py:1: in <module>
    from draft_events.runtime import mapped_player_exists
E   ModuleNotFoundError: No module named 'draft_events'
__________ ERROR collecting tests/test_mock_draft_synchronization.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_mock_draft_synchronization.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mock_draft_synchronization.py:3: in <module>
    from draft.draft_state_hardening import build_hardened_sync
E   ModuleNotFoundError: No module named 'draft'
_______________ ERROR collecting tests/test_model_calibration.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_model_calibration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_model_calibration.py:3: in <module>
    from intelligence.model_calibration import calibration_metrics, model_health
E   ModuleNotFoundError: No module named 'intelligence'
_____________ ERROR collecting tests/test_monte_carlo_survival.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_monte_carlo_survival.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_monte_carlo_survival.py:1: in <module>
    from monte_carlo_survival import curve,enhance,run_risks,seed_for,urgency
E   ModuleNotFoundError: No module named 'monte_carlo_survival'
_____________ ERROR collecting tests/test_phase_f2_integration.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_phase_f2_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_phase_f2_integration.py:4: in <module>
    from phase_f.contracts import NormalizedRecommendation
E   ModuleNotFoundError: No module named 'phase_f'
_____________ ERROR collecting tests/test_phase_f_draft_sandbox.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_phase_f_draft_sandbox.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_phase_f_draft_sandbox.py:5: in <module>
    from phase_f.adapters import NoOpRecommendationAdapter
E   ModuleNotFoundError: No module named 'phase_f'
___________________ ERROR collecting tests/test_readiness.py ___________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_readiness.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_readiness.py:3: in <module>
    from readiness import evaluate_readiness
E   ModuleNotFoundError: No module named 'readiness'
___________ ERROR collecting tests/test_recommendation_explainer.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_recommendation_explainer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_recommendation_explainer.py:1: in <module>
    from intelligence.recommendation_explainer import build_explanation
E   ModuleNotFoundError: No module named 'intelligence'
____________ ERROR collecting tests/test_security_and_validation.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_security_and_validation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_security_and_validation.py:13: in <module>
    from yahoo_pickem import PickemGame, build_week
E   ModuleNotFoundError: No module named 'yahoo_pickem'
_____________ ERROR collecting tests/test_survival_calibration.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_survival_calibration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_survival_calibration.py:1: in <module>
    from intelligence.survival_calibration import availability_confidence,build_comparison,severity
E   ModuleNotFoundError: No module named 'intelligence'
_____________ ERROR collecting tests/test_survivor_intelligence.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_survivor_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_survivor_intelligence.py:3: in <module>
    from survivor_intelligence import build_recommendations, summarize
E   ModuleNotFoundError: No module named 'survivor_intelligence'
______________ ERROR collecting tests/test_trade_intelligence.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_trade_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_trade_intelligence.py:1: in <module>
    from services.trade_intelligence import build_trade_intelligence,generate_one_for_one,generate_two_for_one,trade_value
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_verify_f3_b31_postgres_parity.py _________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_verify_f3_b31_postgres_parity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_verify_f3_b31_postgres_parity.py:5: in <module>
    from scripts import verify_f3_b31_postgres_parity as verifier
E   ModuleNotFoundError: No module named 'scripts'
__________ ERROR collecting tests/test_weekly_lineup_intelligence.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_weekly_lineup_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_weekly_lineup_intelligence.py:1: in <module>
    from services.weekly_lineup_intelligence import build_lineup_intelligence,optimize_lineup
E   ModuleNotFoundError: No module named 'services'
_________________ ERROR collecting tests/test_yahoo_pickem.py __________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_yahoo_pickem.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_yahoo_pickem.py:5: in <module>
    from yahoo_pickem import PickemGame, PickemSettings, build_week, calculate_game, fantasy_game_script_adjustment
E   ModuleNotFoundError: No module named 'yahoo_pickem'
=========================== short test summary info ============================
ERROR tests/test_batch_b_outcome_intelligence.py
ERROR tests/test_batch_d_intelligence_operations.py
ERROR tests/test_draft_day_readiness.py
ERROR tests/test_draft_environment_rotation.py
ERROR tests/test_draft_event_pipeline.py
ERROR tests/test_draft_hq_snapshot_integrity.py
ERROR tests/test_draft_operations_hardening.py
ERROR tests/test_draft_recommendation_service.py
ERROR tests/test_draft_state_hardening.py
ERROR tests/test_draftboard_polling.py
ERROR tests/test_f2r_a_local_identity.py
ERROR tests/test_f2r_c_identity_bridge.py
ERROR tests/test_f3_b1_replay_validation.py
ERROR tests/test_f3_b2_reconciliation.py
ERROR tests/test_f3_b31_postgres_parity.py
ERROR tests/test_f3_b3_live_reconciliation.py
ERROR tests/test_f3_b4_readiness.py
ERROR tests/test_f3_c1_publication_gate.py
ERROR tests/test_f3_c2_draft_recommendation_publication.py
ERROR tests/test_f3_d1_sleeper_waiver_intelligence.py
ERROR tests/test_f3_d2_faab_intelligence.py
ERROR tests/test_f3_d3_waiver_action_plan.py
ERROR tests/test_f3_d4_waiver_action_integration.py
ERROR tests/test_f3_d5_waiver_action_publication.py
ERROR tests/test_f3_d5_waiver_action_route.py
ERROR tests/test_f3a1_repository_integration.py
ERROR tests/test_f3a2_runtime.py
ERROR tests/test_f4_b_matchup_intelligence.py
ERROR tests/test_f4_c_decision_ranking.py
ERROR tests/test_f4_d_trade_target_center.py
ERROR tests/test_f4_e_playoff_intelligence.py
ERROR tests/test_failed_event_retry.py
ERROR tests/test_integrity_freshness.py
ERROR tests/test_integrity_integration.py
ERROR tests/test_integrity_service.py
ERROR tests/test_mock_draft_state_consistency.py
ERROR tests/test_mock_draft_synchronization.py
ERROR tests/test_model_calibration.py
ERROR tests/test_monte_carlo_survival.py
ERROR tests/test_phase_f2_integration.py
ERROR tests/test_phase_f_draft_sandbox.py
ERROR tests/test_readiness.py
ERROR tests/test_recommendation_explainer.py
ERROR tests/test_security_and_validation.py
ERROR tests/test_survival_calibration.py
ERROR tests/test_survivor_intelligence.py
ERROR tests/test_trade_intelligence.py
ERROR tests/test_verify_f3_b31_postgres_parity.py
ERROR tests/test_weekly_lineup_intelligence.py
ERROR tests/test_yahoo_pickem.py
!!!!!!!!!!!!!!!!!!! Interrupted: 50 errors during collection !!!!!!!!!!!!!!!!!!!
==================== 24 tests collected, 50 errors in 1.08s ====================

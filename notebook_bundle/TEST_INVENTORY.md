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
tests/test_team_opportunity_integration.py
tests/test_integrity_summary_template.py
tests/test_ux2_health_route_freshness.py
tests/test_readiness.py
tests/test_survivor_intelligence.py
tests/test_trade_evidence_timestamp_writers.py
tests/test_f2r_a_local_identity.py
tests/test_survivor_template_states.py
tests/test_ux2_health_contract.py
tests/test_failed_event_retry.py
tests/test_no_csv_live_weekly_fallback.py
tests/test_gsis_identity_crosswalk.py
tests/test_ux2_1b_presentation.py
tests/test_f4_d_trade_target_center_contract.py
tests/test_injury_health_sync.py
tests/test_mock_draft_synchronization.py
tests/test_integrity_integration.py
tests/test_roster_reconciliation.py
tests/test_trade_scenarios.py
tests/test_recommendation_explainer.py
tests/test_opportunity_consumer_contract.py
tests/test_ux1_dashboard_sleeper_source.py
tests/test_ux2_team_accuracy_route.py
tests/test_phase_f_draft_sandbox.py
tests/test_player_role_evidence.py
tests/test_f3_b3_live_reconciliation.py
tests/test_survivor_status_contract.py
tests/test_f3_b4_readiness.py
tests/test_player_opportunity_reader.py
tests/test_f3_d4_waiver_action_integration.py
tests/helpers/__init__.py
tests/helpers/health_assertions.py
tests/helpers/health_test_cases.py
tests/test_ux2_team_route_matrix.py
tests/test_lineup_evidence.py
tests/test_ux2_sport_specific_evidence.py
tests/test_f3_d5_waiver_action_template.py
tests/test_draft_hq_snapshot_integrity.py
tests/test_matchup_enrichment_validator.py
tests/test_schedule_bye_threshold_registry.py
tests/test_f4_b_matchup_intelligence.py
tests/test_authoritative_week.py
tests/test_nflverse_player_metadata.py
tests/test_batch_b_outcome_intelligence.py
tests/test_ux2_team_needs.py
tests/test_fantasypros_projection.py
tests/test_phase_f2_integration.py
tests/test_schedule_bye_source_contract.py
tests/test_ux5_lineup_route_contract.py
tests/test_opportunity_evidence.py
tests/test_ux2_team_accuracy_template.py
tests/test_f3_d5_waiver_action_publication.py
tests/test_preliminary_matchup_context.py
tests/test_nfl_intelligence_template.py
tests/test_f3a2_runtime.py
tests/test_survival_calibration.py
tests/test_security_and_validation.py
tests/test_f3a1_repository_integration.py
tests/test_week_authority_consolidation.py
tests/test_monte_carlo_survival.py
tests/test_mock_draft_state_consistency.py
tests/test_weekly_evidence_trust_contract.py
tests/test_f4_e_playoff_intelligence.py
tests/test_integrity_freshness.py
tests/test_draft_operations_hardening.py
tests/test_nflverse_defense_matchups.py
tests/test_active_week_degraded_routes.py
tests/test_ux_evidence.py
tests/test_survivor_persistence_contract.py
tests/test_ux2_lineage_template.py
tests/test_player_opportunity_ingestion.py
tests/test_waiver_availability.py
tests/test_unified_decision_context.py
tests/test_draft_recommendation_service.py
tests/test_f3_b31_migration_contract.py
tests/test_draftboard_polling.py
tests/test_f4_ab_command_center_contract.py
tests/test_ux2_health_targeting.py
tests/test_draft_state_hardening.py
tests/test_batch_a_validation_hardening.py
tests/test_ux2_recommendation_contract.py
tests/test_f4_c_decision_ranking.py
tests/test_ux2_team_accuracy.py
tests/test_f3_b31_postgres_parity.py
tests/test_ux2_team_priority.py
tests/test_trade_intelligence_template.py
tests/test_nfl_intelligence.py
tests/test_f4_e_playoff_template.py
tests/test_ux_1_7_completion.py
tests/test_batch_d_intelligence_operations.py
tests/test_trade_intelligence.py
tests/test_draft_environment_rotation.py
tests/test_f3_c2_draft_recommendation_publication.py
tests/test_team_health_routes.py
tests/test_f2r_c_identity_bridge.py
tests/test_ux2_team_hardening.py
tests/test_trade_projection_coverage.py
tests/test_f3_d1_sleeper_waiver_intelligence.py
tests/test_batch_c_post_draft_transition.py
tests/test_snap_share_foundation.py
tests/test_ux1_dashboard_truth_completion.py
tests/test_player_opportunity_calculation.py
tests/test_ux2_batch_a_health_targeting.py
tests/test_draft_day_readiness.py
tests/test_pre_decision_snapshots.py
tests/test_team_health_template.py
tests/test_f3_b2_reconciliation.py
tests/test_f3_d2_faab_intelligence.py
tests/test_ux2_weekly_score_rendering.py
tests/test_integrity_service.py
tests/test_draft_event_pipeline.py


## Pytest Collection

============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/deeoriginalone/fantasy-intelligence
configfile: pytest.ini
testpaths: tests
collected 111 items / 95 errors

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
    <Module test_integrity_summary_template.py>
      <Function test_shared_integrity_component_renders_verified_contract_fields>
      <Function test_lineup_template_includes_shared_integrity_component>
      <Function test_gm_template_includes_lineup_integrity_component>
      <Function test_trades_template_includes_shared_integrity_component>
      <Function test_component_does_not_recalculate_integrity_scores>
      <Function test_component_formats_utc_timestamps_for_manager_readability>
    <Module test_nfl_intelligence_template.py>
      <Function test_page_loads>
      <Function test_no_wagering_terms_rendered>
      <Function test_unavailable_state_renders>
      <Function test_game_list_renders_with_confidence_separate_from_prediction>
      <Function test_game_without_prediction_shows_note_not_hidden>
      <Function test_blocker_states_render>
      <Function test_diagnostics_collapsed_by_default>
      <Function test_full_schedule_renders_even_without_predictions>
      <Function test_top5_team_strength_section_renders_when_supported>
      <Function test_removed_duplicate_sections_do_not_render>
      <Function test_top_signals_never_empty_when_games_exist_without_predictions>
      <Function test_stale_state_renders>
    <Module test_survivor_template_states.py>
      <Function test_page_returns_200>
      <Function test_jax_visible_under_used_teams_and_history>
      <Function test_status_dropdown_preselects_the_current_status_won>
      <Function test_status_dropdown_preselects_the_current_status_pending>
      <Function test_reset_control_present_for_each_history_row_with_confirmation>
      <Function test_history_forms_include_csrf_token>
      <Function test_used_team_status_is_not_color_only>
      <Function test_hero_appears_before_rankings_and_lineage>
      <Function test_full_rankings_collapsed_by_default>
      <Function test_metric_explanations_collapsed_by_default>
      <Function test_lineage_collapsed_and_last>
      <Function test_unavailable_state_renders_required_explanation>
      <Function test_unavailable_state_shows_refresh_button_with_csrf_token>
      <Function test_refresh_button_absent_when_recommendation_is_ready>
      <Function test_blocked_history_state_renders_required_alert>
      <Function test_locked_week_shows_recorded_selection_not_another_pick>
      <Function test_locked_week_shows_next_week_link_when_verified>
      <Function test_locked_week_shows_unavailable_next_week_when_not_verified>
      <Function test_completed_week_shows_result>
      <Function test_locked_week_rankings_labeled_model_snapshot_non_actionable>
      <Function test_ready_state_shows_primary_pick_and_no_neutral_fallback>
      <Function test_completed_week_loss_shows_result>
      <Function test_stale_evidence_state_renders_unavailable_block_not_a_pick>
      <Function test_degraded_state_still_shows_a_disclosed_primary_pick>
      <Function test_missing_evidence_agreement_shows_unavailable_not_a_number>
      <Function test_manual_pick_control_shown_when_week_open_and_teams_eligible>
      <Function test_manual_pick_control_hidden_when_no_eligible_teams>
      <Function test_manual_pick_control_hidden_for_locked_week>
    <Module test_trade_intelligence_template.py>
      <Function test_trade_template_renders_and_has_no_submission_endpoint>
      <Function test_trade_template_keeps_partner_control_and_action_evidence_visible>
      <Function test_trade_template_separates_package_types_and_collapses_metric_definitions>
    <Module test_trade_projection_coverage.py>
      <Function test_projection_importer_uses_normalized_source_team_for_identity_match>
      <Function test_trade_route_preserves_missing_local_players_as_unavailable>
      <Function test_trade_route_uses_suffix_aware_unique_normalized_join>
      <Function test_trade_route_propagates_stable_and_local_identity_lineage>
    <Module test_ux2_1b_presentation.py>
      <Function test_team_needs_summary_uses_jinja_namespace_and_actionable_detail>
      <Function test_shared_health_outage_does_not_render_empty_card_disclosure>
      <Function test_print_hides_navigation_and_closed_diagnostics>
      <Function test_team_needs_and_bench_use_progressive_disclosure>
    <Module test_ux2_health_route_freshness.py>
      <Function test_team_route_uses_sleeper_health_source_without_csv_fallback>
      <Function test_team_route_supports_suffix_tolerant_player_identity_lookup>
    <Module test_ux2_health_targeting.py>
      <Function test_unknown_health_forces_monitor>
      <Function test_healthy_player_remains_start>
    <Module test_ux2_lineage_template.py>
      <Function test_lineage_is_collapsed_in_accessible_native_disclosure>
    <Module test_ux2_recommendation_contract.py>
      <Function test_recommendation_cards_contain_required_labels>
      <Function test_recommendation_table_uses_player_context_fields>
      <Function test_weekly_score_distinguishes_unavailable_from_zero>
      <Function test_recommendation_row_contains_reason_and_confidence>
      <Function test_recommendation_row_contains_blockers>
      <Function test_template_contains_monitor_state>
      <Function test_template_contains_health_column>
      <Function test_recommendation_evidence_exposes_health_impact_and_freshness>
    <Module test_ux2_team_accuracy_route.py>
      <Function test_team_route_builds_and_supplies_accuracy_contract>
      <Function test_team_route_uses_team_health_freshness_for_player_targeting>
      <Function test_team_route_preserves_missing_weekly_score>
      <Function test_team_route_derives_summary_from_shared_team_needs_result>
      <Function test_team_route_supplies_shared_summary_and_detail_payloads>
      <Function test_team_route_builds_summary_once_from_the_shared_result>
    <Module test_ux2_team_accuracy_template.py>
      <Function test_team_template_wires_accuracy_partial>
      <Function test_accuracy_partial_explains_required_domains>
      <Function test_accuracy_partial_renders_matchup_context_from_shared_evidence>
      <Function test_team_template_removes_unsupported_aggregate_metrics>
      <Function test_team_template_distinguishes_unavailable_weekly_score_from_zero>
      <Function test_team_template_renders_explanation_fields>
      <Function test_matchup_rank_contract_is_complete>
      <Function test_team_needs_table_shows_reconciled_dimensions>
    <Module test_ux2_weekly_score_rendering.py>
      <Function test_unavailable_weekly_score_renders_unavailable>
      <Function test_verified_zero_weekly_score_renders_numeric_zero>
      <Function test_supported_weekly_score_renders_two_decimals>
    <Module test_weekly_lineup_template.py>
      <Function test_template_renders_decisions_and_has_no_form>
      <Function test_template_renders_without_optional_lineage_global>

==================================== ERRORS ====================================
__________ ERROR collecting tests/test_active_week_degraded_routes.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_active_week_degraded_routes.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_active_week_degraded_routes.py:5: in <module>
    import nfl_intelligence_routes
E   ModuleNotFoundError: No module named 'nfl_intelligence_routes'
______________ ERROR collecting tests/test_authoritative_week.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_authoritative_week.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_authoritative_week.py:1: in <module>
    from services.authoritative_week import (
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_batch_b_outcome_intelligence.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_batch_b_outcome_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_batch_b_outcome_intelligence.py:3: in <module>
    from draft_outcome_health import build_outcome_health
E   ModuleNotFoundError: No module named 'draft_outcome_health'
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
    from draft_readiness import build_reconciliation
E   ModuleNotFoundError: No module named 'draft_readiness'
__________ ERROR collecting tests/test_draft_environment_rotation.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_draft_environment_rotation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_draft_environment_rotation.py:5: in <module>
    from draft_state_hardening import rotate_draft_environment
E   ModuleNotFoundError: No module named 'draft_state_hardening'
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
    from draft_operations_hardening import invariants
E   ModuleNotFoundError: No module named 'draft_operations_hardening'
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
    from draft_state_hardening import (
E   ModuleNotFoundError: No module named 'draft_state_hardening'
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
____________ ERROR collecting tests/test_fantasypros_projection.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_fantasypros_projection.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_fantasypros_projection.py:1: in <module>
    from services.fantasypros_projection import (
E   ModuleNotFoundError: No module named 'services'
____________ ERROR collecting tests/test_gsis_identity_crosswalk.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_gsis_identity_crosswalk.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_gsis_identity_crosswalk.py:3: in <module>
    from services.gsis_identity_crosswalk import attach_opportunity_player_ids, resolve_gsis_crosswalk
E   ModuleNotFoundError: No module named 'services'
______________ ERROR collecting tests/test_injury_health_sync.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_injury_health_sync.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_injury_health_sync.py:3: in <module>
    from services.injury_health_sync import (
E   ModuleNotFoundError: No module named 'services'
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
________________ ERROR collecting tests/test_lineup_evidence.py ________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_lineup_evidence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_lineup_evidence.py:1: in <module>
    from services.lineup_evidence import build_lineup_evidence, build_matchup_evidence, build_projection_evidence
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_matchup_enrichment_validator.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_matchup_enrichment_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_matchup_enrichment_validator.py:1: in <module>
    from services.matchup_enrichment_validator import validate_matchup_enrichment
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
    from draft_state_hardening import build_hardened_sync
E   ModuleNotFoundError: No module named 'draft_state_hardening'
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
_______________ ERROR collecting tests/test_nfl_intelligence.py ________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_nfl_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_nfl_intelligence.py:3: in <module>
    from nfl_intelligence import build_game, classify_signal, confidence_label, game_action, injury_impact_label, team_signal_payload
E   ModuleNotFoundError: No module named 'nfl_intelligence'
___________ ERROR collecting tests/test_nflverse_defense_matchups.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_nflverse_defense_matchups.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_nflverse_defense_matchups.py:5: in <module>
    from services.defense_matchup_calculation import calculate_defense_matchups, full_ppr_points
E   ModuleNotFoundError: No module named 'services'
___________ ERROR collecting tests/test_nflverse_player_metadata.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_nflverse_player_metadata.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_nflverse_player_metadata.py:1: in <module>
    from services.nflverse_player_metadata import acquire_nflverse_player_metadata
E   ModuleNotFoundError: No module named 'services'
__________ ERROR collecting tests/test_no_csv_live_weekly_fallback.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_no_csv_live_weekly_fallback.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_no_csv_live_weekly_fallback.py:1: in <module>
    from weekly_intelligence import enrich_players
E   ModuleNotFoundError: No module named 'weekly_intelligence'
_________ ERROR collecting tests/test_opportunity_consumer_contract.py _________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_opportunity_consumer_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_opportunity_consumer_contract.py:3: in <module>
    from services.opportunity_evidence import build_opportunity_view
E   ModuleNotFoundError: No module named 'services'
_____________ ERROR collecting tests/test_opportunity_evidence.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_opportunity_evidence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_opportunity_evidence.py:1: in <module>
    from services.opportunity_evidence import DECISION_CENTER_PANELS, METRICS, build_decision_center, build_market_value_evidence, build_nflverse_usage_evidence, build_nflverse_usage_what_changed, build_opportunity_evidence, build_what_changed, classify_market_signal, classify_opportunity_trend, classify_trade_opportunity
E   ModuleNotFoundError: No module named 'services'
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
________ ERROR collecting tests/test_player_opportunity_calculation.py _________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_player_opportunity_calculation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_player_opportunity_calculation.py:1: in <module>
    from services.player_opportunity_calculation import calculate_player_opportunity
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_player_opportunity_ingestion.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_player_opportunity_ingestion.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_player_opportunity_ingestion.py:7: in <module>
    import imports.import_nflverse_opportunity as opportunity_import
E   ModuleNotFoundError: No module named 'imports'
___________ ERROR collecting tests/test_player_opportunity_reader.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_player_opportunity_reader.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_player_opportunity_reader.py:3: in <module>
    from services.player_opportunity_reader import read_player_opportunity, read_player_what_changed
E   ModuleNotFoundError: No module named 'services'
_____________ ERROR collecting tests/test_player_role_evidence.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_player_role_evidence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_player_role_evidence.py:1: in <module>
    from services.player_role_evidence import (
E   ModuleNotFoundError: No module named 'services'
____________ ERROR collecting tests/test_pre_decision_snapshots.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_pre_decision_snapshots.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_pre_decision_snapshots.py:5: in <module>
    from services.pre_decision_snapshots import (
E   ModuleNotFoundError: No module named 'services'
__________ ERROR collecting tests/test_preliminary_matchup_context.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_preliminary_matchup_context.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_preliminary_matchup_context.py:1: in <module>
    from services.preliminary_matchup_context import build_preliminary_matchup_context
E   ModuleNotFoundError: No module named 'services'
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
_____________ ERROR collecting tests/test_roster_reconciliation.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_roster_reconciliation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_roster_reconciliation.py:3: in <module>
    from services.roster_reconciliation import reconcile_roster
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_schedule_bye_source_contract.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_schedule_bye_source_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_schedule_bye_source_contract.py:2: in <module>
    from services.schedule_bye_evidence import evidence_contract
E   ModuleNotFoundError: No module named 'services'
________ ERROR collecting tests/test_schedule_bye_threshold_registry.py ________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_schedule_bye_threshold_registry.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_schedule_bye_threshold_registry.py:2: in <module>
    from services.integrity.integrity_service import BYE_EVIDENCE_THRESHOLD_ID, SCHEDULE_EVIDENCE_THRESHOLD_ID, schedule_bye_freshness_limits
E   ModuleNotFoundError: No module named 'services'
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
_____________ ERROR collecting tests/test_snap_share_foundation.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_snap_share_foundation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_snap_share_foundation.py:6: in <module>
    from imports.import_nflverse_snap_counts import build_pfr_to_gsis_crosswalk, build_snap_share_evidence
E   ModuleNotFoundError: No module named 'imports'
_____________ ERROR collecting tests/test_survival_calibration.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_survival_calibration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_survival_calibration.py:1: in <module>
    from survival_calibration import availability_confidence,build_comparison,severity
E   ModuleNotFoundError: No module named 'survival_calibration'
_____________ ERROR collecting tests/test_survivor_intelligence.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_survivor_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_survivor_intelligence.py:3: in <module>
    from survivor_intelligence import build_recommendations, stability_score, summarize
E   ModuleNotFoundError: No module named 'survivor_intelligence'
_________ ERROR collecting tests/test_survivor_persistence_contract.py _________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_survivor_persistence_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_survivor_persistence_contract.py:3: in <module>
    from survivor_store import (
E   ModuleNotFoundError: No module named 'survivor_store'
___________ ERROR collecting tests/test_survivor_status_contract.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_survivor_status_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_survivor_status_contract.py:3: in <module>
    from survivor_intelligence import build_status, evidence_freshness_state
E   ModuleNotFoundError: No module named 'survivor_intelligence'
______________ ERROR collecting tests/test_team_health_routes.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_team_health_routes.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_team_health_routes.py:5: in <module>
    from tests.helpers.health_assertions import assert_unknown_state_rendered
E   ModuleNotFoundError: No module named 'tests'
_____________ ERROR collecting tests/test_team_health_template.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_team_health_template.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_team_health_template.py:5: in <module>
    from tests.helpers.health_assertions import assert_unknown_state_rendered
E   ModuleNotFoundError: No module named 'tests'
_________ ERROR collecting tests/test_team_opportunity_integration.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_team_opportunity_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_team_opportunity_integration.py:3: in <module>
    import owner_operations
E   ModuleNotFoundError: No module named 'owner_operations'
_______ ERROR collecting tests/test_trade_evidence_timestamp_writers.py ________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_trade_evidence_timestamp_writers.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_trade_evidence_timestamp_writers.py:2: in <module>
    from imports.import_draft_intelligence import normalize_team
E   ModuleNotFoundError: No module named 'imports'
______________ ERROR collecting tests/test_trade_intelligence.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_trade_intelligence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_trade_intelligence.py:1: in <module>
    from services.trade_intelligence import build_trade_intelligence,generate_one_for_one,generate_two_for_one,trade_evidence_coverage,trade_freshness_metadata,trade_identity_lineage,trade_value
E   ModuleNotFoundError: No module named 'services'
________________ ERROR collecting tests/test_trade_scenarios.py ________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_trade_scenarios.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_trade_scenarios.py:3: in <module>
    from services.trade_scenarios import build_trade_scenario
E   ModuleNotFoundError: No module named 'services'
___________ ERROR collecting tests/test_unified_decision_context.py ____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_unified_decision_context.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_unified_decision_context.py:1: in <module>
    from services.unified_decision_context import build_unified_decision_context
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_ux1_dashboard_sleeper_source.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux1_dashboard_sleeper_source.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux1_dashboard_sleeper_source.py:1: in <module>
    import app as application
E   ModuleNotFoundError: No module named 'app'
________ ERROR collecting tests/test_ux1_dashboard_truth_completion.py _________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux1_dashboard_truth_completion.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux1_dashboard_truth_completion.py:2: in <module>
    from services.ux_evidence import dashboard_agreement_evidence, dashboard_state_contract, format_pacific_datetime, shared_league_facts
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_ux2_batch_a_health_targeting.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_batch_a_health_targeting.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_batch_a_health_targeting.py:1: in <module>
    from services.team_health import apply_player_health_to_recommendations
E   ModuleNotFoundError: No module named 'services'
______________ ERROR collecting tests/test_ux2_health_contract.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_health_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_health_contract.py:3: in <module>
    from services.team_health import health_freshness_from_report_date, normalize_health, player_health_contract, team_health_contract
E   ModuleNotFoundError: No module named 'services'
__________ ERROR collecting tests/test_ux2_sport_specific_evidence.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_sport_specific_evidence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_sport_specific_evidence.py:1: in <module>
    from services.team_health import team_health_contract
E   ModuleNotFoundError: No module named 'services'
_______________ ERROR collecting tests/test_ux2_team_accuracy.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_team_accuracy.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_team_accuracy.py:1: in <module>
    from services.lineup_evidence import build_matchup_evidence
E   ModuleNotFoundError: No module named 'services'
______________ ERROR collecting tests/test_ux2_team_hardening.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_team_hardening.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_team_hardening.py:1: in <module>
    from services.team_hardening import build_bench_decisions, build_roster_outlook, build_team_trust_summary, build_weekly_risks
E   ModuleNotFoundError: No module named 'services'
________________ ERROR collecting tests/test_ux2_team_needs.py _________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_team_needs.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_team_needs.py:1: in <module>
    from services.team_needs import build_team_needs_summary, league_settings_contract, team_needs_contract
E   ModuleNotFoundError: No module named 'services'
_______________ ERROR collecting tests/test_ux2_team_priority.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_team_priority.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_team_priority.py:1: in <module>
    from services.team_priority import build_team_priority_action
E   ModuleNotFoundError: No module named 'services'
_____________ ERROR collecting tests/test_ux2_team_route_matrix.py _____________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux2_team_route_matrix.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux2_team_route_matrix.py:6: in <module>
    import owner_operations
E   ModuleNotFoundError: No module named 'owner_operations'
___________ ERROR collecting tests/test_ux5_lineup_route_contract.py ___________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux5_lineup_route_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux5_lineup_route_contract.py:3: in <module>
    from services.weekly_lineup_intelligence import build_lineup_intelligence
E   ModuleNotFoundError: No module named 'services'
_______________ ERROR collecting tests/test_ux_1_7_completion.py _______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux_1_7_completion.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux_1_7_completion.py:2: in <module>
    from services.ux_evidence import evidence,page_evidence,lineup_explanations,waiver_explanations,gm_action_evidence,roster_lineage
E   ModuleNotFoundError: No module named 'services'
__________________ ERROR collecting tests/test_ux_evidence.py __________________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_ux_evidence.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ux_evidence.py:1: in <module>
    from services.ux_evidence import dashboard_contract,evidence,filter_available_waivers,roster_lineage
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
______________ ERROR collecting tests/test_waiver_availability.py ______________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_waiver_availability.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_waiver_availability.py:4: in <module>
    from services.ux_evidence import derived_waiver_availability, evaluate_waiver_availability, resolve_waiver_candidate_identity, waiver_evidence_contract, waiver_ownership_freshness, waiver_roster_coverage
E   ModuleNotFoundError: No module named 'services'
_________ ERROR collecting tests/test_week_authority_consolidation.py __________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_week_authority_consolidation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_week_authority_consolidation.py:3: in <module>
    from services.authoritative_week import build_authoritative_week_contract, resolve_week_owners
E   ModuleNotFoundError: No module named 'services'
________ ERROR collecting tests/test_weekly_evidence_trust_contract.py _________
ImportError while importing test module '/home/deeoriginalone/fantasy-intelligence/tests/test_weekly_evidence_trust_contract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.14/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_weekly_evidence_trust_contract.py:3: in <module>
    from weekly_intelligence import enrich_players
E   ModuleNotFoundError: No module named 'weekly_intelligence'
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
ERROR tests/test_active_week_degraded_routes.py
ERROR tests/test_authoritative_week.py
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
ERROR tests/test_fantasypros_projection.py
ERROR tests/test_gsis_identity_crosswalk.py
ERROR tests/test_injury_health_sync.py
ERROR tests/test_integrity_freshness.py
ERROR tests/test_integrity_integration.py
ERROR tests/test_integrity_service.py
ERROR tests/test_lineup_evidence.py
ERROR tests/test_matchup_enrichment_validator.py
ERROR tests/test_mock_draft_state_consistency.py
ERROR tests/test_mock_draft_synchronization.py
ERROR tests/test_monte_carlo_survival.py
ERROR tests/test_nfl_intelligence.py
ERROR tests/test_nflverse_defense_matchups.py
ERROR tests/test_nflverse_player_metadata.py
ERROR tests/test_no_csv_live_weekly_fallback.py
ERROR tests/test_opportunity_consumer_contract.py
ERROR tests/test_opportunity_evidence.py
ERROR tests/test_phase_f2_integration.py
ERROR tests/test_phase_f_draft_sandbox.py
ERROR tests/test_player_opportunity_calculation.py
ERROR tests/test_player_opportunity_ingestion.py
ERROR tests/test_player_opportunity_reader.py
ERROR tests/test_player_role_evidence.py
ERROR tests/test_pre_decision_snapshots.py
ERROR tests/test_preliminary_matchup_context.py
ERROR tests/test_readiness.py
ERROR tests/test_recommendation_explainer.py
ERROR tests/test_roster_reconciliation.py
ERROR tests/test_schedule_bye_source_contract.py
ERROR tests/test_schedule_bye_threshold_registry.py
ERROR tests/test_security_and_validation.py
ERROR tests/test_snap_share_foundation.py
ERROR tests/test_survival_calibration.py
ERROR tests/test_survivor_intelligence.py
ERROR tests/test_survivor_persistence_contract.py
ERROR tests/test_survivor_status_contract.py
ERROR tests/test_team_health_routes.py
ERROR tests/test_team_health_template.py
ERROR tests/test_team_opportunity_integration.py
ERROR tests/test_trade_evidence_timestamp_writers.py
ERROR tests/test_trade_intelligence.py
ERROR tests/test_trade_scenarios.py
ERROR tests/test_unified_decision_context.py
ERROR tests/test_ux1_dashboard_sleeper_source.py
ERROR tests/test_ux1_dashboard_truth_completion.py
ERROR tests/test_ux2_batch_a_health_targeting.py
ERROR tests/test_ux2_health_contract.py
ERROR tests/test_ux2_sport_specific_evidence.py
ERROR tests/test_ux2_team_accuracy.py
ERROR tests/test_ux2_team_hardening.py
ERROR tests/test_ux2_team_needs.py
ERROR tests/test_ux2_team_priority.py
ERROR tests/test_ux2_team_route_matrix.py
ERROR tests/test_ux5_lineup_route_contract.py
ERROR tests/test_ux_1_7_completion.py
ERROR tests/test_ux_evidence.py
ERROR tests/test_verify_f3_b31_postgres_parity.py
ERROR tests/test_waiver_availability.py
ERROR tests/test_week_authority_consolidation.py
ERROR tests/test_weekly_evidence_trust_contract.py
ERROR tests/test_weekly_lineup_intelligence.py
ERROR tests/test_yahoo_pickem.py
!!!!!!!!!!!!!!!!!!! Interrupted: 95 errors during collection !!!!!!!!!!!!!!!!!!!
=================== 111 tests collected, 95 errors in 3.85s ====================

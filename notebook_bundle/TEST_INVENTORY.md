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
tests/test_integrity_summary_template.py
tests/test_readiness.py
tests/test_ux_1_7_large_batch.py
tests/test_survivor_intelligence.py
tests/test_f2r_a_local_identity.py
tests/test_failed_event_retry.py
tests/test_f4_d_trade_target_center_contract.py
tests/test_injury_health_sync.py
tests/test_mock_draft_synchronization.py
tests/test_integrity_integration.py
tests/test_roster_reconciliation.py
tests/test_recommendation_explainer.py
tests/test_ux1_dashboard_sleeper_source.py
tests/test_phase_f_draft_sandbox.py
tests/test_f3_b3_live_reconciliation.py
tests/test_f3_b4_readiness.py
tests/test_f3_d4_waiver_action_integration.py
tests/test_f3_d5_waiver_action_template.py
tests/test_draft_hq_snapshot_integrity.py
tests/test_matchup_enrichment_validator.py
tests/test_f4_b_matchup_intelligence.py
tests/test_model_calibration.py
tests/test_batch_b_outcome_intelligence.py
tests/test_phase_f2_integration.py
tests/conftest.py
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
tests/test_ux_evidence.py
tests/test_draft_recommendation_service.py
tests/test_f3_b31_migration_contract.py
tests/test_draftboard_polling.py
tests/test_f4_ab_command_center_contract.py
tests/test_draft_state_hardening.py
tests/test_ux_1_7_final_completion.py
tests/test_batch_a_validation_hardening.py
tests/test_f4_c_decision_ranking.py
tests/test_f3_d3_waiver_action_plan.py
tests/test_f3_b31_postgres_parity.py
tests/test_trade_intelligence_template.py
tests/test_f4_e_playoff_template.py
tests/test_ux_1_7_completion.py
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
collected 441 items

<Dir fantasy-intelligence>
  <Dir tests>
    <Module test_batch_a_validation_hardening.py>
      <Function test_sources_parse>
      <Function test_publication_gate>
    <Module test_batch_b_outcome_intelligence.py>
      <Function test_calibration_metrics_known_values>
      <Function test_calibration_stays_inactive_below_threshold>
      <Function test_calibration_weights_are_bounded_and_normalized>
      <Function test_accuracy_summary_reports_models_and_recent_rows>
      <Function test_outcome_health_combines_counts_accuracy_and_calibration>
    <Module test_batch_c_post_draft_transition.py>
      <Function test_ready_when_identity_counts_and_invariants_pass>
      <Function test_remote_draft_must_be_complete>
      <Function test_count_mismatch_blocks_transition>
      <Function test_finalize_is_idempotent_when_state_is_active>
      <Function test_finalize_materializes_and_transitions>
    <Module test_batch_d_intelligence_operations.py>
      <Function test_explanation_components_and_edge>
      <Function test_explanation_rejects_bad_weights>
      <Function test_readiness_publish_gate>
      <Function test_input_validation_rejects_duplicate_and_bad_yahoo_sum>
      <Function test_reconciliation_signals>
      <Function test_calibration_metrics>
      <Function test_report_blocks_without_readiness>
      <Function test_report_generates_from_real_inputs_only>
    <Module test_db_config_contract.py>
      <Function test_config_db_kwargs_returns_expected_fields>
      <Function test_pickem_store_uses_centralized_config>
      <Function test_main_app_and_pickem_store_resolve_same_settings>
      <Function test_fi_db_values_do_not_redirect_active_pickem_store>
      <Function test_missing_required_db_configuration_raises_controlled_error>
      <Function test_psycopg_connect_is_not_called_with_real_db>
    <Module test_draft_day_readiness.py>
      <Function test_predraft_empty_ready>
      <Function test_identity_mismatch_blocks>
      <Function test_live_count_mismatch_blocks>
    <Module test_draft_environment_rotation.py>
      <Function test_matching_live_rotation_succeeds_and_syncs_destination>
      <Function test_rotation_reports_degraded_success_when_health_refresh_fails>
      <Function test_rotation_reports_degraded_success_when_synchronize_fails>
      <Function test_mock_a_to_mock_b_rotation_preserves_history_and_clears_active_state>
      <Function test_explicit_mock_rotation_can_leave_live_session_without_deleting_history>
      <Function test_mock_mode_cannot_target_protected_live_draft>
      <Function test_invalid_destination_fails_before_database_mutation_or_sync>
      <Function test_live_draft_id_mismatch_fails_before_database_mutation>
      <Function test_live_league_mismatch_fails_before_database_mutation>
      <Function test_reset_failure_rolls_back_authority_and_derived_state>
      <Function test_advisory_lock_serializes_rotation_transaction>
    <Module test_draft_event_pipeline.py>
      <UnitTestCase PipelineTests>
        <TestCaseFunction test_atomic_rollback>
        <TestCaseFunction test_callbacks>
        <TestCaseFunction test_duplicate_event_is_noop>
        <TestCaseFunction test_duplicate_pick_number>
        <TestCaseFunction test_invalid_round_pick>
        <TestCaseFunction test_missing_required>
        <TestCaseFunction test_out_of_order_reconstructs_order>
        <TestCaseFunction test_payload_retention>
        <TestCaseFunction test_replay_after_partial_failure>
        <TestCaseFunction test_same_player_twice>
        <TestCaseFunction test_unknown_owner>
        <TestCaseFunction test_unknown_player>
        <TestCaseFunction test_valid_selection>
    <Module test_draft_hq_snapshot_integrity.py>
      <Function test_unresolved_current_picks_block_recommendations>
      <Function test_live_draft_signals_use_active_snapshot_not_cached_league_draft>
    <Module test_draft_operations_hardening.py>
      <Function test_clean>
      <Function test_bad>
    <Module test_draft_recommendation_service.py>
      <Function test_requires_id>
      <Function test_ranks_and_preserves_shape>
      <Function test_excludes_kicker_early>
    <Module test_draft_state_hardening.py>
      <Function test_reset_clears_only_derived_tables_and_preserves_history_tables>
      <Function test_reset_validation_failure_fails_closed>
      <Function test_session_status_fails_closed_on_authoritative_identity_mismatch>
      <Function test_draft_transition_detects_changed_authoritative_id>
      <Function test_derived_state_counts_default_to_zero_when_tables_are_missing>
      <Function test_ensure_schema_bootstraps_health_and_calibration_tables_for_fresh_db>
      <Function test_capture_derived_state_defaults_to_empty_when_tables_are_missing>
      <Function test_reset_draft_session_ignores_missing_derived_tables_on_first_run>
      <Function test_standalone_mock_metadata_uses_configured_league_when_allowed>
      <Function test_identity_valid>
      <Function test_pre_draft_mock_identity_requires_explicit_mock_mode>
      <Function test_draft_mismatch>
      <Function test_league_mismatch>
    <Module test_draftboard_polling.py>
      <Function test_polling_template_uses_authenticated_post_contract>
      <Function test_anonymous_polling_is_rejected>
      <Function test_authenticated_empty_poll_returns_json_array>
    <Module test_f2r_a_local_identity.py>
      <Function test_integer_local_id_is_normalized_to_string>
      <Function test_draft_state_excludes_same_normalized_local_id>
    <Module test_f2r_c_identity_bridge.py>
      <Function test_exact_mapping>
      <Function test_unknown_is_unmatched>
      <Function test_multiple_local_ids_are_conflict>
      <Function test_cache_calls_repository_once>
      <Function test_sleeper_event_uses_local_id>
      <Function test_event_blocks_unmatched>
      <Function test_snapshot_contains_both_identities>
    <Module test_f3_b1_replay_validation.py>
      <UnitTestCase LargeBatchReplayValidationTests>
        <TestCaseFunction test_001_baseline_large_batch_import>
        <TestCaseFunction test_002_identical_replay_is_idempotent>
        <TestCaseFunction test_003_ten_replays_do_not_change_state>
        <TestCaseFunction test_004_partial_prefix_then_complete_batch_adds_only_missing_events>
        <TestCaseFunction test_005_reverse_order_import_reconstructs_pick_order>
        <TestCaseFunction test_006_conflicting_event_id_for_existing_pick_fails_without_state_drift>
        <TestCaseFunction test_007_conflicting_player_for_new_pick_fails_without_selection_drift>
        <TestCaseFunction test_008_mid_batch_callback_failure_rolls_back_failed_selection_then_replays>
    <Module test_f3_b2_reconciliation.py>
      <UnitTestCase LargeBatchReconciliationTests>
        <TestCaseFunction test_001_exact_1000_pick_match_passes>
        <TestCaseFunction test_002_missing_local_pick_is_reported>
        <TestCaseFunction test_003_extra_local_pick_is_reported>
        <TestCaseFunction test_004_player_mismatch_is_reported>
        <TestCaseFunction test_005_roster_mismatch_is_reported>
        <TestCaseFunction test_006_event_id_mismatch_is_reported>
        <TestCaseFunction test_007_non_applied_event_is_reported>
        <TestCaseFunction test_008_duplicate_source_pick_is_reported>
        <TestCaseFunction test_009_duplicate_source_player_is_reported>
        <TestCaseFunction test_010_foreign_draft_source_event_is_reported>
        <TestCaseFunction test_011_report_serializes_to_json_ready_dictionary>
    <Module test_f3_b31_migration_contract.py>
      <Function test_clean_install_keeps_event_log_unconstrained_and_selection_state_unique>
      <Function test_upgrade_drops_only_obsolete_event_log_constraints_idempotently>
    <Module test_f3_b31_postgres_parity.py>
      <UnitTestCase InMemoryParityReferenceTests>
        <TestCaseFunction test_001_contract_methods_exist>
        <TestCaseFunction test_002_baseline_large_batch_import>
        <TestCaseFunction test_003_identical_replay_is_idempotent>
        <TestCaseFunction test_004_repeated_replay_is_stable>
        <TestCaseFunction test_005_partial_replay_adds_only_missing>
        <TestCaseFunction test_006_duplicate_pick_is_failed_and_selection_is_stable>
        <TestCaseFunction test_007_duplicate_player_is_failed_and_selection_is_stable>
        <TestCaseFunction test_008_reconciliation_exact_match>
        <TestCaseFunction test_009_reconciliation_detects_missing_local_pick>
      <UnitTestCase PostgreSQLParityTests>
        <TestCaseFunction test_001_contract_methods_exist>
        <TestCaseFunction test_002_baseline_large_batch_import>
        <TestCaseFunction test_003_identical_replay_is_idempotent>
        <TestCaseFunction test_004_repeated_replay_is_stable>
        <TestCaseFunction test_005_partial_replay_adds_only_missing>
        <TestCaseFunction test_006_duplicate_pick_is_failed_and_selection_is_stable>
        <TestCaseFunction test_007_duplicate_player_is_failed_and_selection_is_stable>
        <TestCaseFunction test_008_reconciliation_exact_match>
        <TestCaseFunction test_009_reconciliation_detects_missing_local_pick>
    <Module test_f3_b3_live_reconciliation.py>
      <UnitTestCase LiveSleeperReconciliationTests>
        <TestCaseFunction test_001_pre_draft_zero_picks_is_ready_waiting>
        <TestCaseFunction test_002_pre_draft_zero_source_with_local_state_is_blocked>
        <TestCaseFunction test_003_exact_1000_pick_live_match_passes>
        <TestCaseFunction test_004_missing_local_pick_is_blocked>
        <TestCaseFunction test_005_extra_local_pick_is_blocked>
        <TestCaseFunction test_006_player_mismatch_is_blocked>
        <TestCaseFunction test_007_metadata_unavailable_is_blocked>
        <TestCaseFunction test_008_metadata_draft_id_mismatch_is_blocked>
        <TestCaseFunction test_009_normalization_failure_is_blocked>
        <TestCaseFunction test_010_complete_draft_match_passes>
        <TestCaseFunction test_011_report_is_json_ready>
        <TestCaseFunction test_012_service_does_not_write_to_local_store>
    <Module test_f3_b4_readiness.py>
      <UnitTestCase ReadinessGateTests>
        <TestCaseFunction test_001_everything_healthy_is_ready_and_publishable>
        <TestCaseFunction test_002_warning_blocks_publication_by_default>
        <TestCaseFunction test_003_warning_can_publish_only_when_policy_explicitly_allows_it>
        <TestCaseFunction test_004_reconciliation_failure_blocks>
        <TestCaseFunction test_005_sleeper_unavailable_blocks>
        <TestCaseFunction test_006_recommendation_engine_unavailable_blocks>
        <TestCaseFunction test_007_multiple_warnings_remain_warning>
        <TestCaseFunction test_008_warning_plus_blocker_is_blocked>
        <TestCaseFunction test_009_missing_required_component_blocks>
        <TestCaseFunction test_010_duplicate_component_is_rejected>
        <TestCaseFunction test_011_stale_component_blocks>
        <TestCaseFunction test_012_fresh_component_passes>
        <TestCaseFunction test_013_missing_freshness_timestamp_blocks_when_policy_requires_age>
        <TestCaseFunction test_014_future_timestamp_warns>
        <TestCaseFunction test_015_json_serialization_contains_authoritative_decision>
        <TestCaseFunction test_016_engine_is_read_only_for_input_components>
    <Module test_f3_c1_publication_gate.py>
      <UnitTestCase PublicationGateTests>
        <TestCaseFunction test_001_ready_allows_publication>
        <TestCaseFunction test_002_warning_is_blocked_by_default>
        <TestCaseFunction test_003_blocked_reconciliation_denies_publication>
        <TestCaseFunction test_004_warning_override_allows_publication>
        <TestCaseFunction test_005_missing_required_component_denies_publication>
        <TestCaseFunction test_006_require_ready_returns_decision_when_allowed>
        <TestCaseFunction test_007_require_ready_raises_with_decision_when_blocked>
        <TestCaseFunction test_008_execute_calls_publisher_exactly_once_when_ready>
        <TestCaseFunction test_009_execute_never_calls_publisher_when_blocked>
        <TestCaseFunction test_010_decision_preserves_component_statuses>
        <TestCaseFunction test_011_decision_metadata_is_preserved>
        <TestCaseFunction test_012_decision_is_json_ready>
        <TestCaseFunction test_013_empty_workflow_is_rejected>
        <TestCaseFunction test_014_duplicate_reason_codes_are_deduplicated>
        <TestCaseFunction test_015_gate_does_not_modify_readiness_report>
    <Module test_f3_c2_draft_recommendation_publication.py>
      <UnitTestCase DraftRecommendationPublicationTests>
        <TestCaseFunction test_001_ready_publishes_all_recommendations>
        <TestCaseFunction test_002_warning_suppresses_by_default>
        <TestCaseFunction test_003_blocked_reconciliation_suppresses>
        <TestCaseFunction test_004_empty_recommendations_remain_empty>
        <TestCaseFunction test_005_metadata_reaches_decision>
        <TestCaseFunction test_006_result_is_json_ready>
        <TestCaseFunction test_007_input_list_is_not_modified>
        <TestCaseFunction test_008_readiness_json_round_trip>
    <Module test_f3_d1_sleeper_waiver_intelligence.py>
      <Function test_owned_players_are_filtered>
      <Function test_primary_need_bonus_can_change_rank>
      <Function test_score_is_explainable>
      <Function test_non_core_positions_are_ignored>
      <Function test_limit_is_enforced>
      <Function test_empty_inputs_are_safe>
      <Function test_reason_mentions_primary_need>
      <Function test_zero_trend_candidate_is_deterministic>
    <Module test_f3_d2_faab_intelligence.py>
      <Function test_tiers>
      <Function test_primary_need_premium>
      <Function test_ranges_bounded>
      <Function test_budget_conversion>
      <Function test_zero_budget>
      <Function test_candidate_has_faab_fields>
      <Function test_no_budget_keeps_percent_only>
      <Function test_negative_budget_rejected>
    <Module test_f3_d3_waiver_action_plan.py>
      <Function test_surplus_position_preferred>
      <Function test_needed_position_protected>
      <Function test_empty_and_malformed_safe>
      <Function test_drop_is_explainable>
      <Function test_plan_pairs_add_and_drop>
      <Function test_drop_not_reused>
      <Function test_add_only_when_no_drop>
      <Function test_empty_adds_and_limit>
      <Function test_inputs_not_modified>
    <Module test_f3_d4_waiver_action_integration.py>
      <Function test_shared_slot_assignment_matches_repository_shape>
      <Function test_local_context_contains_verified_bench_counts_and_needs>
      <Function test_local_context_empty_roster_is_safe>
      <Function test_context_drives_action_plans_without_starters_as_drops>
      <Function test_context_preserves_original_roster_rows>
    <Module test_f3_d5_waiver_action_publication.py>
      <Function test_blocked_report_fails_closed>
      <Function test_ready_report_publishes_existing_contract>
      <Function test_unknown_budget_does_not_publish_unit_bid>
      <Function test_explicit_starter_drop_is_rejected>
    <Module test_f3_d5_waiver_action_route.py>
      <Function test_html_route_fails_closed_when_readiness_path_missing>
      <Function test_json_contract_remains_unchanged>
    <Module test_f3_d5_waiver_action_template.py>
      <Function test_blocked_state_renders_reason>
      <Function test_plan_renders_f3_d4_fields_without_unknown_bid>
    <Module test_f3a1_repository_integration.py>
      <UnitTestCase IntegrationTests>
        <TestCaseFunction test_repository_callbacks>
        <TestCaseFunction test_sleeper_batch_is_idempotent>
        <TestCaseFunction test_sleeper_ingestion>
    <Module test_f3a2_runtime.py>
      <UnitTestCase RuntimeTests>
        <TestCaseFunction test_existing_writes_are_noops_in_runtime_contract>
        <TestCaseFunction test_runtime_summary>
    <Module test_f4_ab_command_center_contract.py>
      <Function test_gm_template_contract>
      <Function test_owner_integration_contract>
    <Module test_f4_b_matchup_intelligence.py>
      <Function test_favorable_and_difficult>
      <Function test_missing_evidence_is_preserved>
      <Function test_starter_filter>
      <Function test_bye_unavailable>
    <Module test_f4_c_decision_ranking.py>
      <Function test_score_is_deterministic_and_bounded>
      <Function test_blocked_action_scores_zero_and_is_separated>
      <Function test_ranking_orders_score_then_stable_tiebreakers>
      <Function test_duplicate_ids_fail_closed>
      <Function test_lineup_adapter_uses_only_swap_decisions>
      <Function test_waiver_adapter_preserves_bid_metadata_without_inventing_units>
      <Function test_trade_adapter_preserves_package_and_owner_gain>
      <Function test_build_decision_ranking_does_not_mutate_inputs>
      <Function test_validation_rejects_unsupported_category_and_missing_contract>
    <Module test_f4_d_trade_target_center.py>
      <Function test_score_deterministic_bounded>
      <Function test_ranking>
      <Function test_market_signals_from_supplied_fields>
      <Function test_profiles_and_no_submission>
      <Function test_blocked_empty_fails_closed>
    <Module test_f4_d_trade_target_center_contract.py>
      <Function test_template_contract>
      <Function test_route_contract>
    <Module test_f4_e_playoff_intelligence.py>
      <Function test_standings_order_is_deterministic>
      <Function test_playoff_contract_and_no_input_mutation>
      <Function test_missing_owner_fails_closed>
      <Function test_unknown_schedule_is_reported_not_invented>
    <Module test_f4_e_playoff_template.py>
      <Function test_playoff_template_renders_and_has_no_submission_endpoint>
    <Module test_failed_event_retry.py>
      <Function test_failed_event_retry_refreshes_corrected_ownership_metadata>
      <Function test_applied_event_refreshes_corrected_metadata_without_reapplying>
      <Function test_postgres_applied_metadata_refresh_preserves_stored_ownership_on_nulls>
    <Module test_injury_health_sync.py>
      <Function test_verified_snapshot_preserves_timestamp_and_statuses>
      <Function test_missing_timestamp_fails_closed_without_invention>
      <Function test_missing_source_fails_closed>
      <Function test_unmapped_health_is_partial_and_caps_confidence>
      <Function test_missing_roster_player_id_fails_closed>
      <Function test_duplicate_ids_fail_closed>
      <Function test_normalization_and_multipliers_are_conservative>
      <Function test_input_rows_are_not_mutated>
    <Module test_integrity_freshness.py>
      <Function test_fresh>
      <Function test_unknown>
      <Function test_stale_expired>
      <Function test_unknown_health_low>
      <Function test_missing_matchup_low>
      <Function test_bye_high>
      <Function test_ready>
      <Function test_unknown_freshness_blocked>
      <Function test_domains>
    <Module test_integrity_integration.py>
      <Function test_matchup_contract_includes_shared_integrity>
      <Function test_lineup_contract_includes_shared_integrity>
      <Function test_missing_health_and_matchup_are_visible_in_both_contracts>
      <Function test_freshness_metadata_flows_through_both_contracts>
      <Function test_missing_freshness_metadata_remains_unknown_in_both_contracts>
    <Module test_integrity_service.py>
      <Function test_complete_player_scores_100>
      <Function test_missing_matchup_lowers_score>
      <Function test_integrity_report_builds>
    <Module test_integrity_summary_template.py>
      <Function test_shared_integrity_component_renders_verified_contract_fields>
      <Function test_lineup_template_includes_shared_integrity_component>
      <Function test_gm_template_includes_lineup_integrity_component>
      <Function test_component_does_not_recalculate_integrity_scores>
    <Module test_matchup_enrichment_validator.py>
      <Function test_complete_matchup_is_verified>
      <Function test_empty_roster_fails_closed>
      <Function test_missing_timestamp_fails_closed_without_invention>
      <Function test_missing_opponent_is_partial_and_capped>
      <Function test_missing_rank_is_explicit>
      <Function test_missing_modifier_is_explicit_and_zero_is_valid>
      <Function test_bye_week_does_not_require_matchup_fields>
      <Function test_partial_coverage_reports_exact_players>
      <Function test_input_is_not_mutated>
    <Module test_mock_draft_state_consistency.py>
      <Function test_draft_slot_fallback_enriches_pick_with_missing_owner>
      <Function test_draft_slot_fallback_supports_string_slots_with_integer_keys>
      <Function test_picked_by_owner_mapping_precedes_draft_slot_mapping>
      <Function test_existing_roster_id_is_preserved>
      <Function test_unresolved_pick_remains_unresolved>
      <Function test_player_mapping_uses_existing_local_player_name_column>
      <Function test_player_mapping_allows_normalized_local_name_fallback>
    <Module test_mock_draft_synchronization.py>
      <Function test_verified_mock_draft_reaches_synchronization_persistence>
      <Function test_incomplete_mock_metadata_remains_fail_closed>
      <Function test_live_league_identity_synchronizes_with_matching_league_and_draft>
      <Function test_invalid_mock_identity_preserves_session_and_skips_original_sync>
    <Module test_model_calibration.py>
      <Function test_calibration_metrics_falls_back_to_zero_samples_when_table_missing>
      <Function test_calibration_metrics_rolls_back_connection_so_later_queries_are_not_poisoned>
      <Function test_model_health_is_safe_on_fresh_database_with_no_outcome_table>
    <Module test_monte_carlo_survival.py>
      <Function test_curve_monotonic>
      <Function test_curve_bounds>
      <Function test_seed_deterministic>
      <Function test_urgency>
      <Function test_run_risk>
      <Function test_enhance_preserves_terminal>
    <Module test_phase_f2_integration.py>
      <Function test_normalizes_mapping>
      <Function test_requires_read_only>
      <Function test_blocks_drafted_recommendation>
      <Function test_freshness_gate>
      <Function test_snapshot_writer>
      <Function test_outcome_evaluation>
      <Function test_known_strategy>
    <Module test_phase_f_draft_sandbox.py>
      <Function test_complete_mock_draft>
      <Function test_rejects_out_of_order_pick>
      <Function test_rejects_duplicate_player>
      <Function test_json_lines_source>
    <Module test_readiness.py>
      <Function test_ready_state>
      <Function test_approximate_state_for_missing_optional_input>
      <Function test_incomplete_for_missing_required_input>
      <Function test_stale_market_data>
      <Function test_stale_crowd_data>
      <Function test_stale_injury_data>
      <Function test_missing_qb_status_is_approximate_or_incomplete>
      <Function test_duplicate_game_blocks_publication>
      <Function test_missing_market_probability_blocks>
      <Function test_blocked_due_to_duplicate_and_missing_market_probability>
    <Module test_recommendation_explainer.py>
      <Function test_empty>
      <Function test_deterministic>
      <Function test_factor>
      <Function test_gap>
      <Function test_bounds>
      <Function test_risk>
    <Module test_roster_reconciliation.py>
      <Function test_matching_rosters_are_allowed>
      <Function test_local_only_player_is_divergent>
      <Function test_sleeper_only_player_is_divergent>
      <Function test_unmapped_sleeper_id_fails_closed>
      <Function test_missing_authoritative_roster_fails_closed>
      <Function test_missing_snapshot_timestamp_fails_closed>
      <Function test_duplicate_local_player_fails_closed>
      <Function test_invalid_local_row_fails_closed>
      <Function test_common_suffixes_and_punctuation_normalize>
    <Module test_security_and_validation.py>
      <Function test_admin_routes_require_auth>
      <Function test_valid_session_csrf_allows_admin_form_submit>
      <Function test_invalid_csrf_is_rejected_for_form_posts>
      <Function test_duplicate_games_are_rejected>
      <Function test_invalid_probability_is_rejected>
      <Function test_percentages_must_total_approximately_100_percent>
    <Module test_survival_calibration.py>
      <Function test_thresholds>
      <Function test_confidence>
      <Function test_missing>
      <Function test_compare>
      <Function test_canonical>
    <Module test_survivor_intelligence.py>
      <Function test_used_teams_are_excluded>
      <Function test_used_teams_are_excluded_for_multiple_candidates>
      <Function test_primary_is_not_repeated_in_fallbacks>
      <Function test_fallbacks_are_unique_and_capped_at_two>
      <Function test_identical_inputs_remain_deterministic>
      <Function test_equal_scores_keep_a_deterministic_input_order>
      <Function test_current_probability_is_clamped_to_0_to_1>
      <Function test_future_value_is_normalized_to_0_to_1>
      <Function test_future_preservation_reduces_willingness_for_higher_future_value>
      <Function test_empty_candidate_input_is_handled_safely>
      <Function test_all_used_candidates_are_handled_safely>
      <Function test_missing_current_runtime_field_is_not_fabricated>
      <Function test_strategy_names_resolve_to_current_implemented_weights[protect-lead-expected_weights0-0.8]>
      <Function test_strategy_names_resolve_to_current_implemented_weights[balanced-expected_weights1-0.8]>
      <Function test_strategy_names_resolve_to_current_implemented_weights[gain-ground-expected_weights2-0.8]>
      <Function test_documented_60_20_10_10_target_is_not_available_in_active_runtime>
      <Function test_unknown_strategy_uses_balanced_behavior>
    <Module test_trade_intelligence.py>
      <Function test_value_is_deterministic_and_injury_reduces_value>
      <Function test_one_for_one_packages_are_unique_and_balanced_ordered>
      <Function test_two_for_one_never_reuses_same_player>
      <Function test_missing_roster_and_evidence_fail_closed>
      <Function test_inputs_are_not_modified>
    <Module test_trade_intelligence_template.py>
      <Function test_trade_template_renders_and_has_no_submission_endpoint>
    <Module test_ux1_dashboard_sleeper_source.py>
      <Function test_verified_sleeper_metadata>
      <Function test_half_ppr_and_display_name_fallback>
      <Function test_missing_owner_fails_closed>
      <Function test_missing_source_fails_closed>
    <Module test_ux_1_7_completion.py>
      <Function test_dashboard_truth>
      <Function test_page_fail_closed>
      <Function test_lineup_reason>
      <Function test_waiver_owned_filter>
      <Function test_gm_source>
      <Function test_lineage_unknown>
      <Function test_panels>
    <Module test_ux_1_7_final_completion.py>
      <Function test_freshness_fails_closed_without_timestamp>
      <Function test_roster_requirements_include_k_and_def>
      <Function test_dst_is_normalized_to_def>
      <Function test_waiver_contract_filters_owned_and_blocks_unverified_eligibility>
      <Function test_payload_contract>
      <Function test_lineage_audit_reports_fallback_and_transformation>
      <Function test_no_competing_lineage_assignments>
      <Function test_all_active_ux_pages_have_panel>
    <Module test_ux_1_7_large_batch.py>
      <Function test_dashboard_state_is_source_backed>
      <Function test_dashboard_fixed_date_removed>
      <Function test_lineage_unknowns_are_explicit>
      <Function test_owned_waiver_is_removed>
      <Function test_completion_panels_present>
    <Module test_ux_evidence.py>
      <Function test_dashboard_fails_closed>
      <Function test_dashboard_uses_row>
      <Function test_owned_waiver_removed>
      <Function test_lineage_unknown>
      <Function test_state_normalized>
    <Module test_verify_f3_b31_postgres_parity.py>
      <Function test_pytest_counts_distinguish_skips_and_failures>
      <Function test_verifier_blocks_without_isolated_configuration>
      <Function test_verifier_accepts_only_configured_no_skip_full_gate>
    <Module test_weekly_lineup_intelligence.py>
      <Function test_slots_flex_total_and_bench>
      <Function test_bye_and_out_are_benched>
      <Function test_empty_and_incomplete_fail_closed>
      <Function test_missing_evidence_reported_and_inputs_preserved>
    <Module test_weekly_lineup_template.py>
      <Function test_template_renders_decisions_and_has_no_form>
    <Module test_yahoo_pickem.py>
      <UnitTestCase PickemEngineTests>
        <TestCaseFunction test_bad_yahoo_total_rejected>
        <TestCaseFunction test_confidence_points_are_unique>
        <TestCaseFunction test_duplicate_rejected>
        <TestCaseFunction test_position_cap>
        <TestCaseFunction test_probability_is_bounded>
      <Function test_current_contract_four_way_side_alignment[PHI-PHI-0.4-0.6-0.6-0.6-0.0-False]>
      <Function test_current_contract_four_way_side_alignment[PHI-DAL-0.6-0.4-0.4-0.6-0.19999999999999996-False]>
      <Function test_current_contract_four_way_side_alignment[DAL-PHI-0.3-0.7-0.3-0.7-0.3-True]>
      <Function test_current_contract_four_way_side_alignment[DAL-DAL-0.7-0.3-0.7-0.7--0.09999999999999998-False]>
      <Function test_contrarian_edge_uses_yahoo_pct_for_model_selected_team>
      <Function test_current_contract_confidence_band_boundaries[0.599999-0.65-0.65-0.4-False-COIN FLIP]>
      <Function test_current_contract_confidence_band_boundaries[0.6-0.65-0.65-0.4-False-LEAN PICK]>
      <Function test_current_contract_confidence_band_boundaries[0.719999-0.65-0.65-0.4-False-LEAN PICK]>
      <Function test_current_contract_confidence_band_boundaries[0.72-0.65-0.65-0.4-False-STRONG PICK]>
      <Function test_current_contract_confidence_band_boundaries[0.72-0.65-0.65-0.4-True-STRONG VALUE]>
      <Function test_current_contract_confidence_band_boundaries[0.85-0.65-0.65-0.4-False-ELITE PICK]>
      <Function test_current_contract_identical_inputs_are_deterministic>
      <Function test_current_contract_boundary_values_are_covered[0.35]>
      <Function test_current_contract_boundary_values_are_covered[0.5]>
      <Function test_current_contract_boundary_values_are_covered[0.6]>
      <Function test_current_contract_boundary_values_are_covered[0.7]>
      <Function test_current_contract_boundary_values_are_covered[0.72]>
      <Function test_current_contract_boundary_values_are_covered[0.85]>
      <Function test_current_contract_terms_are_named_and_distinct[model_selected_probability-0.6]>
      <Function test_current_contract_terms_are_named_and_distinct[selected_team_crowd_pct-0.3]>
      <Function test_current_contract_terms_are_named_and_distinct[crowd_pick_pct-0.7]>
      <Function test_current_contract_terms_are_named_and_distinct[model_probability_for_crowd_side-0.4]>
      <Function test_proposed_design_public_trap_requires_disagreement>

========================= 441 tests collected in 4.73s =========================

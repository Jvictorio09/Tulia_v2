from __future__ import annotations

from typing import Dict

from .contracts import TemplateContract, TemplateRegistry


def build_default_registry() -> TemplateRegistry:
    registry = TemplateRegistry()
    registry.register_many(
        [
            TemplateContract(
                template_id="ScenarioTaggerCard",
                required_props={"scenario_text", "options", "answer_key"},
                optional_props={"reflection_prompt", "copy"},
                scoring_mode="tiered_accuracy",
            ),
            TemplateContract(
                template_id="PersonalScenarioCapture",
                required_props={"examples", "rating_scale"},
                optional_props={"helper_text", "character_limit"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="TernaryRatingCard",
                required_props={"scenario_ref", "explainers"},
                optional_props={"stakes_defaults", "reflection_prompt"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="SingleSelectActionCard",
                required_props={"scenario_ref", "actions"},
                optional_props={"allow_other", "reflection_prompt"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="MantraSelectOrWrite",
                required_props={"mantras", "character_limit"},
                optional_props={"coach_tip"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="GuidedBreathDrill",
                required_props={"script", "timings"},
                optional_props={"baseline_prompt", "reflection_prompt"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="BinaryClassifierCard",
                required_props={"examples"},
                optional_props={"explainers", "reflection_prompt"},
                scoring_mode="correctness",
            ),
            TemplateContract(
                template_id="PickThreeKeyPoints",
                required_props={"source_paragraph", "options", "correct_ids"},
                optional_props={"free_text_enabled"},
                scoring_mode="tiered_accuracy",
            ),
            TemplateContract(
                template_id="LeverSelector3P",
                required_props={"scenario_ref", "lever_cards"},
                optional_props={"reflection_prompt"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="PresenceRitualQuickStart",
                required_props={"script", "duration_s"},
                optional_props={"intention_prompt"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="StakesMapBuilder",
                required_props={
                    "scenario_ref",
                    "pressure_options",
                    "trigger_examples",
                    "lever_cards",
                    "action_hints",
                },
                optional_props={"prefill"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="ReflectionRatingCard",
                required_props={"scenario_ref", "lever", "feedback_rules"},
                optional_props={"reflection_prompt"},
                scoring_mode="completion",
            ),
            TemplateContract(
                template_id="CoachSheetTip",
                required_props={"title", "body"},
                optional_props={"details", "severity"},
                scoring_mode="informational",
            ),
        ]
    )
    return registry


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from .contracts import TemplateRegistry, ValidationError
from .seeds import FlowConfig, SeedPack


@dataclass
class LessonContext:
    module_code: str
    user_state: Mapping[str, Any]
    session_context: MutableMapping[str, Any]
    cards: List[Dict[str, Any]] = field(default_factory=list)
    analytics: List[Dict[str, Any]] = field(default_factory=list)

    def register_signal(self, name: str, value: Any) -> None:
        self.session_context.setdefault("recent_signals", {})[name] = value


class LessonEngine:
    """Deterministic but adaptable sequencing for lesson runner cards."""

    def __init__(
        self,
        registry: TemplateRegistry,
        seed_packs: Mapping[str, SeedPack],
        flow: FlowConfig,
    ) -> None:
        self.registry = registry
        self.seed_packs = seed_packs
        self.flow = flow

    def build_session_stack(self, context: LessonContext) -> List[Dict[str, Any]]:
        base_sequence = self._expand_sequence(self.flow.sequence, context)
        stack = []

        for index, card_config in enumerate(base_sequence):
            # Guard evaluation may inject cards before the current card
            injections = self._evaluate_guards(card_config, context)
            for injected in injections:
                if self._append_card(injected, context):
                    stack.append(injected)

            if self._append_card(card_config, context):
                stack.append(card_config)

        context.cards = stack
        return stack

    # --- Internals -----------------------------------------------------

    def _expand_sequence(
        self, sequence: Sequence[Mapping[str, Any]], context: LessonContext
    ) -> List[Dict[str, Any]]:
        expanded: List[Dict[str, Any]] = []
        for descriptor in sequence:
            repeats = int(descriptor.get("repeat", 1))
            for iteration in range(repeats):
                card = dict(descriptor)
                card.setdefault("iteration", iteration)
                card.setdefault("card_key", f"{card.get('exercise_id')}::{iteration}")
                self._apply_variants(card, context, iteration)
                self._assign_seed(card, context, iteration)
                expanded.append(card)
        return expanded

    def _apply_variants(
        self, card: MutableMapping[str, Any], context: LessonContext, iteration: int
    ) -> None:
        variants = card.get("variants")
        if not variants:
            return
        variant_key = self._select_variant(card, context, iteration)
        if variant_key and variant_key in variants:
            card.update(variants[variant_key])
            card["variant"] = variant_key
        else:
            card["variant"] = "default"

    def _assign_seed(
        self, card: MutableMapping[str, Any], context: LessonContext, iteration: int
    ) -> None:
        seed_path = card.get("seed_sequence")
        if not seed_path:
            return
        seed_pack = self.seed_packs.get(seed_path)
        if not seed_pack or not seed_pack.payload:
            return
        cursor = context.session_context.setdefault("_seed_cursor", {})
        key = card.get("exercise_id") or seed_path
        index = cursor.get(key, 0)
        seed_item = seed_pack.payload[index % len(seed_pack.payload)]
        cursor[key] = (index + 1) % len(seed_pack.payload)
        card["seed_key"] = f"{seed_path}:{seed_item.get('id')}"
        card["seed_item"] = seed_item

    def _select_variant(
        self, card: Mapping[str, Any], context: LessonContext, iteration: int
    ) -> Optional[str]:
        # Simple A/B variant selection: prefer user assigned variant, fallback to card default
        user_variant = context.user_state.get("ab_variant")
        if user_variant:
            return str(user_variant)
        return card.get("default_variant")

    def _evaluate_guards(
        self, card: Mapping[str, Any], context: LessonContext
    ) -> List[Dict[str, Any]]:
        injections: List[Dict[str, Any]] = []
        for guard in self.flow.guards:
            target = guard.get("target")
            if target and target != card.get("template_id"):
                continue
            if not self._guard_allows(guard, context):
                continue
            for injection in guard.get("inserts", []):
                cooldown_key = guard.get("cooldown_key") or guard.get("id")
                if cooldown_key:
                    context.session_context.setdefault("cooldowns", {})[cooldown_key] = True
                enriched = dict(injection)
                enriched.setdefault("injected_by", guard.get("id"))
                injections.append(enriched)
        return injections

    def _guard_allows(self, guard: Mapping[str, Any], context: LessonContext) -> bool:
        cooldown_key = guard.get("cooldown_key") or guard.get("id")
        if cooldown_key and context.session_context.get("cooldowns", {}).get(cooldown_key):
            return False
        conditions = guard.get("conditions") or []
        for condition in conditions:
            if not self._evaluate_condition(condition, context):
                return False
        return True

    def _evaluate_condition(self, condition: Mapping[str, Any], context: LessonContext) -> bool:
        ctype = condition.get("type")
        if ctype == "metric_gte":
            metric = condition.get("metric")
            threshold = condition.get("value")
            value = context.session_context.get(metric)
            if value is None:
                return False
            try:
                return float(value) >= float(threshold)
            except (TypeError, ValueError):
                return False
        if ctype == "signal_equals":
            signal = condition.get("signal")
            expected = condition.get("value")
            signals = context.session_context.get("recent_signals", {})
            return signals.get(signal) == expected
        if ctype == "missing_context":
            key = condition.get("key")
            return not context.session_context.get(key)
        return False

    def _append_card(self, card: MutableMapping[str, Any], context: LessonContext) -> bool:
        template_id = card.get("template_id")
        if not template_id:
            return False
        completed = context.session_context.get("completed_cards") or []
        if card.get("card_key") and card.get("card_key") in completed:
            return False
        if card.get("needs_scenario_ref") and not context.session_context.get("current_scenario_ref"):
            return False
        props = self._resolve_props(card, context)
        ok, errors = self.registry.validate(template_id, props)
        if ok:
            card["props"] = props
            return True
        # Validation failed: fall back to coach sheet tip card
        fallback = self._build_fallback_card(template_id, errors)
        context.cards.append(fallback)
        return False

    def _resolve_props(
        self, card: MutableMapping[str, Any], context: LessonContext
    ) -> Dict[str, Any]:
        props = dict(card.get("props") or {})
        # Carry-over rules
        if card.get("needs_scenario_ref"):
            scenario_ref = context.session_context.get("current_scenario_ref")
            if not scenario_ref:
                raise ValidationError(
                    f"{card.get('template_id')} requires current_scenario_ref but none is set"
                )
            props.setdefault("scenario_ref", scenario_ref)
        # Apply seed lookups
        if "seed_key" in card:
            pack_name, seed_id = card["seed_key"].split(":", 1)
            seed_pack = self.seed_packs.get(pack_name)
            if not seed_pack:
                raise ValidationError(f"Missing seed pack '{pack_name}'")
            matching = next((item for item in seed_pack.payload if str(item.get("id")) == seed_id), None)
            if not matching:
                raise ValidationError(f"Seed '{seed_id}' not found in pack '{pack_name}'")
            props = {**matching, **props}
        template_id = card.get("template_id")
        if template_id == "ScenarioTaggerCard":
            seed = card.get("seed_item") or {}
            props.setdefault("scenario_text", seed.get("text", ""))
            props.setdefault(
                "options",
                [
                    {"id": "pressure", "label": "Pressure"},
                    {"id": "visibility", "label": "Visibility"},
                    {"id": "irreversibility", "label": "Irreversibility"},
                ],
            )
            props.setdefault("answer_key", seed.get("answer_key", {}))
        elif template_id == "SingleSelectActionCard":
            actions_pack = self.seed_packs.get("moduleA/actions_control_shift.json")
            if actions_pack:
                props.setdefault("actions", actions_pack.payload)
        elif template_id == "MantraSelectOrWrite":
            mantra_pack = self.seed_packs.get("moduleA/reframe_mantras.json")
            if mantra_pack:
                props.setdefault("mantras", mantra_pack.payload)
        elif template_id == "BinaryClassifierCard":
            load_pack = self.seed_packs.get("moduleA/load_examples.json")
            if load_pack:
                props.setdefault("examples", load_pack.payload)
        elif template_id == "PickThreeKeyPoints":
            d2_pack = self.seed_packs.get("moduleA/d2_keypoint_sets.json")
            if d2_pack:
                seed = d2_pack.payload[0]
                props.setdefault("source_paragraph", seed.get("source", ""))
                props.setdefault("options", seed.get("options", []))
                props.setdefault("correct_ids", seed.get("correct_ids", []))
        elif template_id == "LeverSelector3P":
            lever_pack = self.seed_packs.get("moduleA/lever_cards.json")
            if lever_pack:
                props.setdefault("lever_cards", lever_pack.payload)
            last_lever = context.session_context.get("last_lever_choice")
            if last_lever:
                props.setdefault("last_choice", last_lever)
        elif template_id == "StakesMapBuilder":
            map_pack = self.seed_packs.get("moduleA/stakes_map_presets.json")
            if map_pack and map_pack.payload:
                preset = map_pack.payload[0]
                props.setdefault("pressure_options", preset.get("pressure_options", []))
                props.setdefault("trigger_examples", preset.get("trigger_examples", []))
                props.setdefault("action_hints", preset.get("action_hints", []))
                lever_pack = self.seed_packs.get("moduleA/lever_cards.json")
                if lever_pack:
                    props.setdefault("lever_cards", lever_pack.payload)
        elif template_id == "TernaryRatingCard":
            scenario_ref = props.get("scenario_ref")
            if scenario_ref:
                default_pack = self.seed_packs.get("moduleA/pic_sets.json")
                if default_pack:
                    defaults = next(
                        (
                            item.get("recommended_default")
                            for item in default_pack.payload
                            if item.get("scenario_id") == scenario_ref
                        ),
                        None,
                    )
                    if defaults:
                        props.setdefault("stakes_defaults", defaults)
        elif template_id == "ReflectionRatingCard":
            props.setdefault("lever", context.session_context.get("last_lever_choice"))
        return props

    def _build_fallback_card(self, template_id: str, errors: Sequence[str]) -> Dict[str, Any]:
        return {
            "template_id": "CoachSheetTip",
            "props": {
                "title": "Let’s pause for a quick tip",
                "body": (
                    "We hit a snag loading the next activity "
                    f"({template_id}). Our coach tip keeps you moving."
                ),
                "details": list(errors),
            },
            "meta": {
                "severity": "info",
            },
        }


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


class ValidationError(Exception):
    """Raised when a template payload fails validation."""


ValidationCallable = Callable[[Mapping[str, Any]], Optional[str]]


@dataclass(frozen=True)
class TemplateContract:
    template_id: str
    required_props: Set[str] = field(default_factory=set)
    optional_props: Set[str] = field(default_factory=set)
    validations: Sequence[ValidationCallable] = field(default_factory=tuple)
    scoring_mode: str = "completion"

    def validate(self, props: Mapping[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        missing = self.required_props.difference(props.keys())
        if missing:
            errors.append(
                f"{self.template_id} missing required props: {', '.join(sorted(missing))}"
            )

        allowed = self.required_props.union(self.optional_props)
        extras = set(props.keys()).difference(allowed)
        if extras:
            errors.append(
                f"{self.template_id} received unexpected props: {', '.join(sorted(extras))}"
            )

        for validate in self.validations:
            try:
                message = validate(props)
            except Exception as exc:
                errors.append(f"{self.template_id} validator error: {exc}")
            else:
                if message:
                    errors.append(message)

        return (len(errors) == 0, errors)


class TemplateRegistry:
    """Registry holding template contracts for lesson cards."""

    def __init__(self) -> None:
        self._contracts: Dict[str, TemplateContract] = {}

    def register(self, contract: TemplateContract) -> None:
        if contract.template_id in self._contracts:
            raise ValueError(f"Contract already registered for {contract.template_id}")
        self._contracts[contract.template_id] = contract

    def register_many(self, contracts: Iterable[TemplateContract]) -> None:
        for contract in contracts:
            self.register(contract)

    def get(self, template_id: str) -> TemplateContract:
        if template_id not in self._contracts:
            raise KeyError(f"No contract found for template '{template_id}'")
        return self._contracts[template_id]

    def validate(self, template_id: str, props: Mapping[str, Any]) -> Tuple[bool, List[str]]:
        contract = self.get(template_id)
        return contract.validate(props)

    def ensure(self, template_id: str, props: Mapping[str, Any]) -> None:
        ok, errors = self.validate(template_id, props)
        if not ok:
            raise ValidationError("; ".join(errors))


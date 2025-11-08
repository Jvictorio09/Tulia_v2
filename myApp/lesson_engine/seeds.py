from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from django.conf import settings


class SeedVersionError(Exception):
    """Raised when a seed pack or flow file is invalid or stale."""


def _parse_iso8601(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SeedVersionError(f"Invalid ISO8601 date: {value}") from exc


@dataclass(frozen=True)
class SeedPack:
    name: str
    version: str
    module_code: str
    deprecated_after: Optional[datetime]
    payload: List[Dict[str, Any]]

    def ensure_active(self, reference: Optional[datetime] = None) -> None:
        if not self.deprecated_after:
            return
        reference = reference or datetime.now(timezone.utc)
        target = (
            self.deprecated_after
            if self.deprecated_after.tzinfo
            else self.deprecated_after.replace(tzinfo=timezone.utc)
        )
        if reference > target:
            raise SeedVersionError(
                f"Seed pack '{self.name}' version {self.version} expired on {target.isoformat()}"
            )


@dataclass(frozen=True)
class FlowConfig:
    name: str
    version: str
    module_code: str
    deprecated_after: Optional[datetime]
    sequence: List[Dict[str, Any]]
    guards: List[Dict[str, Any]]
    scoring: Dict[str, Any]

    def ensure_active(self, reference: Optional[datetime] = None) -> None:
        if not self.deprecated_after:
            return
        reference = reference or datetime.now(timezone.utc)
        target = (
            self.deprecated_after
            if self.deprecated_after.tzinfo
            else self.deprecated_after.replace(tzinfo=timezone.utc)
        )
        if reference > target:
            raise SeedVersionError(
                f"Flow '{self.name}' version {self.version} expired on {target.isoformat()}"
            )


class SeedLoader:
    """Loads versioned seed packs and flow configs for modules."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = base_path or (Path(settings.BASE_DIR) / "myApp" / "content")

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise SeedVersionError(f"Seed file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError as exc:
                raise SeedVersionError(f"Invalid JSON in {path}: {exc}") from exc

    def _build_pack(self, name: str, data: Mapping[str, Any]) -> SeedPack:
        version = str(data.get("version") or "")
        if not version:
            raise SeedVersionError(f"Seed pack '{name}' missing version")
        module_code = str(data.get("module_code") or "")
        if not module_code:
            raise SeedVersionError(f"Seed pack '{name}' missing module_code")
        deprecated_raw = data.get("deprecated_after")
        deprecated_after = _parse_iso8601(deprecated_raw) if deprecated_raw else None
        payload = data.get("items") or data.get("payload") or []
        if not isinstance(payload, list):
            raise SeedVersionError(f"Seed pack '{name}' payload must be a list")
        return SeedPack(
            name=name,
            version=version,
            module_code=module_code,
            deprecated_after=deprecated_after,
            payload=payload,
        )

    def _build_flow(self, name: str, data: Mapping[str, Any]) -> FlowConfig:
        version = str(data.get("version") or "")
        if not version:
            raise SeedVersionError(f"Flow '{name}' missing version")
        module_code = str(data.get("module_code") or "")
        if not module_code:
            raise SeedVersionError(f"Flow '{name}' missing module_code")
        deprecated_raw = data.get("deprecated_after")
        deprecated_after = _parse_iso8601(deprecated_raw) if deprecated_raw else None
        sequence = data.get("sequence") or []
        if not isinstance(sequence, list):
            raise SeedVersionError(f"Flow '{name}' sequence must be a list")
        guards = data.get("guards") or []
        if not isinstance(guards, list):
            raise SeedVersionError(f"Flow '{name}' guards must be a list")
        scoring = data.get("scoring") or {}
        if not isinstance(scoring, dict):
            raise SeedVersionError(f"Flow '{name}' scoring must be an object")
        return FlowConfig(
            name=name,
            version=version,
            module_code=module_code,
            deprecated_after=deprecated_after,
            sequence=sequence,
            guards=guards,
            scoring=scoring,
        )

    def load_pack(self, path: str) -> SeedPack:
        seed_path = self.base_path / path
        data = self._load_json(seed_path)
        pack = self._build_pack(path, data)
        pack.ensure_active()
        return pack

    def load_flow(self, path: str) -> FlowConfig:
        flow_path = self.base_path / path
        data = self._load_json(flow_path)
        flow = self._build_flow(path, data)
        flow.ensure_active()
        return flow

    def load_many(self, paths: Iterable[str]) -> Dict[str, SeedPack]:
        packs: Dict[str, SeedPack] = {}
        for path in paths:
            pack = self.load_pack(path)
            packs[path] = pack
        return packs

    def resolve_module_seeds(
        self,
        module_code: str,
        pack_paths: Iterable[str],
        flow_path: str,
    ) -> Tuple[Dict[str, SeedPack], FlowConfig]:
        packs = self.load_many(pack_paths)
        flow = self.load_flow(flow_path)
        for pack in packs.values():
            if pack.module_code != module_code:
                raise SeedVersionError(
                    f"Seed pack '{pack.name}' module mismatch (expected {module_code}, got {pack.module_code})"
                )
        if flow.module_code != module_code:
            raise SeedVersionError(
                f"Flow '{flow.name}' module mismatch (expected {module_code}, got {flow.module_code})"
            )
        return packs, flow


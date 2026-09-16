"""
Integration Layer: Registry of State & SRO Adapters.
"""
from typing import Dict, List
from app.services.integration.base_adapter import BaseStateAdapter
from app.services.integration.tamilnadu import TamilNaduNilamAdapter
from app.services.integration.maharashtra import MaharashtraMahaBhulekhAdapter
from app.services.integration.karnataka import KarnatakaBhoomiAdapter
from app.services.integration.canonical import CanonicalLandParcel

ADAPTER_REGISTRY: Dict[str, BaseStateAdapter] = {
    "TN": TamilNaduNilamAdapter(),
    "MH": MaharashtraMahaBhulekhAdapter(),
    "KA": KarnatakaBhoomiAdapter(),
}


def get_adapter(state_code: str) -> BaseStateAdapter:
    code = state_code.upper()
    if code not in ADAPTER_REGISTRY:
        raise ValueError(f"State adapter for '{state_code}' is not implemented. Supported: {list(ADAPTER_REGISTRY.keys())}")
    return ADAPTER_REGISTRY[code]


def list_supported_states() -> List[Dict[str, str]]:
    return [
        {"state_code": k, "state_name": v.state_name}
        for k, v in ADAPTER_REGISTRY.items()
    ]


__all__ = [
    "ADAPTER_REGISTRY",
    "get_adapter",
    "list_supported_states",
    "BaseStateAdapter",
    "CanonicalLandParcel"
]

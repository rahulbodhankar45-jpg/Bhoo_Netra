"""
Abstract Base State Adapter for Land Stack Integration Layer.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.services.integration.canonical import CanonicalLandParcel


class BaseStateAdapter(ABC):
    """Abstract interface defining the contract for State & SRO system adapters."""

    @property
    @abstractmethod
    def state_code(self) -> str:
        """Unique two-letter state code, e.g., 'TN', 'MH', 'KA'."""
        pass

    @property
    @abstractmethod
    def state_name(self) -> str:
        """State display name, e.g., 'Tamil Nadu'."""
        pass

    @abstractmethod
    def transform_to_canonical(self, raw_state_payload: Dict[str, Any]) -> CanonicalLandParcel:
        """Transforms native state API payload into the standardized CanonicalLandParcel."""
        pass

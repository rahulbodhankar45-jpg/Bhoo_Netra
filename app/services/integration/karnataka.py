"""
Karnataka Adapter: Translates Bhoomi RTC (Record of Rights, Tenancy and Crops) & Kaveri Registration.
"""
from typing import Dict, Any
from app.services.integration.base_adapter import BaseStateAdapter
from app.services.integration.canonical import (
    CanonicalLandParcel,
    CanonicalRoR,
    CanonicalOwner,
    CanonicalRegistration,
    CanonicalLandUse
)


class KarnatakaBhoomiAdapter(BaseStateAdapter):
    @property
    def state_code(self) -> str:
        return "KA"

    @property
    def state_name(self) -> str:
        return "Karnataka"

    def transform_to_canonical(self, raw_state_payload: Dict[str, Any]) -> CanonicalLandParcel:
        ulpin = raw_state_payload.get("ulpin") or f"IN-KA-{raw_state_payload.get('district_code', 'BLR')}-{raw_state_payload.get('hissa_no', '45')}"
        area_sqm = float(raw_state_payload.get("extent_sqm", raw_state_payload.get("area", 1850.0)))

        owners = [
            CanonicalOwner(
                owner_id="KA-OWN-01",
                name=raw_state_payload.get("khatadar_name", "Suresh Gowda"),
                share_percentage=100.0
            )
        ]

        ror = CanonicalRoR(
            ror_number=f"RTC-{raw_state_payload.get('rtc_number', 'KA-BHOOMI-778')}",
            status="ACTIVE",
            tenure="Freehold",
            rights=["KHATA_RIGHTS", "ALIENATION_PERMITTED"],
            restrictions=raw_state_payload.get("ptcl_restrictions", "NONE"),
            owners=owners
        )

        reg = CanonicalRegistration(
            registration_number=raw_state_payload.get("kaveri_reg_no"),
            sro_code=raw_state_payload.get("sro_office", "SRO-Kengeri"),
            deed_type="Absolute Sale Deed",
            encumbrance_status="NONE"
        )

        land_use = CanonicalLandUse(
            zone=raw_state_payload.get("bda_zone", "Commercial"),
            permitted_use="Commercial Complex",
            fsi_allowed=2.5
        )

        return CanonicalLandParcel(
            ulpin=ulpin,
            survey_number=raw_state_payload.get("survey_no", "56/2"),
            state="Karnataka",
            district=raw_state_payload.get("district", "Bengaluru Urban"),
            taluk=raw_state_payload.get("taluk", "Bengaluru South"),
            village=raw_state_payload.get("village", "Kengeri"),
            area_sqm=area_sqm,
            land_type="Commercial",
            geometry=raw_state_payload.get("bhoomi_geometry", {
                "type": "Polygon",
                "coordinates": [[[77.4800, 12.9100], [77.4815, 12.9100], [77.4815, 12.9115], [77.4800, 12.9115], [77.4800, 12.9100]]]
            }),
            ror=ror,
            registration=reg,
            land_use=land_use,
            source_system="KA_BHOOMI_KAVERI_GATEWAY"
        )

"""
Tamil Nadu Adapter: Translates TN Nilam (Land Records) & TN-REGINSP (Registration) schemas.
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


class TamilNaduNilamAdapter(BaseStateAdapter):
    @property
    def state_code(self) -> str:
        return "TN"

    @property
    def state_name(self) -> str:
        return "Tamil Nadu"

    def transform_to_canonical(self, raw_state_payload: Dict[str, Any]) -> CanonicalLandParcel:
        """
        Transforms raw TN Nilam / Patta Chitta payload into CanonicalLandParcel.
        Example raw fields: patta_number, survey_subdiv, gramam, vattam, mavattam, visthiranam (hectares), poruppu.
        """
        ulpin = raw_state_payload.get("ulpin") or f"IN-TN-{raw_state_payload.get('mavattam_code', 'CHN')}-{raw_state_payload.get('patta_number', '1001')}"
        
        # Area conversion: TN Nilam often stores in Hectares/Ares. Convert to sq.m if unit is hectare
        area_raw = float(raw_state_payload.get("visthiranam_sqm", raw_state_payload.get("area", 1200.0)))

        owners = []
        raw_owners = raw_state_payload.get("pattadhar_names", ["K. Ramanathan"])
        for idx, name in enumerate(raw_owners):
            owners.append(CanonicalOwner(
                owner_id=f"TN-OWN-{idx+1}",
                name=name,
                share_percentage=100.0 / len(raw_owners)
            ))

        ror = CanonicalRoR(
            ror_number=f"PATTA-{raw_state_payload.get('patta_number', '882')}",
            status="ACTIVE",
            tenure="Ryotwari",
            rights=["RYOTWARI_PATTADAR", "CULTIVATION_TRANSFER"],
            restrictions=raw_state_payload.get("natham_restrictions", "NONE"),
            owners=owners
        )

        reg = CanonicalRegistration(
            registration_number=raw_state_payload.get("reg_doc_no"),
            sro_code=raw_state_payload.get("sro_name", "SRO-Guindy"),
            deed_type="Sale Deed",
            encumbrance_status=raw_state_payload.get("villangam_status", "NONE")
        )

        land_use = CanonicalLandUse(
            zone=raw_state_payload.get("nanjai_punjai_type", "Residential"),
            permitted_use="Residential development",
            fsi_allowed=2.0
        )

        return CanonicalLandParcel(
            ulpin=ulpin,
            survey_number=raw_state_payload.get("survey_subdiv", "123/4A"),
            state="Tamil Nadu",
            district=raw_state_payload.get("mavattam", "Chennai"),
            taluk=raw_state_payload.get("vattam", "Guindy"),
            village=raw_state_payload.get("gramam", "Velachery"),
            area_sqm=area_raw,
            land_type="Residential",
            geometry=raw_state_payload.get("fmb_geometry", {
                "type": "Polygon",
                "coordinates": [[[80.2201, 12.9801], [80.2215, 12.9801], [80.2215, 12.9815], [80.2201, 12.9815], [80.2201, 12.9801]]]
            }),
            ror=ror,
            registration=reg,
            land_use=land_use,
            source_system="TN_NILAM_REGINSP_GATEWAY"
        )

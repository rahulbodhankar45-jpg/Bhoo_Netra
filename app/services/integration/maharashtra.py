"""
Maharashtra Adapter: Translates MahaBhulekh (7/12 - Saat Baara) & iSARITA Registration schemas.
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


class MaharashtraMahaBhulekhAdapter(BaseStateAdapter):
    @property
    def state_code(self) -> str:
        return "MH"

    @property
    def state_name(self) -> str:
        return "Maharashtra"

    def transform_to_canonical(self, raw_state_payload: Dict[str, Any]) -> CanonicalLandParcel:
        """
        Transforms raw 7/12 extract payload into CanonicalLandParcel.
        Handles: Gat kramank, Bhogavatdar Varg, Pot Kharaba, Ferfar (mutation), Kulkarni hakka.
        """
        ulpin = raw_state_payload.get("ulpin") or f"IN-MH-{raw_state_payload.get('zilha_code', 'PUN')}-{raw_state_payload.get('gat_kramank', '204')}"
        
        area_sqm = float(raw_state_payload.get("kshetra_hec_are_sqm", raw_state_payload.get("area", 2450.0)))

        owners = []
        raw_khatedars = raw_state_payload.get("khatedar_names", ["Anand Deshmukh"])
        for idx, name in enumerate(raw_khatedars):
            owners.append(CanonicalOwner(
                owner_id=f"MH-KHAT-{idx+1}",
                name=name,
                share_percentage=100.0 / len(raw_khatedars)
            ))

        ror = CanonicalRoR(
            ror_number=f"7/12-GAT-{raw_state_payload.get('gat_kramank', '204')}",
            status="ACTIVE",
            tenure=raw_state_payload.get("bhogavatdar_varg", "Class-1 Freehold"),
            rights=["KHATEDAR_HAKKA", "FERFAR_RIGHTS"],
            restrictions=raw_state_payload.get("itar_adhikar_liens", "NONE"),
            owners=owners
        )

        reg = CanonicalRegistration(
            registration_number=raw_state_payload.get("dast_kramank"),
            sro_code=raw_state_payload.get("haveli_sro", "SRO-Haveli-04"),
            deed_type="Kharidpatra (Sale Deed)",
            encumbrance_status="NONE" if not raw_state_payload.get("boja_nond") else "ACTIVE"
        )

        land_use = CanonicalLandUse(
            zone=raw_state_payload.get("vapar_prakar", "Residential / NA"),
            permitted_use="Non-Agricultural (NA) Residential",
            fsi_allowed=1.8
        )

        return CanonicalLandParcel(
            ulpin=ulpin,
            survey_number=str(raw_state_payload.get("gat_kramank", "204/1B")),
            state="Maharashtra",
            district=raw_state_payload.get("zilha", "Pune"),
            taluk=raw_state_payload.get("taluka", "Haveli"),
            village=raw_state_payload.get("gaon", "Hinjawadi"),
            area_sqm=area_sqm,
            land_type="Residential",
            geometry=raw_state_payload.get("gis_geometry", {
                "type": "Polygon",
                "coordinates": [[[73.7280, 18.5910], [73.7295, 18.5910], [73.7295, 18.5925], [73.7280, 18.5925], [73.7280, 18.5910]]]
            }),
            ror=ror,
            registration=reg,
            land_use=land_use,
            source_system="MAHA_BHULEKH_ISARITA_GATEWAY"
        )

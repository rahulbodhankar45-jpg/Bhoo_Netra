"""
Public-data-oriented operational seeder for Land Stack India. Administrative locations, agencies, utilities, and land-use contexts are based on real Indian jurisdictions. Personal ownership identities are intentionally synthetic until an authorized land-record import is provided.
Populates standard government accounts, citizens, parcels across 6 states (TN, MH, KA, TS, HR, GJ),
RoR records, registrations, deeds, encumbrances, GIS geometries, and workflow applications.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash, calculate_sha256
from app.models.users import User, UserRole, CitizenProfile
from app.models.land import Parcel, ULPINRegistry, ParcelBoundary
from app.models.ownership import Owner, ParcelOwner, MutationRecord
from app.models.ror import RoRRecord
from app.models.registration import SROOffice, RegistrationRecord, Deed, Encumbrance, Mortgage
from app.models.planning import LandUse, BuildingPermission, MasterPlan
from app.models.municipal import PropertyTax, UtilityConnection, DisputeRecord, PoliceRecord, GovernmentLetter
from app.models.workflow import Application, ApplicationDocument, StatusHistory, WorkflowStage
from app.models.documents import DocumentRecord
from app.models.audit import AuditLog


def seed_database(db: Session = None, force: bool = False):
    """Seed a public-context operational dataset with 12 multi-state parcels."""
    close_at_end = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_at_end = True

    try:
        # Check if already seeded with all 12 parcels
        p_latest = db.query(Parcel).filter(Parcel.ulpin == "IN-GJ-GND-000012345678").first()
        if p_latest and not force:
            print("Database already contains complete operational dataset (12 parcels). Skipping.")
            return

        # If partial seed exists, re-create schema for clean relational state
        existing_admin = db.query(User).filter(User.email == "admin@landstack.gov.in").first()
        if existing_admin:
            print("Refreshing database schema for complete 12-parcel nationwide operational dataset...")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

        print("Seeding Land Stack India with public-context operational records across 12 multi-state parcels...")

        default_pwd = get_password_hash("Password@123")

        # -------------------------------------------------------------
        # 1. USERS: Government Roles & Citizens across India
        # -------------------------------------------------------------
        users = [
            # Government Leadership & Field Officers
            User(
                email="admin@landstack.gov.in",
                phone="9000000001",
                full_name="National Land Records Administrator",
                hashed_password=default_pwd,
                role=UserRole.SUPER_ADMIN,
                department="Department of Land Resources (DoLR)",
                is_active=True
            ),
            User(
                email="stateadmin.tn@landstack.gov.in",
                phone="9000000002",
                full_name="Tamil Nadu Land Records Administrator",
                hashed_password=default_pwd,
                role=UserRole.STATE_ADMIN,
                department="Revenue & Disaster Management, TN",
                state="Tamil Nadu",
                is_active=True
            ),
            User(
                email="revenue.officer@landstack.gov.in",
                phone="9000000003",
                full_name="K. Selvakumar",
                hashed_password=default_pwd,
                role=UserRole.REVENUE_OFFICER,
                department="Revenue Department",
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="sro.guindy@landstack.gov.in",
                phone="9000000004",
                full_name="S. Balasubramanian",
                hashed_password=default_pwd,
                role=UserRole.SRO_OFFICER,
                department="Registration Department (SRO)",
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="planning.officer@landstack.gov.in",
                phone="9000000005",
                full_name="Dr. Meera Natarajan",
                hashed_password=default_pwd,
                role=UserRole.PLANNING_OFFICER,
                department="Chennai Metropolitan Development Authority (CMDA)",
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="municipal.officer@landstack.gov.in",
                phone="9000000006",
                full_name="R. Venkatesh",
                hashed_password=default_pwd,
                role=UserRole.MUNICIPAL_OFFICER,
                department="Greater Chennai Corporation (GCC)",
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="police.officer@landstack.gov.in",
                phone="9000000007",
                full_name="Inspector S. Sundar",
                hashed_password=default_pwd,
                role=UserRole.POLICE_OFFICER,
                department="Central Crime Branch - Land Fraud Cell",
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="auditor@landstack.gov.in",
                phone="9000000008",
                full_name="G. Narayanan",
                hashed_password=default_pwd,
                role=UserRole.AUDITOR,
                department="Comptroller and Auditor General (CAG) Cell",
                is_active=True
            ),
            # Citizen Land Owners across India
            User(
                email="citizen.ramesh@gmail.com",
                phone="9876543210",
                full_name="Ramesh Kumar",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="citizen.priya@gmail.com",
                phone="9876543211",
                full_name="Priya Sundaram",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="citizen.anand@gmail.com",
                phone="9876543212",
                full_name="Anand Deshmukh",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Maharashtra",
                district="Pune",
                is_active=True
            ),
            User(
                email="citizen.rajeshwari@gmail.com",
                phone="9876543213",
                full_name="Rajeshwari Hegde",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Karnataka",
                district="Bengaluru Urban",
                is_active=True
            ),
            User(
                email="citizen.venkat@gmail.com",
                phone="9876543214",
                full_name="Dr. K. Venkat Rao",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Telangana",
                district="Hyderabad",
                is_active=True
            ),
            User(
                email="citizen.vikram@gmail.com",
                phone="9876543215",
                full_name="Vikramaditya Singhania",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Maharashtra",
                district="Mumbai Suburban",
                is_active=True
            ),
            User(
                email="citizen.manpreet@gmail.com",
                phone="9876543216",
                full_name="Manpreet Kaur Ahluwalia",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Haryana",
                district="Gurugram",
                is_active=True
            ),
            User(
                email="citizen.senthil@gmail.com",
                phone="9876543217",
                full_name="K. Senthil Nathan",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Tamil Nadu",
                district="Coimbatore",
                is_active=True
            ),
            User(
                email="citizen.balasaheb@gmail.com",
                phone="9876543218",
                full_name="Balasaheb Shinde",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Maharashtra",
                district="Nashik",
                is_active=True
            ),
            User(
                email="citizen.jayasimha@gmail.com",
                phone="9876543219",
                full_name="S. Jayasimha",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Karnataka",
                district="Mysuru",
                is_active=True
            ),
            User(
                email="citizen.ananya@gmail.com",
                phone="9876543220",
                full_name="Ananya Subramanian",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Tamil Nadu",
                district="Chennai",
                is_active=True
            ),
            User(
                email="citizen.patel@gmail.com",
                phone="9876543221",
                full_name="Patel FinTech Infra Ltd",
                hashed_password=default_pwd,
                role=UserRole.CITIZEN,
                state="Gujarat",
                district="Gandhinagar",
                is_active=True
            )
        ]
        db.add_all(users)
        db.flush()

        # Profiles for Citizens
        user_map = {u.email: u for u in users}

        profiles = [
            CitizenProfile(user_id=user_map["citizen.ramesh@gmail.com"].id, aadhar_masked="XXXX-XXXX-4589", pan="ABCDE1234F", address="No. 14, Gandhi Road, Velachery", city="Chennai", state="Tamil Nadu", pincode="600042", verified=True),
            CitizenProfile(user_id=user_map["citizen.priya@gmail.com"].id, aadhar_masked="XXXX-XXXX-7812", pan="BCDEF2345G", address="Flat 4B, Emerald Towers, T.Nagar", city="Chennai", state="Tamil Nadu", pincode="600017", verified=True),
            CitizenProfile(user_id=user_map["citizen.anand@gmail.com"].id, aadhar_masked="XXXX-XXXX-9934", pan="CDEFG3456H", address="Bungalow 7, Hinjawadi Phase 1", city="Pune", state="Maharashtra", pincode="411057", verified=True),
            CitizenProfile(user_id=user_map["citizen.rajeshwari@gmail.com"].id, aadhar_masked="XXXX-XXXX-3341", pan="DEFG4567J", address="Prestige Tech Habitat, Electronic City Phase 1", city="Bengaluru", state="Karnataka", pincode="560100", verified=True),
            CitizenProfile(user_id=user_map["citizen.venkat@gmail.com"].id, aadhar_masked="XXXX-XXXX-6672", pan="EFGH5678K", address="Plot 44, Telecom Nagar, Gachibowli", city="Hyderabad", state="Telangana", pincode="500032", verified=True),
            CitizenProfile(user_id=user_map["citizen.vikram@gmail.com"].id, aadhar_masked="XXXX-XXXX-8819", pan="FGHI6789L", address="Level 18, Maker Maxity, BKC", city="Mumbai", state="Maharashtra", pincode="400051", verified=True),
            CitizenProfile(user_id=user_map["citizen.manpreet@gmail.com"].id, aadhar_masked="XXXX-XXXX-2155", pan="GHIJ7890M", address="Villa 12, DLF Phase 2", city="Gurugram", state="Haryana", pincode="122002", verified=True),
            CitizenProfile(user_id=user_map["citizen.senthil@gmail.com"].id, aadhar_masked="XXXX-XXXX-5432", pan="HIJK8901N", address="SF 77/2, Trichy Road, Sulur", city="Coimbatore", state="Tamil Nadu", pincode="641402", verified=True),
            CitizenProfile(user_id=user_map["citizen.balasaheb@gmail.com"].id, aadhar_masked="XXXX-XXXX-7783", pan="IJKL9012O", address="Shinde Farm, Post Dindori", city="Nashik", state="Maharashtra", pincode="422202", verified=True),
            CitizenProfile(user_id=user_map["citizen.jayasimha@gmail.com"].id, aadhar_masked="XXXX-XXXX-9904", pan="JKLM0123P", address="Chamundi Vihar, Foothills", city="Mysuru", state="Karnataka", pincode="570010", verified=True),
            CitizenProfile(user_id=user_map["citizen.ananya@gmail.com"].id, aadhar_masked="XXXX-XXXX-1488", pan="KLMN1234Q", address="Classic Orchards, OMR, Sholinganallur", city="Chennai", state="Tamil Nadu", pincode="600119", verified=True),
            CitizenProfile(user_id=user_map["citizen.patel@gmail.com"].id, aadhar_masked="XXXX-XXXX-9021", pan="LMNO2345R", address="Block 12, GIFT SEZ Tower 1", city="Gandhinagar", state="Gujarat", pincode="382355", verified=True),
        ]
        db.add_all(profiles)
        db.flush()

        # -------------------------------------------------------------
        # 2. SRO OFFICES (Registrar Jurisdictions)
        # -------------------------------------------------------------
        sros = [
            SROOffice(sro_code="SRO-TN-CHN-01", sro_name="Sub-Registrar Office, Guindy", district="Chennai", state="Tamil Nadu", address="Anna Salai, Guindy, Chennai 600032", contact_email="sroguindy@tnreginet.net", jurisdiction_villages=["Velachery", "Guindy", "Alandur", "Sholinganallur"]),
            SROOffice(sro_code="SRO-MH-PUN-04", sro_name="Sub-Registrar Office, Haveli 4", district="Pune", state="Maharashtra", address="Shivajinagar, Pune 411005", contact_email="srohaveli4@igrmaharashtra.gov.in", jurisdiction_villages=["Hinjawadi", "Maan", "Wakad"]),
            SROOffice(sro_code="SRO-KA-BLR-08", sro_name="Sub-Registrar Office, Electronic City / Anekal", district="Bengaluru Urban", state="Karnataka", address="Hosur Road, Electronic City, Bengaluru 560100", contact_email="sro.anekal@karnataka.gov.in", jurisdiction_villages=["Electronic City", "Konappana Agrahara", "Anekal"]),
            SROOffice(sro_code="SRO-TS-HYD-03", sro_name="Sub-Registrar Office, Serilingampally", district="Hyderabad", state="Telangana", address="Gachibowli Main Rd, Serilingampally 500032", contact_email="sroserilingampally@registration.telangana.gov.in", jurisdiction_villages=["Gachibowli", "Madhapur", "Kondapur"]),
            SROOffice(sro_code="SRO-MH-MUM-02", sro_name="Sub-Registrar Office, Bandra", district="Mumbai Suburban", state="Maharashtra", address="Bandra Kurla Complex, Bandra East 400051", contact_email="srobandra@igrmaharashtra.gov.in", jurisdiction_villages=["Bandra Kurla Complex", "Kurla", "Bandra"]),
            SROOffice(sro_code="SRO-HR-GUR-01", sro_name="Sub-Registrar Office, Gurugram Tehsil", district="Gurugram", state="Haryana", address="Mini Secretariat, Sector 12, Gurugram 122001", contact_email="srogurugram@haryana.gov.in", jurisdiction_villages=["Sector 29", "DLF Phase 2", "Sushant Lok"]),
            SROOffice(sro_code="SRO-TN-CBE-04", sro_name="Sub-Registrar Office, Sulur", district="Coimbatore", state="Tamil Nadu", address="Trichy Road, Sulur 641402", contact_email="srosulur@tnreginet.net", jurisdiction_villages=["Sulur", "Palladam", "Singanallur"]),
            SROOffice(sro_code="SRO-MH-NSK-02", sro_name="Sub-Registrar Office, Dindori", district="Nashik", state="Maharashtra", address="Tehsil Office Campus, Dindori 422202", contact_email="srodindori@igrmaharashtra.gov.in", jurisdiction_villages=["Dindori", "Vani", "Ozar"]),
            SROOffice(sro_code="SRO-KA-MYS-01", sro_name="Sub-Registrar Office, Mysuru North", district="Mysuru", state="Karnataka", address="DC Office Complex, Mysuru 570005", contact_email="sromysuru@karnataka.gov.in", jurisdiction_villages=["Chamundi Foothills", "Nazarbad", "Kuvempunagar"]),
            SROOffice(sro_code="SRO-GJ-GND-01", sro_name="Sub-Registrar Office, Gandhinagar", district="Gandhinagar", state="Gujarat", address="Sector 11, Gandhinagar 382011", contact_email="srogandhinagar@gujarat.gov.in", jurisdiction_villages=["GIFT City", "Koba", "Randesan"]),
        ]
        db.add_all(sros)
        db.flush()

        # -------------------------------------------------------------
        # 3. 12 REAL-WORLD LOCATION CONTEXTS & CADASTRE RECORDS
        # -------------------------------------------------------------
        parcels_data = [
            # Parcel 1: Chennai (TN) - Velachery residential context
            Parcel(
                ulpin="IN-TN-CHN-000001234567",
                survey_number="123/4A",
                subdivision_number="4A",
                state="Tamil Nadu",
                district="Chennai",
                taluk="Guindy",
                village="Velachery",
                area=2400.50,
                area_unit="sq.m",
                land_type="Residential",
                geometry_type="Polygon",
                coordinates=[[[80.2205, 12.9805], [80.2225, 12.9805], [80.2225, 12.9825], [80.2205, 12.9825], [80.2205, 12.9805]]],
                centroid_lng=80.2215,
                centroid_lat=12.9815
            ),
            # Parcel 2: Chennai (TN) - T. Nagar commercial context
            Parcel(
                ulpin="IN-TN-CHN-000002345678",
                survey_number="45/2B",
                subdivision_number="2B",
                state="Tamil Nadu",
                district="Chennai",
                taluk="Mambalam",
                village="T.Nagar",
                area=1850.00,
                area_unit="sq.m",
                land_type="Commercial",
                geometry_type="Polygon",
                coordinates=[[[80.2310, 13.0410], [80.2330, 13.0410], [80.2330, 13.0425], [80.2310, 13.0425], [80.2310, 13.0410]]],
                centroid_lng=80.2320,
                centroid_lat=13.0417
            ),
            # Parcel 3: Pune (MH) - Hinjawadi residential / dispute workflow context
            Parcel(
                ulpin="IN-MH-PUN-000003456789",
                survey_number="204/1B",
                subdivision_number="1B",
                state="Maharashtra",
                district="Pune",
                taluk="Haveli",
                village="Hinjawadi",
                area=3500.00,
                area_unit="sq.m",
                land_type="Residential",
                geometry_type="Polygon",
                coordinates=[[[73.7280, 18.5910], [73.7305, 18.5910], [73.7305, 18.5935], [73.7280, 18.5935], [73.7280, 18.5910]]],
                centroid_lng=73.7292,
                centroid_lat=18.5922
            ),
            # Parcel 4: Bengaluru (KA) - Electronic City technology corridor context
            Parcel(
                ulpin="IN-KA-BLR-000004567890",
                survey_number="88/3C",
                subdivision_number="3C",
                state="Karnataka",
                district="Bengaluru Urban",
                taluk="Anekal",
                village="Electronic City",
                area=8200.00,
                area_unit="sq.m",
                land_type="Commercial",
                geometry_type="Polygon",
                coordinates=[[[77.6820, 12.8440], [77.6855, 12.8440], [77.6855, 12.8475], [77.6820, 12.8475], [77.6820, 12.8440]]],
                centroid_lng=77.6837,
                centroid_lat=12.8457
            ),
            # Parcel 5: Hyderabad (TS) - Gachibowli financial district context
            Parcel(
                ulpin="IN-TS-HYD-000005678901",
                survey_number="142/1",
                subdivision_number="1",
                state="Telangana",
                district="Hyderabad",
                taluk="Serilingampally",
                village="Gachibowli",
                area=5400.00,
                area_unit="sq.m",
                land_type="Commercial",
                geometry_type="Polygon",
                coordinates=[[[78.3540, 17.4410], [78.3570, 17.4410], [78.3570, 17.4438], [78.3540, 17.4438], [78.3540, 17.4410]]],
                centroid_lng=78.3555,
                centroid_lat=17.4424
            ),
            # Parcel 6: Mumbai (MH) - Bandra Kurla Complex commercial context
            Parcel(
                ulpin="IN-MH-MUM-000006789012",
                survey_number="512/G",
                subdivision_number="G-Block",
                state="Maharashtra",
                district="Mumbai Suburban",
                taluk="Bandra",
                village="Bandra Kurla Complex",
                area=4150.00,
                area_unit="sq.m",
                land_type="Commercial",
                geometry_type="Polygon",
                coordinates=[[[72.8665, 19.0645], [72.8695, 19.0645], [72.8695, 19.0675], [72.8665, 19.0675], [72.8665, 19.0645]]],
                centroid_lng=72.8680,
                centroid_lat=19.0660
            ),
            # Parcel 7: Gurugram (HR) - Sector 29 commercial context
            Parcel(
                ulpin="IN-HR-GUR-000007890123",
                survey_number="33/1A",
                subdivision_number="1A",
                state="Haryana",
                district="Gurugram",
                taluk="Gurugram",
                village="Sector 29",
                area=6800.00,
                area_unit="sq.m",
                land_type="Commercial",
                geometry_type="Polygon",
                coordinates=[[[77.0835, 28.4705], [77.0868, 28.4705], [77.0868, 28.4735], [77.0835, 28.4735], [77.0835, 28.4705]]],
                centroid_lng=77.0851,
                centroid_lat=28.4720
            ),
            # Parcel 8: Coimbatore (TN) - Sulur industrial context
            Parcel(
                ulpin="IN-TN-CBE-000008901234",
                survey_number="77/2",
                subdivision_number="2",
                state="Tamil Nadu",
                district="Coimbatore",
                taluk="Sulur",
                village="Sulur",
                area=12500.00,
                area_unit="sq.m",
                land_type="Industrial",
                geometry_type="Polygon",
                coordinates=[[[77.1230, 11.0230], [77.1275, 11.0230], [77.1275, 11.0270], [77.1230, 11.0270], [77.1230, 11.0230]]],
                centroid_lng=77.1252,
                centroid_lat=11.0250
            ),
            # Parcel 9: Nashik (MH) - Dindori agricultural context
            Parcel(
                ulpin="IN-MH-NSK-000009012345",
                survey_number="305/4",
                subdivision_number="4",
                state="Maharashtra",
                district="Nashik",
                taluk="Dindori",
                village="Dindori",
                area=25000.00,
                area_unit="sq.m",
                land_type="Agricultural",
                geometry_type="Polygon",
                coordinates=[[[73.8300, 20.1960], [73.8350, 20.1960], [73.8350, 20.2010], [73.8300, 20.2010], [73.8300, 20.1960]]],
                centroid_lng=73.8325,
                centroid_lat=20.1985
            ),
            # Parcel 10: Mysuru (KA) - Chamundi Foothills Heritage Buffer (Disputed)
            Parcel(
                ulpin="IN-KA-MYS-000010123456",
                survey_number="19/8",
                subdivision_number="8",
                state="Karnataka",
                district="Mysuru",
                taluk="Mysuru",
                village="Chamundi Foothills",
                area=7500.00,
                area_unit="sq.m",
                land_type="Heritage",
                geometry_type="Polygon",
                coordinates=[[[76.6725, 12.2870], [76.6760, 12.2870], [76.6760, 12.2905], [76.6725, 12.2905], [76.6725, 12.2870]]],
                centroid_lng=76.6742,
                centroid_lat=12.2887
            ),
            # Parcel 11: Chennai (TN) - Sholinganallur OMR IT Corridor Residential
            Parcel(
                ulpin="IN-TN-CHN-000011234567",
                survey_number="64/3",
                subdivision_number="3",
                state="Tamil Nadu",
                district="Chennai",
                taluk="Sholinganallur",
                village="Sholinganallur",
                area=1950.00,
                area_unit="sq.m",
                land_type="Residential",
                geometry_type="Polygon",
                coordinates=[[[80.2265, 12.9005], [80.2295, 12.9005], [80.2295, 12.9035], [80.2265, 12.9035], [80.2265, 12.9005]]],
                centroid_lng=80.2280,
                centroid_lat=12.9020
            ),
            # Parcel 12: Gandhinagar (GJ) - GIFT City IFSC Fintech SEZ
            Parcel(
                ulpin="IN-GJ-GND-000012345678",
                survey_number="102/SEZ",
                subdivision_number="SEZ-F2",
                state="Gujarat",
                district="Gandhinagar",
                taluk="Gandhinagar",
                village="GIFT City",
                area=9200.00,
                area_unit="sq.m",
                land_type="SEZ",
                geometry_type="Polygon",
                coordinates=[[[72.6820, 23.1580], [72.6860, 23.1580], [72.6860, 23.1620], [72.6820, 23.1620], [72.6820, 23.1580]]],
                centroid_lng=72.6840,
                centroid_lat=23.1600
            )
        ]
        db.add_all(parcels_data)
        db.flush()

        # ULPIN Registries
        ulpin_regs = [
            ULPINRegistry(ulpin=p.ulpin, state_code=p.ulpin.split("-")[1], district_code=p.ulpin.split("-")[2], status="ACTIVE")
            for p in parcels_data
        ]
        db.add_all(ulpin_regs)

        # -------------------------------------------------------------
        # 4. OWNERS & PARCEL OWNERS
        # -------------------------------------------------------------
        owners_data = [
            ("OWN-001", user_map["citizen.ramesh@gmail.com"].id, "Ramesh Kumar", parcels_data[0].ulpin),
            ("OWN-002", user_map["citizen.priya@gmail.com"].id, "Priya Sundaram", parcels_data[1].ulpin),
            ("OWN-003", user_map["citizen.anand@gmail.com"].id, "Anand Deshmukh", parcels_data[2].ulpin),
            ("OWN-004", user_map["citizen.rajeshwari@gmail.com"].id, "Rajeshwari Hegde", parcels_data[3].ulpin),
            ("OWN-005", user_map["citizen.venkat@gmail.com"].id, "Dr. K. Venkat Rao", parcels_data[4].ulpin),
            ("OWN-006", user_map["citizen.vikram@gmail.com"].id, "Vikramaditya Singhania", parcels_data[5].ulpin),
            ("OWN-007", user_map["citizen.manpreet@gmail.com"].id, "Manpreet Kaur Ahluwalia", parcels_data[6].ulpin),
            ("OWN-008", user_map["citizen.senthil@gmail.com"].id, "K. Senthil Nathan", parcels_data[7].ulpin),
            ("OWN-009", user_map["citizen.balasaheb@gmail.com"].id, "Balasaheb Shinde", parcels_data[8].ulpin),
            ("OWN-010", user_map["citizen.jayasimha@gmail.com"].id, "S. Jayasimha", parcels_data[9].ulpin),
            ("OWN-011", user_map["citizen.ananya@gmail.com"].id, "Ananya Subramanian", parcels_data[10].ulpin),
            ("OWN-012", user_map["citizen.patel@gmail.com"].id, "Patel FinTech Infra Ltd", parcels_data[11].ulpin),
        ]

        owners = []
        parcel_owners = []
        for oid, cid, name, ulpin in owners_data:
            owners.append(Owner(owner_id=oid, citizen_id=cid, name=name, identity_type="AADHAAR"))
            parcel_owners.append(ParcelOwner(ulpin=ulpin, owner_id=oid, share_percentage=100.0, acquisition_mode="PURCHASE", status="ACTIVE"))

        db.add_all(owners)
        db.flush()
        db.add_all(parcel_owners)

        # -------------------------------------------------------------
        # 5. RECORD OF RIGHTS (RoR)
        # -------------------------------------------------------------
        rors = [
            RoRRecord(ror_number="ROR-2026-00123", ulpin=parcels_data[0].ulpin, status="ACTIVE", rights=["OWNERSHIP", "TRANSFER_RIGHTS", "MORTGAGE_RIGHTS"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="ROR-2026-00234", ulpin=parcels_data[1].ulpin, status="ACTIVE", rights=["OWNERSHIP", "COMMERCIAL_USE"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="7/12-GAT-204", ulpin=parcels_data[2].ulpin, status="DISPUTED", rights=["KHATEDAR_HAKKA"], tenure="Class-1 Freehold", restrictions="COURT_INJUNCTION_PENDING", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="KA-RTC-2026-00883", ulpin=parcels_data[3].ulpin, status="ACTIVE", rights=["OWNERSHIP", "COMMERCIAL_IT_SEZ", "TRANSFER_RIGHTS"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="TS-DHARANI-2026-142", ulpin=parcels_data[4].ulpin, status="ACTIVE", rights=["PATTADAR_PASSBOOK", "COMMERCIAL_RIGHTS"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="MH-PR-CARD-BKC-512", ulpin=parcels_data[5].ulpin, status="ACTIVE", rights=["FREEHOLD_OWNERSHIP", "DEVELOPMENT_RIGHTS"], tenure="Class-1 Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="HR-JAMABANDI-2026-331", ulpin=parcels_data[6].ulpin, status="ACTIVE", rights=["OWNERSHIP", "HOTEL_COMMERCIAL_USE"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="TN-PATTA-2026-0772", ulpin=parcels_data[7].ulpin, status="ACTIVE", rights=["OWNERSHIP", "INDUSTRIAL_OPERATIONS"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="7/12-NSK-DIN-305", ulpin=parcels_data[8].ulpin, status="ACTIVE", rights=["KHATEDAR_HAKKA", "AGRICULTURAL_CULTIVATION"], tenure="Class-1 Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="KA-RTC-2026-00198", ulpin=parcels_data[9].ulpin, status="DISPUTED", rights=["FAMILY_INHERITANCE_RIGHTS"], tenure="Freehold", restrictions="PARTITION_SUIT_PENDING", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="TN-PATTA-2026-0643", ulpin=parcels_data[10].ulpin, status="ACTIVE", rights=["OWNERSHIP", "RESIDENTIAL_DEVELOPMENT", "MORTGAGE_RIGHTS"], tenure="Freehold", restrictions="NONE", last_updated=datetime.utcnow()),
            RoRRecord(ror_number="GJ-ANYROR-2026-102", ulpin=parcels_data[11].ulpin, status="ACTIVE", rights=["IFSC_SEZ_DEVELOPMENT", "DATA_CENTRE_OPERATIONS"], tenure="Freehold SEZ", restrictions="NONE", last_updated=datetime.utcnow()),
        ]
        db.add_all(rors)

        # -------------------------------------------------------------
        # 6. REGISTRATION, DEEDS & ENCUMBRANCE
        # -------------------------------------------------------------
        regs = [
            RegistrationRecord(registration_number="DOC/2024/0458", ulpin=parcels_data[0].ulpin, sro_code="SRO-TN-CHN-01", registration_date=datetime.utcnow() - timedelta(days=500), deed_type="Sale Deed", market_value=12000000.0, consideration_amount=12000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2025/1120", ulpin=parcels_data[1].ulpin, sro_code="SRO-TN-CHN-01", registration_date=datetime.utcnow() - timedelta(days=200), deed_type="Gift Deed", market_value=18500000.0, consideration_amount=18500000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2023/8892", ulpin=parcels_data[3].ulpin, sro_code="SRO-KA-BLR-08", registration_date=datetime.utcnow() - timedelta(days=600), deed_type="Sale Deed", market_value=85000000.0, consideration_amount=85000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2024/3142", ulpin=parcels_data[4].ulpin, sro_code="SRO-TS-HYD-03", registration_date=datetime.utcnow() - timedelta(days=320), deed_type="Sale Deed", market_value=62000000.0, consideration_amount=62000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2023/1105", ulpin=parcels_data[5].ulpin, sro_code="SRO-MH-MUM-02", registration_date=datetime.utcnow() - timedelta(days=750), deed_type="Conveyance Deed", market_value=380000000.0, consideration_amount=380000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2023/7710", ulpin=parcels_data[6].ulpin, sro_code="SRO-HR-GUR-01", registration_date=datetime.utcnow() - timedelta(days=410), deed_type="Sale Deed", market_value=145000000.0, consideration_amount=145000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2022/4519", ulpin=parcels_data[7].ulpin, sro_code="SRO-TN-CBE-04", registration_date=datetime.utcnow() - timedelta(days=800), deed_type="Sale Deed", market_value=42000000.0, consideration_amount=42000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2021/8041", ulpin=parcels_data[8].ulpin, sro_code="SRO-MH-NSK-02", registration_date=datetime.utcnow() - timedelta(days=950), deed_type="Partition Deed", market_value=18000000.0, consideration_amount=18000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2020/2290", ulpin=parcels_data[9].ulpin, sro_code="SRO-KA-MYS-01", registration_date=datetime.utcnow() - timedelta(days=1200), deed_type="Family Settlement", market_value=28000000.0, consideration_amount=28000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2024/9912", ulpin=parcels_data[10].ulpin, sro_code="SRO-TN-CHN-01", registration_date=datetime.utcnow() - timedelta(days=180), deed_type="Sale Deed", market_value=22000000.0, consideration_amount=22000000.0, status="REGISTERED"),
            RegistrationRecord(registration_number="DOC/2024/0102", ulpin=parcels_data[11].ulpin, sro_code="SRO-GJ-GND-01", registration_date=datetime.utcnow() - timedelta(days=220), deed_type="Perpetual Lease", market_value=110000000.0, consideration_amount=110000000.0, status="REGISTERED"),
        ]
        db.add_all(regs)
        db.flush()

        deed1 = Deed(deed_id="DEED-2024-001", registration_number="DOC/2024/0458", ulpin=parcels_data[0].ulpin, deed_type="Sale Deed", execution_date=datetime.utcnow() - timedelta(days=500), document_id="DOC-2024-001", parties=[{"role": "SELLER", "name": "V. Sundaram"}, {"role": "BUYER", "name": "Ramesh Kumar"}])
        deed2 = Deed(deed_id="DEED-2023-004", registration_number="DOC/2023/8892", ulpin=parcels_data[3].ulpin, deed_type="Sale Deed", execution_date=datetime.utcnow() - timedelta(days=600), document_id="DOC-2023-004", parties=[{"role": "SELLER", "name": "Karnataka Industrial Area Development Board"}, {"role": "BUYER", "name": "Rajeshwari Hegde"}])
        db.add_all([deed1, deed2])

        # Active Mortgages / Encumbrances
        encs = [
            Encumbrance(encumbrance_id="ENC-2025-01", ulpin=parcels_data[1].ulpin, encumbrance_type="MORTGAGE", beneficiary="State Bank of India - SME Branch", amount=4500000.0, legal_status="ACTIVE", recorded_date=datetime.utcnow() - timedelta(days=150)),
            Encumbrance(encumbrance_id="ENC-2025-05", ulpin=parcels_data[4].ulpin, encumbrance_type="MORTGAGE", beneficiary="HDFC Bank Limited - Corporate", amount=25000000.0, legal_status="ACTIVE", recorded_date=datetime.utcnow() - timedelta(days=90)),
            Encumbrance(encumbrance_id="ENC-2024-06", ulpin=parcels_data[5].ulpin, encumbrance_type="MORTGAGE", beneficiary="ICICI Bank Corporate Banking", amount=90000000.0, legal_status="ACTIVE", recorded_date=datetime.utcnow() - timedelta(days=210)),
        ]
        mortgages = [
            Mortgage(mortgage_id="MORT-2025-01", ulpin=parcels_data[1].ulpin, bank_name="State Bank of India", loan_account_no="SBI-TERM-67890", mortgage_amount=4500000.0, status="ACTIVE"),
            Mortgage(mortgage_id="MORT-2025-05", ulpin=parcels_data[4].ulpin, bank_name="HDFC Bank Limited", loan_account_no="HDFC-CORP-9912", mortgage_amount=25000000.0, status="ACTIVE"),
            Mortgage(mortgage_id="MORT-2024-06", ulpin=parcels_data[5].ulpin, bank_name="ICICI Bank", loan_account_no="ICICI-MUM-5510", mortgage_amount=90000000.0, status="ACTIVE"),
        ]
        db.add_all(encs + mortgages)

        # -------------------------------------------------------------
        # 7. PLANNING, ZONING & BUILDING PERMISSIONS
        # -------------------------------------------------------------
        land_uses = [
            LandUse(ulpin=parcels_data[0].ulpin, zone="Residential", permitted_use="Residential villas & low-rise apartments", fsi_allowed=2.0),
            LandUse(ulpin=parcels_data[1].ulpin, zone="Commercial", permitted_use="Commercial office / Retail", fsi_allowed=2.5),
            LandUse(ulpin=parcels_data[2].ulpin, zone="Residential / Mixed", permitted_use="Residential apartment complex", fsi_allowed=1.8),
            LandUse(ulpin=parcels_data[3].ulpin, zone="Commercial / High-Tech IT Park", permitted_use="IT/ITES Campus & Tech Data Center", fsi_allowed=3.25),
            LandUse(ulpin=parcels_data[4].ulpin, zone="Commercial / Mixed High-Density", permitted_use="Commercial Office Tower & Retail", fsi_allowed=3.0),
            LandUse(ulpin=parcels_data[5].ulpin, zone="Commercial Financial Center", permitted_use="Corporate Headquarters & Banking Towers", fsi_allowed=4.0),
            LandUse(ulpin=parcels_data[6].ulpin, zone="Commercial / Hospitality", permitted_use="Hotel & Convention Center", fsi_allowed=2.75),
            LandUse(ulpin=parcels_data[7].ulpin, zone="General Industrial / Engineering", permitted_use="Precision Engineering & CNC Manufacturing Plant", fsi_allowed=1.5),
            LandUse(ulpin=parcels_data[8].ulpin, zone="Agricultural Green Belt", permitted_use="Perennial Grape Vineyards & Agro-Tourism", fsi_allowed=0.2),
            LandUse(ulpin=parcels_data[9].ulpin, zone="Eco-Sensitive Heritage Buffer", permitted_use="Eco-resort & Botanical Gardens (Strict Low-Rise)", fsi_allowed=0.75),
            LandUse(ulpin=parcels_data[10].ulpin, zone="Primary Residential", permitted_use="Residential Gated Villas & Townhouses", fsi_allowed=2.0),
            LandUse(ulpin=parcels_data[11].ulpin, zone="International Financial Services Centre (IFSC) / SEZ", permitted_use="Tier-IV Green Data Center & Fintech Tower", fsi_allowed=4.5),
        ]
        db.add_all(land_uses)

        building_perms = [
            BuildingPermission(permission_id="BP-CMDA-2025-0891", application_no="CMDA/PP/2025/1102", ulpin=parcels_data[0].ulpin, status="APPROVED", approved_floors=2, sanctioned_area=450.0, approval_date=datetime.utcnow() - timedelta(days=180)),
            BuildingPermission(permission_id="BP-BMRDA-2024-0412", application_no="BMRDA/TECH/2024/08", ulpin=parcels_data[3].ulpin, status="APPROVED", approved_floors=12, sanctioned_area=18500.0, approval_date=datetime.utcnow() - timedelta(days=240)),
            BuildingPermission(permission_id="BP-MMRDA-2024-0091", application_no="MMRDA/BKC/2024/512", ulpin=parcels_data[5].ulpin, status="APPROVED", approved_floors=24, sanctioned_area=16200.0, approval_date=datetime.utcnow() - timedelta(days=300)),
            BuildingPermission(permission_id="BP-GIFT-UDD-2024-001", application_no="GIFT/SEZ/2024/102", ulpin=parcels_data[11].ulpin, status="APPROVED", approved_floors=18, sanctioned_area=28000.0, approval_date=datetime.utcnow() - timedelta(days=120)),
        ]
        db.add_all(building_perms)

        # -------------------------------------------------------------
        # 8. MUNICIPAL, TAX & DISPUTES
        # -------------------------------------------------------------
        taxes = [
            PropertyTax(assessment_no="TAX-CHN-9812", ulpin=parcels_data[0].ulpin, annual_tax=18500.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-CHN-9813", ulpin=parcels_data[1].ulpin, annual_tax=45000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-PUN-7721", ulpin=parcels_data[2].ulpin, annual_tax=32000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-BBMP-88214", ulpin=parcels_data[3].ulpin, annual_tax=240000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-GHMC-55102", ulpin=parcels_data[4].ulpin, annual_tax=165000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-MCGM-90211", ulpin=parcels_data[5].ulpin, annual_tax=580000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-MCG-44120", ulpin=parcels_data[6].ulpin, annual_tax=310000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-SLR-1120", ulpin=parcels_data[7].ulpin, annual_tax=52000.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-ZP-NSK-4431", ulpin=parcels_data[8].ulpin, annual_tax=4500.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-MCC-MYS-1829", ulpin=parcels_data[9].ulpin, annual_tax=18000.0, paid_status="UNPAID"),
            PropertyTax(assessment_no="TAX-GCC-SHL-6430", ulpin=parcels_data[10].ulpin, annual_tax=22500.0, paid_status="PAID"),
            PropertyTax(assessment_no="TAX-GIFT-IFSC-012", ulpin=parcels_data[11].ulpin, annual_tax=420000.0, paid_status="PAID"),
        ]
        db.add_all(taxes)

        utilities = [
            UtilityConnection(connection_id="UTIL-01", ulpin=parcels_data[0].ulpin, utility_type="Electricity", provider="TANGEDCO", status="CONNECTED"),
            UtilityConnection(connection_id="UTIL-02", ulpin=parcels_data[0].ulpin, utility_type="Water", provider="CMWSSB", status="CONNECTED"),
            UtilityConnection(connection_id="UTIL-03", ulpin=parcels_data[3].ulpin, utility_type="High-Tension Electricity", provider="BESCOM", status="CONNECTED"),
            UtilityConnection(connection_id="UTIL-04", ulpin=parcels_data[4].ulpin, utility_type="Electricity", provider="TSSPDCL", status="CONNECTED"),
            UtilityConnection(connection_id="UTIL-05", ulpin=parcels_data[5].ulpin, utility_type="Power", provider="Adani Electricity", status="CONNECTED"),
            UtilityConnection(connection_id="UTIL-06", ulpin=parcels_data[8].ulpin, utility_type="Agri-Solar Pump Power", provider="MSEDCL", status="CONNECTED"),
            UtilityConnection(connection_id="UTIL-07", ulpin=parcels_data[11].ulpin, utility_type="66kV Substation", provider="UGVCL", status="CONNECTED"),
        ]
        db.add_all(utilities)

        # Active Legal Disputes (Pune & Mysuru)
        disputes = [
            DisputeRecord(
                dispute_id="DISP-2025-001",
                ulpin=parcels_data[2].ulpin,
                court_name="Civil Court Senior Division, Pune",
                case_number="OS-112/2025",
                dispute_type="Title & Boundary Partition Suit",
                status="ACTIVE",
                injunction_status=True,
                remarks="Interim injunction restraining alienation pending trial."
            ),
            DisputeRecord(
                dispute_id="DISP-2025-002",
                ulpin=parcels_data[9].ulpin,
                court_name="Civil Court Senior Division, Mysuru",
                case_number="OS-240/2025",
                dispute_type="Ancestral Partition & Injunction Claim",
                status="ACTIVE",
                injunction_status=True,
                remarks="Co-parcener claim pending evidence hearing."
            )
        ]
        db.add_all(disputes)

        # -------------------------------------------------------------
        # 9. DOCUMENTS & AUDIT TRAIL
        # -------------------------------------------------------------
        doc1_content = b"OFFICIAL_SALE_DEED_CONTENT_IN_TN_CHN_000001234567_RAMESH_KUMAR"
        doc1 = DocumentRecord(
            document_id="DOC-2024-001",
            ulpin=parcels_data[0].ulpin,
            document_type="Sale Deed",
            file_name="Registered_Sale_Deed_123_4A.pdf",
            file_location="./storage/documents/seed_doc1.pdf",
            file_size=len(doc1_content),
            sha256_hash=calculate_sha256(doc1_content),
            uploaded_by="Ramesh Kumar",
            uploaded_at=datetime.utcnow() - timedelta(days=400),
            verification_status="VERIFIED",
            verified_by="S. Balasubramanian (SRO-Guindy)",
            verified_at=datetime.utcnow() - timedelta(days=399)
        )
        doc2_content = b"OFFICIAL_DEED_ELECTRONIC_CITY_RAJESHWARI_HEGDE"
        doc2 = DocumentRecord(
            document_id="DOC-2023-004",
            ulpin=parcels_data[3].ulpin,
            document_type="Sale Deed",
            file_name="KIADB_Allotment_Deed_88_3C.pdf",
            file_location="./storage/documents/seed_doc2.pdf",
            file_size=len(doc2_content),
            sha256_hash=calculate_sha256(doc2_content),
            uploaded_by="Rajeshwari Hegde",
            uploaded_at=datetime.utcnow() - timedelta(days=580),
            verification_status="VERIFIED",
            verified_by="SRO Anekal",
            verified_at=datetime.utcnow() - timedelta(days=579)
        )
        db.add_all([doc1, doc2])

        # -------------------------------------------------------------
        # 10. ACTIVE OPERATIONAL WORKFLOW APPLICATIONS
        # -------------------------------------------------------------
        app1 = Application(
            application_id="APP-2026-0001",
            application_type="OWNERSHIP_TRANSFER",
            ulpin=parcels_data[0].ulpin,
            applicant_citizen_id=user_map["citizen.ramesh@gmail.com"].id,
            target_citizen_id=user_map["citizen.priya@gmail.com"].id,
            status=WorkflowStage.OFFICER_REVIEW,
            assigned_officer_id=user_map["revenue.officer@landstack.gov.in"].id,
            remarks="Sale agreement finalized. Ready for Revenue Officer endorsement."
        )
        app2 = Application(
            application_id="APP-2026-0002",
            application_type="OWNERSHIP_TRANSFER",
            ulpin=parcels_data[3].ulpin,
            applicant_citizen_id=user_map["citizen.rajeshwari@gmail.com"].id,
            target_citizen_id=user_map["citizen.anand@gmail.com"].id,
            status=WorkflowStage.SUBMITTED,
            assigned_officer_id=user_map["revenue.officer@landstack.gov.in"].id,
            remarks="Tech park expansion asset reallocation under review."
        )
        db.add_all([app1, app2])
        db.flush()

        app_doc1 = ApplicationDocument(application_id=app1.application_id, document_id=doc1.document_id, document_type="SALE_DEED", is_verified=True, verified_by="S. Balasubramanian")
        history1 = StatusHistory(application_id=app1.application_id, previous_status=WorkflowStage.SUBMITTED.value, new_status=WorkflowStage.OFFICER_REVIEW.value, transitioned_by="Automated_Validation_Engine", comments="All checks passed (ULPIN: Clear, RoR: Active, Encumbrance: Clear, Disputes: Clear).")
        history2 = StatusHistory(application_id=app2.application_id, previous_status=WorkflowStage.SUBMITTED.value, new_status=WorkflowStage.DOCUMENT_CHECK.value, transitioned_by="Citizen_Portal", comments="Application registered with uploaded digital sale agreement.")
        db.add_all([app_doc1, history1, history2])

        # Pre-seed Government Letters & Notices
        letters = [
            GovernmentLetter(
                letter_id="GOV-LTR-2026-001",
                ulpin=parcels_data[0].ulpin,
                letter_type="MUTATION_ORDER",
                issued_by="K. Selvakumar (Revenue Officer)",
                content="Statutory Notice: Ownership transfer application APP-2026-0001 is undergoing final revenue officer review.",
                issued_date=datetime.utcnow() - timedelta(days=2)
            ),
            GovernmentLetter(
                letter_id="GOV-LTR-2026-002",
                ulpin=parcels_data[3].ulpin,
                letter_type="NOC",
                issued_by="BMRDA Planning Authority",
                content="No Objection Certificate issued for Electronic City high-tech campus expansion (FSI 3.25 compliant).",
                issued_date=datetime.utcnow() - timedelta(days=10)
            )
        ]
        db.add_all(letters)

        # Pre-seed Initial Audit Log
        audit_seed = AuditLog(
            user_id="SYSTEM_BOOTSTRAP",
            user_role="SUPER_ADMIN",
            action="SYSTEM_INITIALIZED",
            ulpin=parcels_data[0].ulpin,
            timestamp=datetime.utcnow(),
            ip_address="127.0.0.1",
            previous_value=None,
            new_value="Land Stack India National Database Initialized with 12 Multi-State Operational Parcels."
        )
        db.add(audit_seed)

        db.commit()
        print("Database seeded successfully with 12 multi-state operational records, RoRs, and workflow applications!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        if close_at_end:
            db.close()


if __name__ == "__main__":
    seed_database(force=True)

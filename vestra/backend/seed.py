"""
VESTRA Demo Data Seed Script
Creates admin, agents, buyers, sellers, properties, verifications, and payments.
Run: python seed.py
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.core.config import settings
from app.core.database import AsyncSessionLocal, create_tables, Base, engine
from app.models.user import User, UserRole
from app.models.property import Property, PropertyStatus, PropertyType, ListingType, AgentProfile
from app.models.document import Verification, VerificationStatus, Document, DocumentType
from app.models.payment import Payment, PaymentStatus, PaymentMethod, PaymentPurpose
from app.core.security import get_password_hash

# ─── Data pools ────────────────────────────────────────────────────────────────
CITIES = [
    ("Nairobi", "Nairobi"),
    ("Mombasa", "Mombasa"),
    ("Kisumu", "Kisumu"),
    ("Eldoret", "Uasin Gishu"),
    ("Nakuru", "Nakuru"),
    ("Thika", "Kiambu"),
    ("Malindi", "Kilifi"),
    ("Nyeri", "Nyeri"),
]

NEIGHBORHOODS = {
    "Nairobi": ["Kileleshwa", "Karen", "Westlands", "Kilimani", "Lavington", "Runda", "South C", "Eastleigh"],
    "Mombasa": ["Nyali", "Bamburi", "Shanzu", "Kizingo", "Tudor"],
    "Kisumu": ["Milimani", "Kibuye", "Mamboleo", "Kondele"],
    "Eldoret": ["Elgon View", "Langas", "Kapsoya"],
    "Nakuru": ["Milimani", "Section 58", "Lanet"],
}

TITLES = {
    "residential": [
        "Modern {B}BR Apartment with Stunning Views",
        "Spacious {B}BR Family Home in {N}",
        "Elegant {B}BR Townhouse with Garden",
        "Executive {B}BR Penthouse {N}",
        "Charming {B}BR Bungalow with Servant Quarters",
        "Stylish {B}BR Apartment Near Amenities",
        "Premium {B}BR Villa with Pool {N}",
        "Affordable {B}BR Starter Home {N}",
    ],
    "commercial": [
        "Prime Office Space {N} {Sq} sqft",
        "Retail Shop with High Foot Traffic {N}",
        "Modern Office Block in CBD",
        "Warehouse with Loading Bay {N}",
        "Mixed-Use Building {N}",
    ],
    "land": [
        "Prime Plot {N} — Ready to Build",
        "Half-Acre Plot in {N}",
        "Commercial Plot with Highway Frontage",
        "Agricultural Land — {Sq} sqft in {N}",
    ],
}

AMENITIES_POOL = [
    ["Swimming Pool", "Gym", "CCTV", "Backup Generator"],
    ["Garden", "Parking", "Security", "Borehole"],
    ["Balcony", "Elevator", "Rooftop Terrace", "Concierge"],
    ["Servant Quarters", "Solar Panels", "Water Tank", "Electric Fence"],
    ["Clubhouse", "Kids Playground", "Jogging Track", "Sauna"],
    ["Air Conditioning", "Fibre Internet", "Walk-in Closet", "Jacuzzi"],
]

COUNTIES = list(set(c[1] for c in CITIES))


async def seed():
    await create_tables()

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        r = await db.execute(select(func.count(User.id)))
        if r.scalar_one() > 1:
            print("Database already seeded. Dropping and recreating...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await create_tables()
            print("Tables recreated.")

        now = datetime.now(timezone.utc)

        # ─── Users ─────────────────────────────────────────────────────────
        users_data = [
            {"email": "admin@vestra.co.ke", "full_name": "Admin User", "role": UserRole.super_admin, "is_verified": True, "is_active": True},
            {"email": "jane.muthoni@email.com", "full_name": "Jane Muthoni", "role": UserRole.agent, "is_verified": True, "is_active": True},
            {"email": "david.kamau@email.com", "full_name": "David Kamau", "role": UserRole.agent, "is_verified": True, "is_active": True},
            {"email": "peter.omondi@email.com", "full_name": "Peter Omondi", "role": UserRole.seller, "is_verified": True, "is_active": True},
            {"email": "faith.wanjiku@email.com", "full_name": "Faith Wanjiku", "role": UserRole.seller, "is_verified": True, "is_active": True},
            {"email": "grace.akinyi@email.com", "full_name": "Grace Akinyi", "role": UserRole.landlord, "is_verified": True, "is_active": True},
            {"email": "samuel.njoroge@email.com", "full_name": "Samuel Njoroge", "role": UserRole.buyer, "is_verified": False, "is_active": True},
            {"email": "mary.wekesa@email.com", "full_name": "Mary Wekesa", "role": UserRole.buyer, "is_verified": False, "is_active": True},
        ]

        users = []
        for i, u in enumerate(users_data):
            days_ago = random.randint(10, 180)
            user = User(
                email=u["email"],
                phone=f"+2547{random.randint(10000000, 99999999)}",
                full_name=u["full_name"],
                hashed_password=get_password_hash(u.get("password", "demo1234")),
                role=u["role"],
                is_verified=u["is_verified"],
                is_active=u["is_active"],
                location=random.choice(list(NEIGHBORHOODS.keys())),
                created_at=now - timedelta(days=days_ago),
            )
            db.add(user)
            users.append(user)

        await db.flush()
        admin = users[0]

        # Agent profiles for agents
        for user in users:
            if user.role == UserRole.agent:
                profile = AgentProfile(
                    user_id=user.id,
                    agency_name=f"{user.full_name} Realty",
                    license_number=f"EA-{random.randint(1000,9999)}",
                    years_experience=random.randint(2, 15),
                    specialization=["residential", "commercial"][:random.randint(1, 2)],
                    badge_level=random.choice(["silver", "gold", "platinum"]),
                    badge_expires_at=now + timedelta(days=365),
                    total_listings=random.randint(5, 50),
                    successful_deals=random.randint(2, 30),
                    rating=round(random.uniform(3.5, 5.0), 1),
                    subscription_tier="pro",
                    subscription_expires_at=now + timedelta(days=180),
                )
                db.add(profile)

        await db.flush()

        # ─── Properties ────────────────────────────────────────────────────
        properties = []
        # Ensure good distribution: 8 active, 3 pending_review, 2 draft, 2 sold
        statuses = [PropertyStatus.active] * 8 + [PropertyStatus.pending_review] * 3 + [PropertyStatus.draft] * 2 + [PropertyStatus.sold] * 2

        # Pre-define diverse property specs to ensure good demo coverage
        property_specs = [
            # (city, county, ptype, ltype, beds, baths, sqft, price, status)
            ("Nairobi", "Nairobi", PropertyType.residential, ListingType.sale, 4, 3, 2800, 25000000, 0),
            ("Nairobi", "Nairobi", PropertyType.residential, ListingType.rent, 3, 2, 1800, 5000, 0),
            ("Nairobi", "Nairobi", PropertyType.commercial, ListingType.sale, None, 2, 5000, 35000000, 0),
            ("Nairobi", "Nairobi", PropertyType.residential, ListingType.sale, 2, 1, 900, 8500000, 0),
            ("Nairobi", "Nairobi", PropertyType.land, ListingType.sale, None, None, 15000, 12000000, 0),
            ("Mombasa", "Mombasa", PropertyType.residential, ListingType.sale, 3, 2, 1600, 18000000, 0),
            ("Mombasa", "Mombasa", PropertyType.residential, ListingType.rent, 5, 4, 3500, 8000, 0),
            ("Kisumu", "Kisumu", PropertyType.residential, ListingType.sale, 3, 2, 1500, 9500000, 0),
            ("Eldoret", "Uasin Gishu", PropertyType.land, ListingType.sale, None, None, 25000, 5500000, 0),
            ("Nakuru", "Nakuru", PropertyType.residential, ListingType.sale, 4, 3, 2200, 14000000, 0),
            ("Thika", "Kiambu", PropertyType.residential, ListingType.rent, 2, 1, 800, 2500, 0),
            ("Nairobi", "Nairobi", PropertyType.commercial, ListingType.lease, None, 3, 8000, 800000, 0),
            ("Nairobi", "Nairobi", PropertyType.residential, ListingType.sale, 5, 4, 4200, 52000000, 1),  # pending
            ("Nairobi", "Nairobi", PropertyType.residential, ListingType.sale, 6, 5, 6000, 85000000, 3),  # sold (was going to be draft)
            ("Kisumu", "Kisumu", PropertyType.commercial, ListingType.sale, None, 1, 2000, 7500000, 3),  # sold
        ]

        for i, spec in enumerate(property_specs):
            city, county, ptype, ltype, beds, baths, sqft, price, status_idx = spec
            neighborhood = random.choice(NEIGHBORHOODS.get(city, ["Central"]))
            status = statuses[status_idx] if status_idx < len(statuses) else PropertyStatus.active

            if ptype == PropertyType.residential:
                title = random.choice(TITLES["residential"]).replace("{B}", str(beds or 3)).replace("{N}", neighborhood)
            elif ptype == PropertyType.commercial:
                title = random.choice(TITLES["commercial"]).replace("{N}", neighborhood).replace("{Sq}", str(sqft))
            else:
                title = random.choice(TITLES["land"]).replace("{N}", neighborhood).replace("{Sq}", str(sqft))

            trust = round(random.uniform(45, 98), 1) if status == PropertyStatus.active else None
            is_verified = status == PropertyStatus.active and trust and trust > 60

            prop = Property(
                owner_id=random.choice([u.id for u in users[1:5]]),  # agents & sellers
                title=title,
                description=f"Beautiful {ptype.value} in {neighborhood}, {city}. "
                            f"This property offers excellent value with modern finishes "
                            f"and convenient access to amenities, schools, and transport links. "
                            f"Perfect for {'families' if ptype == PropertyType.residential else 'business'} "
                            f"looking for quality space in a prime location.",
                property_type=ptype,
                listing_type=ltype,
                status=status,
                address=f"{random.randint(1, 500)} {neighborhood} Road",
                city=city,
                county=county,
                country="Kenya",
                price=float(price),
                currency="KES",
                price_negotiable=random.choice([True, False]),
                bedrooms=beds,
                bathrooms=baths,
                size_sqft=float(sqft),
                year_built=random.randint(2005, 2025),
                amenities=random.choice(AMENITIES_POOL),
                images=[],
                trust_score=trust,
                is_verified=is_verified,
                verification_badge=_badge(trust) if is_verified else None,
                views=random.randint(20, 1500),
                inquiries=random.randint(1, 30),
                created_at=now - timedelta(days=random.randint(5, 200)),
            )
            db.add(prop)
            properties.append(prop)

        await db.flush()

        # ─── Verifications ─────────────────────────────────────────────────
        verifications = []
        ai_notes = [
            ("approve", 12, 92, "under", "high", "All documents verified. Title deed matches KRA records.", []),
            ("approve", 8, 88, "fair", "high", "Property verified. Minor discrepancy in sale agreement date — resolved.", ["sale_agreement_date_mismatch"]),
            ("review", 25, 68, "over", "medium", "Price 22% above comparable sales in area. Request additional valuation.", ["price_anomaly"]),
            ("approve", 5, 95, "fair", "high", "Clean verification. All checks passed.", []),
            ("reject", 55, 35, "under", "low", "Multiple red flags: title deed number not in registry. Possible fraud.", ["title_deed_mismatch", "owner_name_mismatch", "suspicious_price"]),
            ("review", 18, 72, "fair", "medium", "Ownership confidence medium — national ID scan quality poor.", ["low_quality_id"]),
            ("approve", 10, 90, "fair", "high", "Verified. Good investment opportunity.", []),
            ("review", 30, 62, "over", "medium", "High price per sqft for area. Agent license expiring soon.", ["price_anomaly", "agent_license_expiring"]),
            ("approve", 6, 93, "under", "high", "Excellent value. Below market price.", []),
            ("approve", 7, 91, "fair", "high", "All documents in order. Property photos match satellite imagery.", []),
        ]

        for i, prop in enumerate(properties[:10]):
            rec, fraud, trust, price_rec, own_conf, summary, flags = ai_notes[i]
            status_map = {"approve": VerificationStatus.approved, "review": VerificationStatus.flagged, "reject": VerificationStatus.rejected}

            v = Verification(
                property_id=prop.id,
                user_id=prop.owner_id,
                requester_id=prop.owner_id,
                status=status_map[rec],
                fraud_risk_score=fraud,
                trust_score=trust,
                price_reasonableness=price_rec,
                ownership_confidence=own_conf,
                ai_recommendation=rec,
                document_flags=flags,
                ai_summary=summary,
                ai_raw_response={"fraud_risk_score": fraud, "trust_score": trust},
                created_at=prop.created_at + timedelta(days=random.randint(1, 5)),
            )
            db.add(v)
            verifications.append(v)

        await db.flush()

        # ─── Payments ──────────────────────────────────────────────────────
        purposes = list(PaymentPurpose)
        for i in range(20):
            ptype = random.choice(purposes)
            status = random.choices(
                [PaymentStatus.completed, PaymentStatus.completed, PaymentStatus.completed, PaymentStatus.processing, PaymentStatus.failed],
                weights=[60, 20, 10, 5, 5]
            )[0]
            method = random.choice([PaymentMethod.mpesa, PaymentMethod.mpesa, PaymentMethod.stripe])

            payment = Payment(
                user_id=random.choice(users[2:]).id,
                amount=random.choice([500, 500, 5000, 5000, 10000, 50000]),
                currency="KES",
                method=method,
                purpose=ptype,
                status=status,
                phone_number=f"+2547{random.randint(10000000, 99999999)}",
                reference=f"VST-{random.randint(100000, 999999)}",
                description=f"Vestra {ptype.value.replace('_', ' ').title()}",
                payment_metadata={"reference_id": random.randint(1, 15)},
                created_at=now - timedelta(days=random.randint(2, 150)),
            )
            if status == PaymentStatus.completed and method == PaymentMethod.mpesa:
                payment.mpesa_receipt_number = f"QK{random.randint(1000000, 9999999)}"
            db.add(payment)

        # ─── Documents ─────────────────────────────────────────────────────
        doc_types = list(DocumentType)
        for prop in properties[:8]:
            num_docs = random.randint(1, 3)
            for _ in range(num_docs):
                dt = random.choice(doc_types)
                doc = Document(
                    property_id=prop.id,
                    uploader_id=prop.owner_id,
                    document_type=dt,
                    file_name=f"{dt.value.replace('_', ' ').title()}_{prop.id}.pdf",
                    file_path=f"/uploads/docs/{prop.id}/{dt.value}.pdf",
                    file_size=random.randint(50000, 5000000),
                    mime_type="application/pdf",
                    is_verified=prop.is_verified,
                    created_at=prop.created_at + timedelta(hours=random.randint(1, 48)),
                )
                db.add(doc)

        await db.commit()

        print("=" * 60)
        print("  VESTRA Demo Data Seeded Successfully!")
        print("=" * 60)
        print(f"  Users:           {len(users)}")
        print(f"  Properties:      {len(properties)}")
        print(f"  Verifications:   {len(verifications)}")
        print(f"  Payments:        20")
        print(f"  Documents:       ~24")
        print()
        print("  --- Login Credentials ---")
        print(f"  Admin:    admin@vestra.co.ke / demo1234")
        print(f"  Agent:    jane.muthoni@email.com / demo1234")
        print(f"  Seller:   peter.omondi@email.com / demo1234")
        print(f"  Buyer:    samuel.njoroge@email.com / demo1234")
        print("=" * 60)


def _badge(score):
    if not score: return None
    if score >= 90: return "platinum"
    if score >= 75: return "gold"
    if score >= 60: return "silver"
    return "bronze"


if __name__ == "__main__":
    asyncio.run(seed())

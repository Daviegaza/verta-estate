"""
Simple demo data seeder — synchronous, no async issues.
Run: python seed_simple.py
"""
import os
os.environ["ENVIRONMENT"] = "development"

import json
import bcrypt
import psycopg2
from datetime import datetime, timedelta, timezone
import random

# Connection
DB_URL = "postgresql://postgres:postgres@localhost:5432/vestra"
now = datetime.now(timezone.utc)
password_hash = bcrypt.hashpw("demo1234".encode(), bcrypt.gensalt()).decode()

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

# Drop all tables
cur.execute("""
    DO $$ DECLARE r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
    END $$;
""")
print("Tables dropped.")

import asyncio
from app.core.database import engine, Base

# Create tables — must import all models so Base.metadata knows about them
async def _create():
    from app.models import user, property, document, payment, audit_log, subscription, referral, title_chain, rental  # noqa: F401
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

asyncio.run(_create())
print("Tables created.")

# ── Users ─────────────────────────────────────────────────────────────────
users_sql = """
INSERT INTO users (email, phone, full_name, hashed_password, role, is_verified, is_active, location, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
"""
users_data = [
    ("admin@vestra.co.ke", "+254700000001", "Admin User", password_hash, "super_admin", True, True, "Nairobi", now - timedelta(days=100)),
    ("jane.muthoni@email.com", "+254700000002", "Jane Muthoni", password_hash, "agent", True, True, "Nairobi", now - timedelta(days=90)),
    ("david.kamau@email.com", "+254700000003", "David Kamau", password_hash, "agent", True, True, "Mombasa", now - timedelta(days=80)),
    ("amara.chioma@email.com", "+254700000004", "Amara Chioma", password_hash, "agent", True, True, "Kisumu", now - timedelta(days=70)),
    ("peter.omondi@email.com", "+254700000005", "Peter Omondi", password_hash, "seller", True, True, "Nairobi", now - timedelta(days=60)),
    ("faith.wanjiku@email.com", "+254700000006", "Faith Wanjiku", password_hash, "seller", True, True, "Karen", now - timedelta(days=50)),
    ("kofi.abebe@email.com", "+254700000007", "Kofi Abebe", password_hash, "seller", True, True, "Nakuru", now - timedelta(days=40)),
    ("grace.akinyi@email.com", "+254700000008", "Grace Akinyi", password_hash, "landlord", True, True, "Eldoret", now - timedelta(days=30)),
    ("emmanuel.mwangi@email.com", "+254700000009", "Emmanuel Mwangi", password_hash, "landlord", True, True, "Thika", now - timedelta(days=20)),
    ("samuel.njoroge@email.com", "+254700000010", "Samuel Njoroge", password_hash, "buyer", False, True, "Nairobi", now - timedelta(days=10)),
    ("mary.wekesa@email.com", "+254700000011", "Mary Wekesa", password_hash, "buyer", False, True, "Kisumu", now - timedelta(days=5)),
    ("fatima.hassan@email.com", "+254700000012", "Fatima Hassan", password_hash, "buyer", True, True, "Mombasa", now - timedelta(days=5)),
    ("john.kariuki@email.com", "+254700000013", "John Kariuki", password_hash, "buyer", False, True, "Nairobi", now),
    ("aisha.juma@email.com", "+254700000014", "Aisha Juma", password_hash, "buyer", True, True, "Nakuru", now),
    ("brian.otieno@email.com", "+254700000015", "Brian Otieno", password_hash, "buyer", False, True, "Eldoret", now),
]

user_ids = []
for u in users_data:
    cur.execute(users_sql, u)
    user_ids.append(cur.fetchone()[0])
print(f"Inserted {len(user_ids)} users.")

# ── Agent Profiles ─────────────────────────────────────────────────────────
agent_sql = """
INSERT INTO agent_profiles (user_id, agency_name, license_number, years_experience, badge_level, badge_expires_at, total_listings, successful_deals, rating, subscription_tier, subscription_expires_at, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
for uid in user_ids[:4]:  # First 4 users are agents (indices 1-3 are actual agents, 0 is admin)
    cur.execute(agent_sql, (
        uid, f"Agent {uid} Realty", f"EA-{random.randint(1000,9999)}",
        random.randint(3, 20), random.choice(["gold", "platinum", "silver"]),
        now + timedelta(days=365), random.randint(10, 100), random.randint(5, 50),
        round(random.uniform(4.0, 5.0), 1), "pro", now + timedelta(days=180), now
    ))
print("Inserted agent profiles.")

# ── Properties (50+) ────────────────────────────────────────────────────────
prop_sql = """
INSERT INTO properties (owner_id, title, description, property_type, listing_type, status, address, city, county, country, price, currency, price_negotiable, bedrooms, bathrooms, size_sqft, year_built, amenities, trust_score, is_verified, verification_badge, views, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
"""

PROPERTIES = [
    # (city, ptype, ltype, beds, baths, sqft, price, title, desc, status)
    ("Nairobi", "residential", "sale", 4, 3, 3200, 42000000, "Luxury 4-Bedroom Villa in Kileleshwa with Pool",
     "Stunning contemporary villa in Kileleshwa with private pool, manicured garden, modern kitchen, en-suite bathrooms, staff quarters, and 24-hour security. Walking distance to Yaya Centre.", "active"),
    ("Nairobi", "residential", "sale", 5, 4, 4500, 78000000, "Executive 5-Bedroom Mansion in Spring Valley",
     "Magnificent family home on half an acre in one of Nairobi's most prestigious neighborhoods. Grand foyer, formal living/dining, home office, swimming pool, mature garden, guest cottage.", "active"),
    ("Nairobi", "commercial", "sale", None, 3, 8000, 95000000, "Prime Commercial Building in Upper Hill — Grade A Offices",
     "Brand new Grade A office building in Nairobi's financial district. Column-free 8,000 sqft floor plates, panoramic city views, 3 elevators, backup generator, rooftop terrace, 50+ parking.", "active"),
    ("Nairobi", "residential", "rent", 2, 1, 950, 85000, "Stylish 2-Bedroom Apartment in Kilimani — Furnished",
     "Beautifully furnished 2-bedroom apartment in vibrant Kilimani. Open-plan living, fully equipped kitchen, balcony with city views, gym access, secure parking. Rent includes service charge.", "active"),
    ("Nairobi", "residential", "sale", 4, 4, 3800, 65000000, "Elegant 4-Bedroom Country Home in Karen",
     "Charming country-style home on 1.5 acres in Karen. Exposed beam ceilings, fireplace, wrap-around veranda, swimming pool, tennis court, mature trees, organic garden, staff quarters.", "active"),
    ("Nairobi", "residential", "rent", 3, 2, 1500, 120000, "Modern 3-Bedroom Apartment in Westlands — Near Sarit Centre",
     "Contemporary unfurnished apartment in Westlands. Floor-to-ceiling windows, modern kitchen, en-suite master, dedicated parking. 5-min walk to Sarit Centre, banks, and restaurants.", "active"),
    ("Nairobi", "residential", "rent", 1, 1, 600, 25000, "Cozy 1-Bedroom Bedsitter in Parklands — Ideal for Students",
     "Well-maintained bedsitter near Aga Khan University. Built-in wardrobes, modern bathroom, shared rooftop, reliable water. Walking to matatu stages and Waiyaki Way.", "active"),
    ("Nairobi", "residential", "sale", 3, 2, 2000, 28000000, "Charming 3-Bedroom Townhouse in Muthangari",
     "Delightful townhouse in a gated community of 8 units. Private garden, open-plan living/dining, modern kitchen, en-suite master, guest cloakroom, 2 parking spaces.", "active"),
    ("Nairobi", "residential", "sale", 4, 3, 2800, 38000000, "Spacious Family Home in Lavington Green — 4 Bedrooms",
     "Beautiful family residence in leafy Lavington. Double-volume living room, separate dining, family/TV room, modern kitchen with pantry, staff quarters, mature garden, borehole.", "active"),
    ("Nairobi", "residential", "rent", 3, 2, 1600, 95000, "Newly Renovated 3-Bedroom House — King'ara Road, Lavington",
     "Recently renovated house in quiet cul-de-sac off King'ara Road. Modern finishes, large living room, private garden, fitted kitchen, 2 parking spaces, 24-hour security.", "active"),
    ("Runda", "residential", "sale", 5, 5, 5000, 85000000, "Premium 5-Bedroom Villa in New Runda — Resort-Style",
     "Exceptional villa in exclusive New Runda. Grand entrance, double-volume living, home cinema, wine cellar, infinity pool, tropical garden, staff quarters, 4-car garage.", "active"),
    ("Runda", "residential", "rent", 4, 3, 2800, 150000, "Executive 4-Bedroom Furnished Home in Runda Estate",
     "Luxuriously furnished home in Runda. All en-suite bedrooms, modern kitchen, study, private garden, pool, borehole, generator. Ideal for expat family or corporate executive.", "active"),
    ("Mombasa", "residential", "sale", 4, 3, 2600, 32000000, "Beachside 4-Bedroom Villa in Nyali — Ocean Breeze",
     "Stunning coastal villa minutes from Nyali Beach. Swahili-style architecture, makuti ceilings, tropical garden, pool, rooftop terrace with ocean views. Perfect holiday home or Airbnb.", "active"),
    ("Mombasa", "residential", "rent", 2, 1, 800, 35000, "2-Bedroom Beach Apartment in Bamburi",
     "Bright airy apartment in secure beachfront complex. Furnished with coastal decor, ocean-view balcony, shared pool, generator, 24-hour security. Walk to Bamburi Beach.", "active"),
    ("Mombasa", "commercial", "sale", None, 2, 3500, 28000000, "Thriving Beachfront Restaurant & Bar in Nyali",
     "Established restaurant on Nyali beachfront. Seats 120, fully equipped kitchen, liquor license, ocean-view terrace, ample parking, loyal clientele. Staff of 15 included.", "active"),
    ("Mombasa", "land", "sale", None, None, 87000, 12500000, "Prime Beachfront Plot in Shanzu — 2 Acres",
     "Rare 2-acre beachfront land in Shanzu. Clean title deed, approved for mixed-use development. Between Sarova Whitesands and Pride Inn Paradise. Survey plan available.", "active"),
    ("Kisumu", "residential", "sale", 4, 3, 2200, 18000000, "Lakeside 4-Bedroom Home in Milimani, Kisumu",
     "Elegant family home in Kisumu's premier Milimani estate. Partial Lake Victoria views, modern kitchen, en-suite bedrooms, mature garden, borehole, staff quarters.", "active"),
    ("Kisumu", "residential", "rent", 3, 2, 1400, 35000, "Modern 3-Bedroom in Riat Hills — Panoramic Lake Views",
     "Brand new apartment in up-and-coming Riat Hills. Stunning Lake Victoria views from balcony, modern finishes, fitted kitchen, secure parking. Close to United Mall.", "active"),
    ("Kisumu", "land", "sale", None, None, 130000, 4800000, "3-Acre Plot in Mamboleo — Ready to Build",
     "Well-located plot near Northern Bypass in Mamboleo. Gentle slope, good drainage, tarmac road access, electricity and water nearby. Excellent long-term investment.", "active"),
    ("Nakuru", "residential", "sale", 3, 2, 1600, 12500000, "Beautiful 3-Bedroom Bungalow in Milimani, Nakuru",
     "Well-maintained bungalow in Nakuru's most desirable neighborhood. Fireplace, modern kitchen, en-suite master, mature garden, garage, staff quarters. Close to Lake Nakuru Park.", "active"),
    ("Nakuru", "residential", "rent", 2, 1, 750, 18000, "Affordable 2-Bedroom in Section 58, Nakuru",
     "Clean secure apartment in convenient Section 58. Spacious rooms, tiled floors, built-in wardrobes, reliable water, secure compound. Walking to Nakuru town center.", "active"),
    ("Nakuru", "land", "sale", None, None, 22000, 2800000, "Half-Acre Residential Plot in London Estate, Nakuru",
     "Prime plot in fast-growing London Estate. Level terrain, tarmac road, electricity on site, water nearby. Quality homes in neighborhood. Nakuru is Kenya's fastest-growing city.", "active"),
    ("Eldoret", "residential", "sale", 4, 3, 2400, 15000000, "Spacious 4-Bedroom in Elgon View — Eldoret's Best Address",
     "Quality-built family home in prestigious Elgon View. Cherengani Hills views, modern kitchen, en-suite master, 2 living rooms, home office, mature garden, borehole, staff quarters.", "active"),
    ("Eldoret", "residential", "rent", 2, 1, 700, 15000, "Modern 2-Bedroom in Kapsoya — Close to Moi University",
     "Newly built apartment block in Kapsoya. Tiled throughout, fitted kitchen, secure parking, borehole water. Popular with Moi University staff and students. Long-term leases preferred.", "active"),
    ("Thika", "residential", "sale", 3, 2, 1400, 8500000, "3-Bedroom Modern Bungalow in Thika — Great for Families",
     "Contemporary bungalow in quiet Thika estate. Open-plan living, modern kitchen, en-suite master, landscaped garden, secure parking. Close to Thika Road Mall, 45 minutes to Nairobi.", "active"),
    ("Kiambu", "land", "sale", None, None, 44000, 5500000, "1-Acre Farm Land in Kiambu — Fertile Red Soil",
     "Excellent agricultural land 30 minutes from Nairobi. Fertile red volcanic soil, perennial river along boundary, electricity nearby. Area produces tea, coffee, vegetables for Nairobi.", "active"),
    ("Ruaka", "residential", "rent", 1, 1, 500, 18000, "Compact Studio in Ruaka — Near Two Rivers Mall",
     "Efficient studio in modern block near Two Rivers. Built-in kitchenette, modern bathroom, fiber-ready, secure compound with CCTV. Perfect for young professional in Gigiri or Westlands.", "active"),
    ("Limuru", "land", "sale", None, None, 90000, 7500000, "2-Acre Tea-Growing Land in Limuru — Cool Climate",
     "Beautiful 2-acre parcel in Limuru highlands with established tea bushes and mature trees. Cool climate, clean air, Aberdare Range views. Near Limuru Road, Nairobi-Nakuru Highway.", "active"),
    ("Kitengela", "residential", "sale", 3, 2, 1500, 6500000, "Affordable 3-Bedroom Maisonette in Kitengela",
     "Value-packed maisonette on own plot in growing Kitengela. Spacious rooms, modern finishes, private compound with 3-car parking, water storage. 30 min to JKIA, 45 min to Nairobi CBD.", "active"),
    ("Ngong", "residential", "rent", 2, 1, 850, 18000, "2-Bedroom House in Ngong — Ngong Hills Views",
     "Charming house with breathtaking Ngong Hills views. Fireplace, modern kitchen, garden with fruit trees, secure parking. Fresh air, quiet neighborhood, 30 min to Karen.", "active"),
    ("Rongai", "residential", "rent", 3, 2, 1200, 25000, "Family 3-Bedroom House in Rongai — Near Catholic University",
     "Comfortable family house in secure gated estate near CUEA. Modern finishes, fitted kitchen, en-suite master, playground, 24-hour security. Great value for families seeking space.", "active"),
    ("Kitengela", "land", "sale", None, None, 22000, 1800000, "Half-Acre Plot in Kitengela — Near Namanga Road",
     "Well-priced residential plot in fast-growing Kitengela. Clean title deed, surveyed with beacons, access road, electricity nearby. Excellent capital appreciation potential.", "active"),
    ("Athi River", "land", "sale", None, None, 200000, 15000000, "5-Acre Industrial Plot in Athi River — EPZ Zone",
     "Prime industrial land in Athi River's EPZ. 200m Mombasa Road frontage, level terrain, electricity on site, borehole. Approved for warehousing/manufacturing. 20 min to JKIA.", "active"),
    ("Athi River", "residential", "rent", 2, 1, 800, 12000, "Budget-Friendly 2-Bedroom in Athi River",
     "Clean secure apartment near Daystar University. Tiled floors, reliable water, secure parking, near public transport. Popular with Daystar students and EPZ workers.", "active"),
    ("Ruiru", "residential", "sale", 2, 1, 700, 3500000, "2-Bedroom Starter Home in Ruiru — Affordable First Home",
     "Perfect starter home for young family or first-time buyer. Modern bungalow, open-plan living, fitted kitchen, en-suite master, private garden. Ruiru booming with new infrastructure.", "active"),
    ("Nairobi", "residential", "rent", 2, 2, 1100, 90000, "Fully Furnished 2-Bedroom in Hurlingham — Corporate Let",
     "Executive furnished apartment in Hurlingham. Modern decor, fully equipped kitchen, DSTV, fast WiFi, backup generator, pool, gym, underground parking. Walk to Yaya Centre.", "active"),
    ("Nairobi", "commercial", "rent", None, 1, 2500, 60000, "Ground-Floor Retail Space in Ngara — High Foot Traffic",
     "Prime ground-floor commercial space on busy Ngara road. Previously electronics shop. High ceilings, storage room, roller shutter, back entrance. Heavy pedestrian traffic.", "active"),
    ("Nairobi", "residential", "rent", 5, 4, 3500, 200000, "Diplomatic Residence in Spring Valley — 5 Beds",
     "Prestigious furnished residence in diplomatic belt. Grand living/dining rooms, study, gourmet kitchen, en-suite bedrooms, staff quarters for 4, pool, garden, borehole, generator.", "active"),
    ("Kileleshwa", "residential", "sale", 3, 2, 1800, 22000000, "Newly Built 3-Bedroom Apartment in Kileleshwa — Rooftop",
     "Brand new boutique development of 6 units. Floor-to-ceiling windows, Italian kitchen, en-suite bedrooms, private rooftop terrace with BBQ, gym, panoramic Nairobi skyline views.", "active"),
    ("Karen", "land", "sale", None, None, 220000, 45000000, "5-Acre Prime Land in Karen — Gated Community Ready",
     "Exceptional land in heart of Karen, 2km from Karen Shopping Centre. Mature trees, gentle slope, borehole drilled, tarmac road. Approved for half-acre subdivision or gated community.", "active"),
    ("Nairobi", "short_stay", "rent", 1, 1, 500, 3000, "Luxury Studio Airbnb in Kilimani",
     "Professionally managed short-stay studio. Hotel-quality furnishings, kitchenette, fast WiFi, smart TV, weekly housekeeping. Rooftop pool, gym. Generates KES 120K/month.", "active"),
    ("Mombasa", "short_stay", "rent", 3, 2, 1400, 8000, "Beachfront Holiday Villa in Nyali — Turnkey Airbnb",
     "Beautifully decorated 3-bedroom holiday villa steps from Nyali Beach. Private pool, tropical garden, fully equipped kitchen. Superhost-rated 4.9 stars (120+ reviews). Turnkey operation.", "active"),
    # pending / sold
    ("Nairobi", "residential", "sale", 3, 2, 1800, 25000000, "Pending Review: Modern Kileleshwa Apartment",
     "Under AI verification review. Modern finishes, excellent location.", "pending_review"),
    ("Mombasa", "residential", "sale", 5, 4, 4000, 55000000, "Sold: Luxury Beachfront Villa in Nyali",
     "Recently sold. Benchmark property for Nyali luxury market.", "sold"),
    ("Nairobi", "residential", "sale", 6, 5, 6000, 95000000, "Sold: Ultra-Luxury Runda Mansion",
     "Recently sold. Record price for Runda estate.", "sold"),
]

AMENITIES_POOL = [
    ["Swimming Pool", "Gym", "CCTV", "Backup Generator", "Borehole"],
    ["Garden", "Parking", "Security", "Borehole", "Electric Fence"],
    ["Balcony", "Elevator", "Rooftop Terrace", "Concierge", "Fibre Internet"],
    ["Servant Quarters", "Solar Panels", "Water Tank", "Electric Fence", "Automatic Gate"],
    ["Clubhouse", "Kids Playground", "Jogging Track", "Sauna", "Steam Room"],
    ["Air Conditioning", "Fibre Internet", "Walk-in Closet", "Jacuzzi", "Home Office"],
    ["Swimming Pool", "Tennis Court", "Garden", "Staff Quarters", "Generator House"],
    ["CCTV", "Intercom", "Backup Water", "Underground Parking", "Gym"],
]

prop_ids = []
seller_ids = user_ids[4:8]  # Sellers + landlords
for i, p in enumerate(PROPERTIES):
    city, ptype, ltype, beds, baths, sqft, price, title, desc, status = p
    trust = round(random.uniform(55, 98), 1) if status == "active" else None
    is_verified = status == "active" and trust and trust > 60
    badge = None
    if is_verified and trust:
        badge = "platinum" if trust >= 90 else "gold" if trust >= 75 else "silver" if trust >= 60 else "bronze"

    cur.execute(prop_sql, (
        random.choice(seller_ids), title, desc, ptype, ltype, status,
        f"{random.randint(1, 500)} {random.choice(['Road','Avenue','Lane','Drive','Close'])}",
        city, "Nairobi" if city in ("Karen","Kileleshwa","Westlands","Lavington","Runda","Kileleshwa","Parklands","Upper Hill","Ruiru","Ruaka","Ngong","Rongai","Kitengela","Athi River","Limuru","Kiambu","Thika") else city,
        "Kenya", float(price), "KES", random.choice([True, True, False]),
        beds, baths, float(sqft), random.randint(2008, 2026),
        json.dumps(random.choice(AMENITIES_POOL)), trust, is_verified, badge,
        random.randint(50, 5000), now - timedelta(days=random.randint(1, 400))
    ))
    prop_ids.append(cur.fetchone()[0])
print(f"Inserted {len(prop_ids)} properties.")

# ── Verifications ───────────────────────────────────────────────────────────
ver_sql = """
INSERT INTO verifications (property_id, user_id, requester_id, status, fraud_risk_score, trust_score, price_reasonableness, ownership_confidence, ai_recommendation, document_flags, ai_summary, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
ai_results = [
    ("approved", 8, 92, "under", "high", "approve", "All documents verified. Clean title deed. Excellent investment."),
    ("approved", 12, 88, "fair", "high", "approve", "Minor KRA PIN discrepancy resolved. Property verified."),
    ("approved", 5, 95, "fair", "high", "approve", "Clean verification. All checks passed."),
    ("flagged", 28, 65, "over", "medium", "review", "Price 20% above market. Request additional valuation."),
    ("rejected", 52, 32, "under", "low", "reject", "Title deed not in official registry. Possible fraud."),
    ("flagged", 18, 72, "fair", "medium", "review", "Agent license expiring. ID scan quality poor."),
    ("approved", 10, 90, "fair", "high", "approve", "All clear. Good investment in growing area."),
    ("approved", 6, 94, "under", "high", "approve", "Below market price — excellent deal."),
    ("approved", 7, 91, "fair", "high", "approve", "Photos match satellite imagery. Documents verified."),
    ("flagged", 22, 68, "fair", "medium", "review", "Land search shows minor encumbrance. Needs resolution."),
    ("approved", 4, 96, "fair", "high", "approve", "Perfect documentation. Platinum trust level."),
    ("approved", 9, 89, "fair", "high", "approve", "Verified with minor note on sale agreement date."),
]

for i, (status, fraud, trust, price_rec, own_conf, rec, summary) in enumerate(ai_results):
    if i < len(prop_ids):
        cur.execute(ver_sql, (
            prop_ids[i], seller_ids[0], seller_ids[0],
            status, fraud, trust, price_rec, own_conf, rec,
            "[]", summary, now - timedelta(days=random.randint(1, 30))
        ))
print(f"Inserted {len(ai_results)} verifications.")

# ── Payments ───────────────────────────────────────────────────────────────
pay_sql = """
INSERT INTO payments (user_id, amount, currency, method, purpose, status, phone_number, reference, description, mpesa_receipt_number, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
for i in range(30):
    purp = random.choice(["verification_report", "subscription", "listing_fee", "agent_badge", "transaction_fee"])
    st = random.choice(["completed", "completed", "completed", "processing", "failed"])
    meth = random.choice(["mpesa", "mpesa", "mpesa", "stripe"])
    receipt = f"QK{random.randint(1000000, 9999999)}" if st == "completed" and meth == "mpesa" else None
    cur.execute(pay_sql, (
        random.choice(user_ids[4:]), random.choice([500, 1000, 5000, 5000, 10000, 25000, 50000]),
        "KES", meth, purp, st, f"+2547{random.randint(10000000, 99999999)}",
        f"VST-{random.randint(100000, 999999)}", f"Vestra {purp.replace('_', ' ').title()}",
        receipt, now - timedelta(days=random.randint(2, 200))
    ))
print("Inserted 30 payments.")

cur.close()
conn.close()
print()
print("=" * 60)
print("  VESTRA Demo Data Seeded Successfully!")
print(f"  Users: {len(user_ids)} | Properties: {len(prop_ids)}")
print(f"  Verifications: {len(ai_results)} | Payments: 30")
print("=" * 60)
print("  Login: admin@vestra.co.ke / demo1234")
print("=" * 60)

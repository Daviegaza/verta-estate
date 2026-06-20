"""
VESTRA Rich Demo Data Seed Script
Creates 50+ properties, 15+ users, verifications, payments, reviews, and more.
Run: python seed.py
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.core.config import settings
from app.core.database import AsyncSessionLocal, create_tables, Base, engine
from app.core.hashing import get_password_hash
from app.models.user import User, UserRole
from app.models.property import Property, PropertyStatus, PropertyType, ListingType, AgentProfile
from app.models.document import Verification, VerificationStatus, Document, DocumentType
from app.models.payment import Payment, PaymentStatus, PaymentMethod, PaymentPurpose

# ─── Rich data pools ─────────────────────────────────────────────────────────

CITIES = [
    ("Nairobi", "Nairobi"), ("Karen", "Nairobi"), ("Kilimani", "Nairobi"),
    ("Westlands", "Nairobi"), ("Lavington", "Nairobi"), ("Runda", "Nairobi"),
    ("Kileleshwa", "Nairobi"), ("Parklands", "Nairobi"), ("Upper Hill", "Nairobi"),
    ("Mombasa", "Mombasa"), ("Nyali", "Mombasa"), ("Bamburi", "Mombasa"),
    ("Kisumu", "Kisumu"), ("Nakuru", "Nakuru"), ("Eldoret", "Uasin Gishu"),
    ("Thika", "Kiambu"), ("Kiambu", "Kiambu"), ("Ruaka", "Kiambu"),
    ("Kitengela", "Kajiado"), ("Ngong", "Kajiado"), ("Rongai", "Kajiado"),
    ("Athi River", "Machakos"), ("Ruiru", "Kiambu"), ("Limuru", "Kiambu"),
]

NEIGHBORHOODS = {
    "Nairobi": ["CBD", "Upper Hill", "Hurlingham", "Ngara", "Kileleshwa", "Spring Valley"],
    "Karen": ["Karen Blixen", "Hardy", "Langata", "Karen Plains"],
    "Kilimani": ["Kilimani", "Yaya Centre Area", "Argwings Kodhek", "Milimani"],
    "Westlands": ["Westlands", "Parklands", "Muthangari", "Spring Valley"],
    "Lavington": ["Lavington Green", "Valley Arcade", "King'ara Road"],
    "Runda": ["New Runda", "Old Runda", "Runda Estate", "Membley"],
    "Mombasa": ["Nyali", "Bamburi", "Shanzu", "Kizingo", "Tudor"],
    "Kisumu": ["Milimani", "Kondele", "Riat Hills", "Mamboleo"],
    "Nakuru": ["Milimani", "London", "Section 58", "Lanet"],
    "Eldoret": ["Elgon View", "Kapsoya", "Langas", "Pioneer"],
}

PROPERTY_TEMPLATES = [
    # (city, neighborhood, ptype, ltype, beds, baths, sqft, price, title, description)
    # ── Nairobi Premium ──
    ("Nairobi", "Kileleshwa", PropertyType.residential, ListingType.sale, 4, 3, 3200, 42000000,
     "Luxury 4-Bedroom Villa in Kileleshwa with Pool",
     "Stunning contemporary villa in the heart of Kileleshwa. Features include a private swimming pool, manicured garden, modern kitchen with granite countertops, en-suite bathrooms, staff quarters, and 24-hour security. Walking distance to Yaya Centre and top international schools."),
    ("Nairobi", "Spring Valley", PropertyType.residential, ListingType.sale, 5, 4, 4500, 78000000,
     "Executive 5-Bedroom Mansion in Spring Valley",
     "Magnificent family home set on half an acre in one of Nairobi's most prestigious neighborhoods. Features a grand foyer, formal living and dining rooms, family room, gourmet kitchen, home office, swimming pool, mature garden, and guest cottage. Perfect for diplomatic or executive family."),
    ("Nairobi", "Upper Hill", PropertyType.commercial, ListingType.sale, None, 3, 8000, 95000000,
     "Prime Commercial Building in Upper Hill — Grade A Offices",
     "Brand new Grade A office building in Nairobi's financial district. Column-free floor plates of 8,000 sqft, panoramic city views, 3 high-speed elevators, backup generator, borehole, rooftop terrace, and secure basement parking for 50+ cars. Currently 60% pre-leased to blue-chip tenants."),
    ("Kilimani", "Kilimani", PropertyType.residential, ListingType.rent, 2, 1, 950, 4500,
     "Stylish 2-Bedroom Apartment in Kilimani — Furnished",
     "Beautifully furnished 2-bedroom apartment in the vibrant Kilimani neighborhood. Open-plan living with modern finishes, fully equipped kitchen, balcony with city views, gym access, and secure parking. Walking distance to restaurants, cafes, and Yaya Centre. Rent includes service charge."),
    ("Karen", "Karen", PropertyType.residential, ListingType.sale, 4, 4, 3800, 65000000,
     "Elegant 4-Bedroom Country Home in Karen with Acre Garden",
     "Charming country-style home set on 1.5 acres of lush gardens in Karen. Features exposed beam ceilings, fireplace, wrap-around veranda, swimming pool, tennis court, mature trees, organic vegetable garden, and staff quarters. Perfect for nature lovers seeking tranquility within the city."),
    # ── Westlands Area ──
    ("Westlands", "Westlands", PropertyType.residential, ListingType.rent, 3, 2, 1500, 6500,
     "Modern 3-Bedroom Apartment in Westlands — Near Sarit Centre",
     "Contemporary unfurnished apartment in the heart of Westlands. Spacious rooms with floor-to-ceiling windows, modern kitchen, en-suite master, ample storage, and dedicated parking. 5-minute walk to Sarit Centre, banks, and restaurants. 24-hour security and backup water supply."),
    ("Westlands", "Parklands", PropertyType.residential, ListingType.rent, 1, 1, 600, 2500,
     "Cozy 1-Bedroom Bedsitter in Parklands — Ideal for Students/Young Pros",
     "Well-maintained bedsitter in a secure apartment block near Aga Khan University and University of Nairobi School of Law. Built-in wardrobes, modern bathroom, shared rooftop, and reliable water supply. Walking distance to matatu stages and quick access to Waiyaki Way."),
    ("Westlands", "Muthangari", PropertyType.residential, ListingType.sale, 3, 2, 2000, 28000000,
     "Charming 3-Bedroom Townhouse in Muthangari with Garden",
     "Delightful townhouse in a gated community of only 8 units. Features a private garden, open-plan living/dining, modern kitchen, en-suite master, guest cloakroom, and secure parking for 2 cars. Well-managed compound with swimming pool and gym. Close to Westlands and Lavington."),
    # ── Lavington ──
    ("Lavington", "Lavington Green", PropertyType.residential, ListingType.sale, 4, 3, 2800, 38000000,
     "Spacious Family Home in Lavington Green — 4 Bedrooms",
     "Beautiful family residence in the leafy suburbs of Lavington. Double-volume living room, separate dining, family/TV room, modern kitchen with pantry, en-suite bedrooms, guest wing, laundry, staff quarters, mature garden, and borehole. Close to Lavington Mall and Braeburn School."),
    ("Lavington", "King'ara Road", PropertyType.residential, ListingType.rent, 3, 2, 1600, 5500,
     "Newly Renovated 3-Bedroom House — King'ara Road, Lavington",
     "Recently renovated house in a quiet cul-de-sac off King'ara Road. Modern finishes throughout, large living room opening to a private garden, fully fitted kitchen, 2 parking spaces, and 24-hour security. Ideal for a young family seeking space, comfort, and excellent schools nearby."),
    # ── Runda ──
    ("Runda", "New Runda", PropertyType.residential, ListingType.sale, 5, 5, 5000, 85000000,
     "Premium 5-Bedroom Villa in New Runda — Resort-Style Living",
     "Exceptional villa in the exclusive New Runda estate. This architectural masterpiece features a grand entrance, double-volume living areas, home cinema, wine cellar, study/library, infinity pool, landscaped tropical garden, staff quarters, and a 4-car garage. Secure estate with country club amenities."),
    ("Runda", "Runda Estate", PropertyType.residential, ListingType.rent, 4, 3, 2800, 8000,
     "Executive 4-Bedroom Furnished Home in Runda Estate",
     "Luxuriously furnished home available for long-term rental in Runda. All bedrooms en-suite, modern kitchen, spacious living and dining, home office, private garden, swimming pool, borehole, and generator. Ideal for expatriate family or corporate executive. Rent negotiable for 2+ year lease."),
    # ── Mombasa ──
    ("Mombasa", "Nyali", PropertyType.residential, ListingType.sale, 4, 3, 2600, 32000000,
     "Beachside 4-Bedroom Villa in Nyali — Ocean Breeze & Tropical Garden",
     "Stunning coastal villa minutes from Nyali Beach. Open-plan living with Swahili-style architecture, high makuti ceilings, ceiling fans throughout, tropical garden with coconut palms, swimming pool, rooftop terrace with ocean views, and staff quarters. Perfect holiday home or boutique Airbnb investment."),
    ("Mombasa", "Bamburi", PropertyType.residential, ListingType.rent, 2, 1, 800, 2500,
     "2-Bedroom Beach Apartment in Bamburi — Walk to the Beach",
     "Bright and airy apartment in a secure beachfront complex in Bamburi. Furnished with coastal decor, ocean-view balcony, shared swimming pool, generator, and 24-hour security. Walking distance to Bamburi Beach and close to Sarova Whitesands. Ideal for remote workers seeking coastal lifestyle."),
    ("Mombasa", "Nyali", PropertyType.commercial, ListingType.sale, None, 2, 3500, 28000000,
     "Thriving Beachfront Restaurant & Bar in Nyali — Turnkey Business",
     "Established restaurant and bar on Nyali's beachfront strip. Seats 120 guests, fully equipped commercial kitchen, liquor license, outdoor terrace with ocean views, ample parking, and loyal clientele. Consistently profitable with strong weekend trade. Staff of 15 included in transition."),
    ("Mombasa", "Shanzu", PropertyType.land, ListingType.sale, None, None, 87000, 12500000,
     "Prime Beachfront Plot in Shanzu — 2 Acres Development Land",
     "Rare opportunity: 2 acres of prime beachfront land in Shanzu, Mombasa. Clean title deed, ready for immediate development. Approved for mixed-use (hotel, residential, commercial). Located between Sarova Whitesands and Pride Inn Paradise. Survey plan and change-of-user approval available."),
    # ── Kisumu ──
    ("Kisumu", "Milimani", PropertyType.residential, ListingType.sale, 4, 3, 2200, 18000000,
     "Lakeside 4-Bedroom Home in Milimani, Kisumu — Lake View",
     "Elegant family home in Kisumu's premier Milimani estate. Elevated position with partial Lake Victoria views, modern kitchen, en-suite bedrooms, mature garden with fruit trees, borehole, and staff quarters. Minutes from Kisumu International Airport, Impala Sanctuary, and Kisumu Yacht Club."),
    ("Kisumu", "Riat Hills", PropertyType.residential, ListingType.rent, 3, 2, 1400, 2500,
     "Modern 3-Bedroom Apartment in Riat Hills — Panoramic Lake Views",
     "Brand new apartment in the up-and-coming Riat Hills area. Stunning panoramic views of Lake Victoria from the balcony and all living areas. Modern finishes, fitted kitchen, secure parking, and backup water. Close to United Mall, Kibuye Market, and the new Kisumu-Kakamega Highway."),
    ("Kisumu", "Mamboleo", PropertyType.land, ListingType.sale, None, None, 130000, 4800000,
     "3-Acre Agricultural/Residential Plot in Mamboleo — Ready to Build",
     "Well-located plot near the Northern Bypass in Mamboleo, Kisumu. Gentle slope with good drainage, access road already tarmacked, electricity and water nearby. Suitable for residential development or small-scale farming. Area is rapidly appreciating — excellent long-term investment."),
    # ── Nakuru ──
    ("Nakuru", "Milimani", PropertyType.residential, ListingType.sale, 3, 2, 1600, 12500000,
     "Beautiful 3-Bedroom Bungalow in Milimani, Nakuru",
     "Well-maintained bungalow in Nakuru's most desirable neighborhood. Large living room with fireplace, separate dining, modern kitchen, en-suite master, mature garden with indigenous trees, garage, and staff quarters. Close to Lake Nakuru National Park gate and Nakuru Golf Club."),
    ("Nakuru", "Section 58", PropertyType.residential, ListingType.rent, 2, 1, 750, 1800,
     "Affordable 2-Bedroom Apartment in Section 58, Nakuru",
     "Clean and secure apartment block in convenient Section 58 location. Spacious rooms, tiled floors, built-in wardrobes, reliable water supply, and secure compound. Walking distance to Nakuru town center and public transport. Ideal for young professionals or small family."),
    ("Nakuru", "London", PropertyType.land, ListingType.sale, None, None, 22000, 2800000,
     "Half-Acre Residential Plot in London Estate, Nakuru",
     "Prime residential plot in the fast-growing London Estate. Level terrain, tarmac road access, electricity on site, water connection available. Neighborhood has quality homes and good security. Excellent investment — Nakuru is Kenya's fastest-growing city after Nairobi."),
    # ── Eldoret ──
    ("Eldoret", "Elgon View", PropertyType.residential, ListingType.sale, 4, 3, 2400, 15000000,
     "Spacious 4-Bedroom Home in Elgon View — Eldoret's Best Address",
     "Quality-built family home in the prestigious Elgon View estate. Panoramic views of the Cherengani Hills, modern kitchen, en-suite master, 2 living rooms, home office, mature garden, borehole, and staff quarters. Close to Moi Teaching and Referral Hospital, schools, and Eldoret International Airport."),
    ("Eldoret", "Kapsoya", PropertyType.residential, ListingType.rent, 2, 1, 700, 1500,
     "Modern 2-Bedroom in Kapsoya — Close to Moi University",
     "Newly built apartment block in Kapsoya area. Tiled throughout, fitted kitchen, secure compound with parking, borehole water supply. Popular with Moi University staff and students. Quick access to Eldoret town and Eldoret Airport. Long-term leases preferred (6+ months)."),
    # ── Thika/Kiambu ──
    ("Thika", "Thika", PropertyType.residential, ListingType.sale, 3, 2, 1400, 8500000,
     "3-Bedroom Modern Bungalow in Thika — Great for Families",
     "Contemporary bungalow in a quiet Thika estate. Open-plan living, modern kitchen with island, en-suite master, landscaped garden, and secure parking. Close to Thika Road Mall, Del Monte, and good schools. Easy commute to Nairobi via Thika Superhighway (45 minutes off-peak)."),
    ("Kiambu", "Kiambu", PropertyType.land, ListingType.sale, None, None, 44000, 5500000,
     "1-Acre Farm Land in Kiambu — Fertile Red Soil with River Frontage",
     "Excellent agricultural land 30 minutes from Nairobi. Fertile red volcanic soil ideal for horticulture, dairy farming, or poultry. Perennial river along boundary, electricity nearby, access road maintained by county. Area produces tea, coffee, and vegetables for Nairobi markets."),
    ("Ruaka", "Ruaka", PropertyType.residential, ListingType.rent, 1, 1, 500, 1300,
     "Compact Studio Apartment in Ruaka — Near Two Rivers Mall",
     "Efficient studio apartment in a modern block near Two Rivers Mall. Open-plan layout maximizing space, built-in kitchenette, modern bathroom, high-speed fiber internet-ready, and secure compound with CCTV. Perfect for young professional working in Gigiri or Westlands (15-minute commute via Northern Bypass)."),
    ("Limuru", "Limuru", PropertyType.land, ListingType.sale, None, None, 90000, 7500000,
     "2-Acre Tea-Growing Land in Limuru — Cool Climate, Scenic Views",
     "Beautiful 2-acre parcel in the Limuru highlands with established tea bushes and mature trees. Cool climate, clean air, scenic views of the Aberdare Range. Suitable for residential development, weekend retreat, or continued tea farming. Accessible via Limuru Road (Nairobi-Nakuru Highway)."),
    # ── Kitengela/Ngong/Rongai ──
    ("Kitengela", "Kitengela", PropertyType.residential, ListingType.sale, 3, 2, 1500, 6500000,
     "Affordable 3-Bedroom Maisonette in Kitengela with Own Compound",
     "Value-packed maisonette on own plot in Kitengela's growing residential zone. Spacious rooms, modern finishes, private compound with parking for 3 cars, water storage, and septic system. 30 minutes to JKIA and 45 minutes to Nairobi CBD. Area has good schools, hospitals, and shopping centers."),
    ("Ngong", "Ngong", PropertyType.residential, ListingType.rent, 2, 1, 850, 1600,
     "2-Bedroom House in Ngong — Ngong Hills Views, Clean Air",
     "Charming house with breathtaking views of the Ngong Hills. Large windows flooding the space with natural light, fireplace in the living room, modern kitchen, garden with fruit trees, and secure parking. Fresh air, quiet neighborhood, 30-minute drive to Karen and 45 minutes to Nairobi CBD."),
    ("Rongai", "Rongai", PropertyType.residential, ListingType.rent, 3, 2, 1200, 2000,
     "Family-Friendly 3-Bedroom House in Rongai — Near Catholic University",
     "Comfortable family house in a secure gated estate near Catholic University of Eastern Africa. Modern finishes, spacious living/dining, fitted kitchen, en-suite master, children's playground in estate, reliable water, and 24-hour security. Great value for families seeking space and affordability."),
    ("Kitengela", "Kitengela", PropertyType.land, ListingType.sale, None, None, 22000, 1800000,
     "Half-Acre Plot in Kitengela — Near Namanga Road, Ready Title Deed",
     "Well-priced residential plot in a fast-growing section of Kitengela. Clean title deed, surveyed with beacons, access road, and electricity nearby. The area is developing rapidly with new homes and businesses. Buy now while prices are still affordable — excellent capital appreciation potential."),
    # ── Athi River / Machakos ──
    ("Athi River", "Athi River", PropertyType.land, ListingType.sale, None, None, 200000, 15000000,
     "5-Acre Industrial Plot in Athi River — EPZ Zone, Highway Frontage",
     "Prime industrial land in Athi River's Export Processing Zone. 200 meters of Mombasa Road frontage, level terrain, electricity on site, borehole water, and approved for warehousing, manufacturing, or logistics park. Close to JKIA (20 minutes) and Inland Container Depot. Environmental impact assessment already done."),
    ("Athi River", "Athi River", PropertyType.residential, ListingType.rent, 2, 1, 800, 1200,
     "Budget-Friendly 2-Bedroom in Athi River — Near Daystar University",
     "Clean and secure apartment in Athi River's student-friendly area. Modern finishes, tiled floors, reliable water, secure parking, and close to public transport. Popular with Daystar University students, EPZ workers, and young families. 20-minute drive to JKIA via the Eastern Bypass."),
    # ── Ruiru ──
    ("Ruiru", "Ruiru", PropertyType.residential, ListingType.sale, 2, 1, 700, 3500000,
     "2-Bedroom Starter Home in Ruiru — Affordable First Home",
     "Perfect starter home for a young family or first-time buyer. Modern bungalow with open-plan living, fitted kitchen, en-suite master, private garden, and secure parking. Ruiru is booming with new infrastructure, shopping malls, and easy Thika Superhighway access. 30 minutes to Nairobi CBD off-peak."),
    # ── More Nairobi ──
    ("Nairobi", "Hurlingham", PropertyType.residential, ListingType.rent, 2, 2, 1100, 5000,
     "Fully Furnished 2-Bedroom in Hurlingham — Corporate Let",
     "Executive furnished apartment in Hurlingham, ideal for corporate or diplomatic tenants. Modern decor, fully equipped kitchen, DSTV, fast WiFi, backup generator, swimming pool, gym, and secure underground parking. Walking distance to Yaya Centre, Prestige Plaza, and several embassies. Short-term (3+ months) available."),
    ("Nairobi", "Ngara", PropertyType.commercial, ListingType.rent, None, 1, 2500, 3500,
     "Ground-Floor Retail Space in Ngara — High Foot Traffic",
     "Prime ground-floor commercial space on a busy Ngara road. Previously a successful electronics shop. Open-plan layout, high ceilings, customer toilet, storage room, roller shutter, and back entrance for deliveries. Heavy pedestrian traffic from nearby bus stages, schools, and residential estates. Ideal for retail, pharmacy, or supermarket."),
    ("Nairobi", "Spring Valley", PropertyType.residential, ListingType.rent, 5, 4, 3500, 12000,
     "Diplomatic Residence in Spring Valley — 5 Bedrooms, Pool, Garden",
     "Prestigious furnished residence in the diplomatic belt of Spring Valley. Grand living and dining rooms, study/library, gourmet kitchen, all en-suite bedrooms, staff quarters for 4, swimming pool, mature garden, borehole, generator, electric fence, and 24-hour guard. Near UN headquarters and international schools."),
    # ── Additional premium listings ──
    ("Kileleshwa", "Kileleshwa", PropertyType.residential, ListingType.sale, 3, 2, 1800, 22000000,
     "Newly Built 3-Bedroom Apartment in Kileleshwa — Rooftop Terrace",
     "Brand new apartment in a boutique development of only 6 units. Open-plan layout with floor-to-ceiling windows, modern Italian kitchen, en-suite bedrooms, private rooftop terrace with BBQ area, secure parking, gym, and panoramic Nairobi skyline views. Close to Lavington Mall, Junction, and major road networks."),
    ("Karen", "Karen", PropertyType.land, ListingType.sale, None, None, 220000, 45000000,
     "5-Acre Prime Land in Karen — Ideal for Gated Community Development",
     "Exceptional undeveloped land in the heart of Karen, 2km from Karen Shopping Centre. Mature indigenous trees, gentle slope with good drainage, borehole already drilled, electricity on site, and direct tarmac road access. Approved for subdivision into half-acre plots or gated community. Title deed in order."),
    # ── Short Stay / Airbnb ──
    ("Kilimani", "Kilimani", PropertyType.short_stay, ListingType.rent, 1, 1, 500, 300,
     "Luxury Studio Airbnb in Kilimani — Daily/Weekly Rates from KES 3,000/night",
     "Professionally managed short-stay studio in the heart of Kilimani. Hotel-quality furnishings, fully equipped kitchenette, fast WiFi, smart TV with Netflix, and weekly housekeeping. Building has rooftop pool, gym, and 24-hour security. Walk to Yaya Centre. Currently generates KES 120K/month. Fully licensed."),
    ("Mombasa", "Nyali", PropertyType.short_stay, ListingType.rent, 3, 2, 1400, 800,
     "Beachfront Holiday Villa in Nyali — Amazing Reviews, Turnkey Airbnb",
     "Beautifully decorated 3-bedroom holiday villa steps from Nyali Beach. Private pool, tropical garden, outdoor dining area, fully equipped kitchen, and dedicated housekeeper. Consistently Superhost-rated with 4.9 stars (120+ reviews). Turnkey operation — all bookings and management systems in place."),
    # ── Commercial additions ──
    ("Upper Hill", "Upper Hill", PropertyType.commercial, ListingType.lease, None, 4, 12000, 12000,
     "Full-Floor Office Space in Upper Hill — Ready for Immediate Occupancy",
     "Entire floor (12,000 sqft) in a premium Grade A building in Upper Hill. Raised floors, suspended ceiling, central air conditioning, backup power, high-speed elevators, basement parking, and professional building management. Neighbors include PwC, World Bank, and major banks. Available unfurnished or fully fitted."),
    ("Westlands", "Westlands", PropertyType.commercial, ListingType.rent, None, 2, 800, 4500,
     "Modern Co-Working/Office Space in Westlands — Flexible Terms",
     "Turnkey office space in a converted warehouse in Westlands. Exposed brick and steel aesthetic, high ceilings, fiber internet, meeting rooms, breakout areas, kitchen, and 24/7 access. Hot desks from KES 15,000/month, private offices from KES 45,000/month. Vibrant community of startups, freelancers, and creatives."),
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

COUNTIES = list(set(c[1] for c in CITIES))


async def seed():
    await create_tables()

    async with AsyncSessionLocal() as db:
        r = await db.execute(select(func.count(User.id)))
        if r.scalar_one() > 1:
            print("Database already seeded. Dropping and recreating...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await create_tables()
            print("Tables recreated.")

        now = datetime.now(timezone.utc)

        # ─── Users (15) ─────────────────────────────────────────────────────
        users_data = [
            # Admins
            {"email": "admin@vestra.co.ke", "full_name": "Admin User", "role": UserRole.super_admin, "is_verified": True, "is_active": True},
            # Agents
            {"email": "jane.muthoni@email.com", "full_name": "Jane Muthoni", "role": UserRole.agent, "is_verified": True, "is_active": True},
            {"email": "david.kamau@email.com", "full_name": "David Kamau", "role": UserRole.agent, "is_verified": True, "is_active": True},
            {"email": "amara.chioma@email.com", "full_name": "Amara Chioma", "role": UserRole.agent, "is_verified": True, "is_active": True},
            # Sellers
            {"email": "peter.omondi@email.com", "full_name": "Peter Omondi", "role": UserRole.seller, "is_verified": True, "is_active": True},
            {"email": "faith.wanjiku@email.com", "full_name": "Faith Wanjiku", "role": UserRole.seller, "is_verified": True, "is_active": True},
            {"email": "kofi.abebe@email.com", "full_name": "Kofi Abebe", "role": UserRole.seller, "is_verified": True, "is_active": True},
            # Landlords
            {"email": "grace.akinyi@email.com", "full_name": "Grace Akinyi", "role": UserRole.landlord, "is_verified": True, "is_active": True},
            {"email": "emmanuel.mwangi@email.com", "full_name": "Emmanuel Mwangi", "role": UserRole.landlord, "is_verified": True, "is_active": True},
            # Buyers
            {"email": "samuel.njoroge@email.com", "full_name": "Samuel Njoroge", "role": UserRole.buyer, "is_verified": False, "is_active": True},
            {"email": "mary.wekesa@email.com", "full_name": "Mary Wekesa", "role": UserRole.buyer, "is_verified": False, "is_active": True},
            {"email": "fatima.hassan@email.com", "full_name": "Fatima Hassan", "role": UserRole.buyer, "is_verified": True, "is_active": True},
            {"email": "john.kariuki@email.com", "full_name": "John Kariuki", "role": UserRole.buyer, "is_verified": False, "is_active": True},
            {"email": "aisha.juma@email.com", "full_name": "Aisha Juma", "role": UserRole.buyer, "is_verified": True, "is_active": True},
            {"email": "brian.otieno@email.com", "full_name": "Brian Otieno", "role": UserRole.buyer, "is_verified": False, "is_active": True},
        ]

        users = []
        for u in users_data:
            days_ago = random.randint(10, 300)
            user = User(
                email=u["email"],
                phone=f"+2547{random.randint(10000000, 99999999)}",
                full_name=u["full_name"],
                hashed_password=await get_password_hash(u.get("password", "demo1234")),
                role=u["role"],
                is_verified=u["is_verified"],
                is_active=u["is_active"],
                location=random.choice(list(NEIGHBORHOODS.keys())),
                created_at=now - timedelta(days=days_ago),
            )
            db.add(user)
            users.append(user)

        await db.flush()

        # Agent profiles
        for user in users:
            if user.role == UserRole.agent:
                profile = AgentProfile(
                    user_id=user.id,
                    agency_name=f"{user.full_name} Realty",
                    license_number=f"EA-{random.randint(1000,9999)}",
                    years_experience=random.randint(3, 20),
                    specialization=random.sample(["residential", "commercial", "land", "luxury"], random.randint(1, 3)),
                    badge_level=random.choice(["gold", "platinum", "silver"]),
                    badge_expires_at=now + timedelta(days=365),
                    total_listings=random.randint(10, 100),
                    successful_deals=random.randint(5, 50),
                    rating=round(random.uniform(4.0, 5.0), 1),
                    subscription_tier="pro",
                    subscription_expires_at=now + timedelta(days=180),
                )
                db.add(profile)

        await db.flush()

        # ─── Properties (50+) ────────────────────────────────────────────────
        properties = []
        seller_ids = [u.id for u in users if u.role in (UserRole.seller, UserRole.agent, UserRole.landlord)]

        for i, spec in enumerate(PROPERTY_TEMPLATES):
            city, neighborhood, ptype, ltype, beds, baths, sqft, price, title, description = spec

            # Set status — mostly active, some pending, a few sold
            if i < 40:
                status = PropertyStatus.active
            elif i < 45:
                status = PropertyStatus.pending_review
            elif i < 48:
                status = PropertyStatus.sold
            else:
                status = PropertyStatus.draft

            trust = round(random.uniform(55, 98), 1) if status == PropertyStatus.active else None
            is_verified = status == PropertyStatus.active and trust and trust > 60

            prop = Property(
                owner_id=random.choice(seller_ids),
                title=title,
                description=description,
                property_type=ptype,
                listing_type=ltype,
                status=status,
                address=f"{random.randint(1, 500)} {neighborhood} Road",
                city=city,
                county=dict(CITIES).get(city, "Nairobi"),
                country="Kenya",
                price=float(price),
                currency="KES",
                price_negotiable=random.choice([True, True, False]),
                bedrooms=beds,
                bathrooms=baths,
                size_sqft=float(sqft),
                year_built=random.randint(2008, 2026),
                amenities=random.choice(AMENITIES_POOL),
                images=[],
                trust_score=trust,
                is_verified=is_verified,
                verification_badge=_badge(trust) if is_verified else None,
                views=random.randint(50, 5000),
                inquiries=random.randint(0, 45),
                created_at=now - timedelta(days=random.randint(1, 400)),
            )
            db.add(prop)
            properties.append(prop)

        await db.flush()

        # ─── Verifications & Documents ──────────────────────────────────────
        ai_results = [
            ("approve", 8, 92, "under", "high", "All documents verified. Clean title deed. Excellent investment."),
            ("approve", 12, 88, "fair", "high", "Minor KRA PIN discrepancy resolved. Property verified."),
            ("approve", 5, 95, "fair", "high", "Clean verification. All checks passed."),
            ("review", 28, 65, "over", "medium", "Price 20% above market. Request additional valuation report."),
            ("reject", 52, 32, "under", "low", "Title deed not in official registry. Possible fraud."),
            ("review", 18, 72, "fair", "medium", "Agent license expiring. ID scan quality poor."),
            ("approve", 10, 90, "fair", "high", "All clear. Good investment in growing area."),
            ("approve", 6, 94, "under", "high", "Below market price — excellent deal."),
            ("approve", 7, 91, "fair", "high", "Photos match satellite imagery. Documents verified."),
            ("review", 22, 68, "fair", "medium", "Land search shows minor encumbrance. Needs resolution."),
            ("approve", 4, 96, "fair", "high", "Perfect documentation. Platinum trust level."),
            ("approve", 9, 89, "fair", "high", "Verified with minor note on sale agreement date."),
        ]

        for i, prop in enumerate(properties[:min(len(properties), len(ai_results))]):
            rec, fraud, trust, price_rec, own_conf, summary = ai_results[i]
            st_map = {"approve": VerificationStatus.approved, "review": VerificationStatus.flagged, "reject": VerificationStatus.rejected}

            v = Verification(
                property_id=prop.id,
                user_id=prop.owner_id,
                requester_id=prop.owner_id,
                status=st_map[rec],
                fraud_risk_score=fraud,
                trust_score=trust,
                price_reasonableness=price_rec,
                ownership_confidence=own_conf,
                ai_recommendation=rec,
                document_flags=[],
                ai_summary=summary,
                ai_raw_response={"fraud": fraud, "trust": trust},
                created_at=prop.created_at + timedelta(days=random.randint(1, 5)),
            )
            db.add(v)

            # Add 1-4 documents per verified property
            for dt in random.sample(list(DocumentType), random.randint(1, 4)):
                doc = Document(
                    property_id=prop.id,
                    uploader_id=prop.owner_id,
                    document_type=dt,
                    file_name=f"{dt.value}_{prop.id}.pdf",
                    file_path=f"/uploads/docs/{prop.id}/{dt.value}.pdf",
                    file_size=random.randint(50000, 5000000),
                    mime_type="application/pdf",
                    is_verified=trust > 70,
                    created_at=prop.created_at + timedelta(hours=random.randint(1, 48)),
                )
                db.add(doc)

        # ─── Payments (30) ─────────────────────────────────────────────────
        purposes = list(PaymentPurpose)
        for i in range(30):
            ptype = random.choice(purposes)
            status = random.choices(
                [PaymentStatus.completed, PaymentStatus.completed, PaymentStatus.completed,
                 PaymentStatus.processing, PaymentStatus.failed],
                weights=[60, 20, 10, 5, 5]
            )[0]
            method = random.choice([PaymentMethod.mpesa, PaymentMethod.mpesa, PaymentMethod.mpesa, PaymentMethod.stripe])

            payment = Payment(
                user_id=random.choice(seller_ids + [u.id for u in users if u.role == UserRole.buyer]),
                amount=random.choice([500, 500, 1000, 5000, 5000, 10000, 25000, 50000]),
                currency="KES",
                method=method,
                purpose=ptype,
                status=status,
                phone_number=f"+2547{random.randint(10000000, 99999999)}",
                reference=f"VST-{random.randint(100000, 999999)}",
                description=f"Vestra {ptype.value.replace('_', ' ').title()}",
                payment_metadata={"item_id": random.randint(1, 50)},
                created_at=now - timedelta(days=random.randint(2, 200)),
            )
            if status == PaymentStatus.completed and method == PaymentMethod.mpesa:
                payment.mpesa_receipt_number = f"QK{random.randint(1000000, 9999999)}"
            db.add(payment)

        await db.commit()

        print()
        print("=" * 65)
        print("  🏠  VESTRA — Rich Demo Data Seeded Successfully!")
        print("=" * 65)
        print(f"  👤 Users:              {len(users)}")
        print(f"  🏘️  Properties:         {len(properties)}")
        print(f"  🔍 Verifications:      {len(ai_results)}")
        print(f"  💰 Payments:           30")
        print(f"  📄 Documents:          ~30-50")
        print()
        print("  🔑 Login Credentials (password: demo1234):")
        print(f"     Admin:       admin@vestra.co.ke")
        print(f"     Agent:       jane.muthoni@email.com")
        print(f"     Seller:      peter.omondi@email.com")
        print(f"     Buyer:       samuel.njoroge@email.com")
        print(f"     Landlord:    grace.akinyi@email.com")
        print()
        print("  🌐 URLs after startup:")
        print(f"     Frontend:    http://localhost:3000")
        print(f"     Backend API: http://localhost:8000/docs")
        print(f"     AI Search:   http://localhost:3000/market?ai=1")
        print("=" * 65)
        print()


def _badge(score):
    if not score: return None
    if score >= 90: return "platinum"
    if score >= 75: return "gold"
    if score >= 60: return "silver"
    return "bronze"


if __name__ == "__main__":
    asyncio.run(seed())

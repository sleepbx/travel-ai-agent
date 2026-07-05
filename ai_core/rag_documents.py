# rag_documents.py  –  Structured India travel knowledge base for RAG retrieval.
# Each entry produces 1-3 semantic chunks at the default 850-char chunk size.
# Facts are grounded in common travel knowledge; costs are indicative INR ranges.

india_travel_docs = {

    # ------------------------------------------------------------------ #
    #  INDIA OVERVIEW                                                      #
    # ------------------------------------------------------------------ #

    "India Travel Overview": """
India spans 29 states with climates ranging from Himalayan alpine to tropical coastal.
The best time to visit most of India is October to March when temperatures are moderate and skies are clear.
Monsoon season runs July to September; hill stations and Kerala are beautiful during rains but some roads flood.
April to June is hot and dry across the plains; Ladakh and Spiti open in summer and are ideal then.
India uses Indian Rupee (INR); ATMs are widespread in cities and most towns. UPI and cards are widely accepted.
SIM cards (Airtel, Jio) are cheap and provide good 4G coverage in cities; buy at the airport with your passport.
Tipping is appreciated but not mandatory: round up auto fares, tip hotel staff INR 50-100 per service.
Dress modestly when visiting temples and mosques: cover shoulders and knees, remove shoes at entrances.
""",

    "India Transport Overview": """
Domestic flights connect major cities cheaply when booked 3-4 weeks ahead; IndiGo and Air India Express offer budget fares.
Indian Railways is an excellent value for intercity travel; book on IRCTC at least 2 weeks ahead.
Train classes: Sleeper (cheapest, no AC), 3A (AC 3-tier, good value), 2A (AC 2-tier, comfortable), 1A (premium).
Rajdhani and Shatabdi express trains are faster and more comfortable but cost 2-3x more than regular mail trains.
Metro rail operates in Delhi, Mumbai, Bangalore, Hyderabad, Chennai, Kolkata, Kochi, Jaipur, and Ahmedabad.
Ola and Uber work in all major cities; fares are INR 80-200 for short city rides, cheaper than prepaid taxis.
Auto-rickshaws charge INR 30-150 for short hops; always ask for meter or negotiate before boarding.
Intercity AC buses by TSRTC, KSRTC, and private operators are comfortable and cheaper than trains on many routes.
""",

    "India Budget Guide": """
Budget travel in India is very affordable; backpackers can manage on INR 1,500-2,500 per person per day.
Mid-range travel with decent hotels, restaurant meals, and guided tours costs INR 4,000-8,000 per person per day.
Luxury travel at 5-star hotels with private tours runs INR 15,000-40,000 per person per day.
Budget accommodation: hostels INR 400-800, guesthouses INR 800-1,500, budget hotels INR 1,200-2,500 per night.
Mid-range hotels typically cost INR 2,500-6,000 per night; many include breakfast.
Street food meals cost INR 50-200; sit-down restaurant meals cost INR 250-600; upscale dining INR 800-2,000.
Attraction entry fees: most temples are free; major heritage sites (Taj Mahal) INR 50-1,100; museums INR 20-500.
Auto or metro for local transport costs INR 20-200 per trip; cab apps slightly higher but metered and safe.
""",

    # ------------------------------------------------------------------ #
    #  HYDERABAD                                                           #
    # ------------------------------------------------------------------ #

    "Hyderabad City Guide": """
Hyderabad, capital of Telangana, is famous for its biryani, the Charminar, and a booming IT sector.
Best time to visit is October to February; summers are very hot (40°C+) and monsoon brings flooding.
The city divides into Old City (south, historic) and New City (north, modern IT corridors).
Old City contains Charminar, Mecca Masjid, Laad Bazaar, Chowmahalla Palace, and Salar Jung Museum.
HITEC City and Gachibowli in the west are the IT hubs with good hotels, malls, and cafes.
Banjara Hills and Jubilee Hills are upscale residential areas with restaurants, bars, and boutique hotels.
Secunderabad is the twin city north of Hussain Sagar lake; major railway terminus for outbound trains.
The Hyderabad Metro covers HITEC City, Ameerpet, LB Nagar, and Miyapur; single ride costs INR 10-60.
""",

    "Hyderabad Food & Attractions": """
Hyderabadi biryani (dum-cooked mutton or chicken) is the city's signature dish; budget INR 200-600 per plate.
Shah Ghouse and Paradise are iconic biryani restaurants; Café Bahar is famous for Irani chai and Osmania biscuits.
Irani chai (sweet, strong) with Osmania biscuits at Old City tea houses costs INR 20-40.
Haleem is a slow-cooked meat and wheat stew; best during Ramadan at Old City restaurants for INR 150-300.
Charminar entry is free; climb to top for INR 25; visit early morning (7-9am) before crowds arrive.
Golconda Fort is a half-day trip (15 km west); entry INR 15 Indians, INR 200 foreigners; evening light show at 6:30pm.
Ramoji Film City is the world's largest film studio (25 km east); full-day entry INR 1,150-1,750.
Hussain Sagar lake offers boat rides to the Buddha statue island for INR 60-100 return.
Laad Bazaar near Charminar sells lac bangles, pearls, and Hyderabadi jewelry; bargain for 30% off listed price.
""",

    # ------------------------------------------------------------------ #
    #  BANGALORE (BENGALURU)                                               #
    # ------------------------------------------------------------------ #

    "Bangalore City Guide": """
Bangalore (officially Bengaluru), Karnataka's capital, is India's tech hub and known for its pleasant climate year-round.
Best time to visit is October to February; the city rarely exceeds 35°C and enjoys a cool breeze.
MG Road and Brigade Road are the main commercial and nightlife corridors with malls, pubs, and restaurants.
Koramangala and Indiranagar are trendy neighborhoods packed with cafes, restaurants, breweries, and boutiques.
Whitefield and Electronic City are IT corridors with business hotels; far from central attractions.
Cubbon Park (300 acres) and Lalbagh Botanical Gardens are green escapes in the city center.
Namma Metro (Purple and Green lines) covers key corridors; single ride INR 10-60; peak-hour traffic is severe.
Ola/Uber rides cost INR 80-300 for most city trips; auto rates are meter-based at INR 30 flagfall + INR 15/km.
""",

    "Bangalore Food & Nightlife": """
Bangalore has the best craft beer scene in India; Toit, Arbor Brewing, and Windmills are must-visit breweries.
Masala dosa, idli-vada, and filter coffee are the quintessential South Indian breakfast; budget INR 80-200.
Vidyarthi Bhavan and MTR (Mavalli Tiffin Room) in Basavanagudi serve classic Bangalore breakfasts since the 1920s.
The Church Street and MG Road area has everything from fine dining to craft beer pubs; evenings get lively.
Koramangala 5th Block has a dense cluster of mid-range restaurants and rooftop bars.
Street food: Darshinis (stand-up eateries) serve a meal for INR 50-100; widely distributed across the city.
Bangalore is a gateway to day trips: Mysore (3 hrs), Nandi Hills sunrise (60 km), Coorg coffee estates (5 hrs).
Traffic jams are severe 8-10am and 5-8pm; plan mornings to start by 7am or after 10am.
""",

    # ------------------------------------------------------------------ #
    #  MUMBAI                                                              #
    # ------------------------------------------------------------------ #

    "Mumbai City Guide": """
Mumbai, Maharashtra's capital, is India's financial and entertainment capital; it runs 24/7 and never sleeps.
Best time to visit is November to February; monsoon (June-September) brings heavy rain and flooding.
South Mumbai (Colaba, Fort, Marine Drive) has colonial landmarks, Gateway of India, and heritage hotels.
Bandra (west) is the bohemian suburb with cafes, sea-facing promenades, and Bollywood connections.
Juhu Beach in the north has street food stalls and occasional Bollywood celebrity sightings.
Dharavi, Asia's largest informal settlement, offers fascinating socioeconomic walking tours (INR 700-1,200).
Mumbai Suburban Railway (local trains) connects the city north-south; INR 10-60 per ride; extremely crowded at rush hour.
Mumbai Metro Line 1 covers Versova-Andheri-Ghatkopar; new lines are expanding; fares INR 10-40.
Prepaid taxis at airport cost INR 600-1,200 to South Mumbai; Ola/Uber are INR 400-900 depending on traffic.
""",

    "Mumbai Food & Attractions": """
Vada pav (spiced potato fritter in bread) is Mumbai's street food icon; costs INR 15-30 at roadside stalls.
Pav bhaji, bhel puri, and sev puri are staple street foods; best at Chowpatty Beach and Juhu Beach.
Leopold Cafe and Cafe Mondegar in Colaba are historic hang-outs; meals INR 400-800.
Seafood restaurants in Colaba and Bandra serve fresh pomfret, prawn, and surmai; budget INR 600-1,500.
Gateway of India is free to visit and iconic; arrive early (7-8am) to avoid tour groups.
Chhatrapati Shivaji Maharaj Terminus (CST) is a UNESCO World Heritage railway station worth visiting.
Elephanta Caves on an island near Gateway are carved rock temples; ferry INR 200 return, entry INR 40.
Marine Drive (Queen's Necklace) is a 3.6 km promenade best for sunset walks; free and always lively.
Dharavi slum tours run by Reality Tours start at INR 700; all proceeds go to local NGOs.
""",

    # ------------------------------------------------------------------ #
    #  DELHI & NCR                                                         #
    # ------------------------------------------------------------------ #

    "Delhi City Guide": """
New Delhi, India's capital, blends Mughal monuments, colonial architecture, and modern urban life.
Best time to visit is October to March; summers reach 45°C and winter mornings can have dense fog (December-January).
Old Delhi (Shahjahanabad) is the historic heart: Jama Masjid, Chandni Chowk, Red Fort, and spice market.
Connaught Place (CP) is the colonial commercial hub; Lutyens Delhi has embassies and government buildings.
South Delhi has affluent neighborhoods: Hauz Khas Village (art, cafes), Lodi Colony, and Saket malls.
Delhi Metro is extensive and affordable (INR 10-60); runs 5am to 11pm; the safest and fastest way to get around.
Ola/Uber operate city-wide; short hops INR 100-250; airport to city center INR 400-700 via Metro or cab.
Avoid solo exploring Chandni Chowk narrow lanes after dark; stick to main streets or join group walks.
""",

    "Delhi Food & Heritage Monuments": """
Old Delhi street food is among the best in India: parathas at Paranthe Wali Gali, jalebis at Dariba Kalan.
Karim's near Jama Masjid is a 100-year-old institution famous for mutton korma and seekh kebabs; meal INR 400-700.
Connaught Place cafes and restaurants range from INR 300 budget thalis to INR 1,500 fine dining.
Red Fort (Lal Qila) entry: INR 35 Indians, INR 500 foreigners; arrive at 9am; light and sound show at 7pm.
Qutub Minar complex entry INR 30 Indians, INR 500 foreigners; best in early morning light.
Humayun's Tomb entry INR 40 Indians, INR 600 foreigners; less crowded than Taj Mahal, equally impressive.
India Gate and Rashtrapati Bhavan are free; best at dusk; nearby Rajpath lawns are pleasant for a stroll.
Akshardham Temple is grand and free (camera not allowed inside); allow 3-4 hours including exhibitions.
Agra (Taj Mahal) is a day trip 200 km south; fastest by Gatimaan Express train (1.5 hrs, INR 750 each way).
""",

    # ------------------------------------------------------------------ #
    #  GOA                                                                 #
    # ------------------------------------------------------------------ #

    "Goa Travel Guide": """
Goa, India's smallest state, is famous for beaches, seafood, Portuguese heritage, and vibrant nightlife.
Best time to visit is November to February; crowds peak at Christmas and New Year.
Monsoon (June-September) closes most beach shacks but the landscape turns lush; hotel rates drop 50-70%.
North Goa (Calangute, Baga, Anjuna, Vagator) is livelier with beach clubs, night markets, and parties.
South Goa (Palolem, Agonda, Colva) is quieter, cleaner, and more family-friendly.
Panjim (Panaji) is the state capital with Portuguese-style Latin Quarter (Fontainhas), cafes, and casinos.
Renting a scooter is the best way to explore: INR 300-500/day from guesthouses; international license needed.
Taxis in Goa are expensive (no Ola/Uber); negotiate fixed fares upfront; airport to North Goa costs INR 700-1,200.
""",

    "Goa Food & Beach Life": """
Goa's signature dishes: fish curry rice (basic daily meal, INR 150-250), prawn balchão, pork vindaloo.
Beach shacks serve grilled seafood platters for INR 400-1,000; kingfish, tiger prawns, and lobster are best fresh.
Curlies, Brittos, and Infantaria Pastry Shop are Baga beach institutions; sundowners at Curlies or Thalassa in Vagator.
Anjuna flea market (Wednesday) and Saturday Night Bazaar at Arpora sell clothing, jewelry, and handicrafts.
Basilica of Bom Jesus in Old Goa holds St. Francis Xavier's remains; entry free; 9am-6pm.
Dudhsagar Waterfall (60 km east) is spectacular June to November; jeep safari from Collem costs INR 2,500-3,500 per group.
Water sports at Baga and Calangute: parasailing INR 700, banana boat INR 300, jet ski INR 500 per 15 minutes.
Goa beach season: sunrise to 9am for quiet walks; 9am-1pm for swimming; 4-7pm for sunset and shacks.
""",

    # ------------------------------------------------------------------ #
    #  RAJASTHAN                                                           #
    # ------------------------------------------------------------------ #

    "Rajasthan Travel Guide": """
Rajasthan, the Land of Kings, has desert forts, royal palaces, colorful bazaars, and camel safaris.
Best time to visit is October to March; summers are extreme (45°C+); Pushkar Camel Fair is in November.
Jaipur (Pink City) is the state capital with Amber Fort, City Palace, Hawa Mahal, and Jantar Mantar observatory.
Jodhpur (Blue City) is known for the massive Mehrangarh Fort, blue-painted old city lanes, and Umaid Bhawan Palace.
Udaipur (City of Lakes) is the most romantic city with lake palaces, boat rides, and rooftop restaurants.
Jaisalmer (Golden City) is a living desert fort with camel safaris in the Sam Sand Dunes at sunset.
Pushkar has the sacred lake, Brahma Temple, and buzzing bazaars; great for spiritual travelers.
RSRTC buses connect all Rajasthan cities; overnight Volvo AC buses cost INR 300-700; trains are excellent too.
""",

    "Jaipur City Guide": """
Jaipur is the most visited city in Rajasthan; plan 2-3 days to cover the main sights comfortably.
Amber Fort (11 km north) is a must-visit; entry INR 100 Indians, INR 500 foreigners; go by 8am before tour buses.
Hawa Mahal (Wind Palace) is best photographed from across the street at sunrise for the best light; entry INR 50.
City Palace complex in Old City has a museum; entry INR 200-500 depending on sections; grand audience hall.
Jantar Mantar (UNESCO observatory) is next to City Palace; entry INR 50; allow 45 minutes.
Johri Bazaar and Tripolia Bazaar sell silver jewelry, gemstones, blue pottery, and tie-dye textiles.
Local transport: auto-rickshaws cost INR 30-100 for city hops; tuk-tuk day hire INR 700-1,200.
Rajasthani thali (dal baati churma, ker sangri, gatte ki sabzi) at a traditional restaurant costs INR 250-500.
""",

    # ------------------------------------------------------------------ #
    #  KERALA                                                              #
    # ------------------------------------------------------------------ #

    "Kerala Travel Guide": """
Kerala, God's Own Country, is known for backwaters, hill station tea estates, temples, and Ayurvedic wellness.
Best time to visit is October to February; monsoon (June-August) is lush but backwater boats may be limited.
Kochi (Cochin) is the major entry point; Fort Kochi has colonial architecture, Chinese fishing nets, and art galleries.
Alleppey (Alappuzha) is the backwater hub; overnight houseboat rides through canals cost INR 6,000-12,000 for two.
Munnar (130 km east of Kochi) is a tea estate hill station at 1,600m; cool at night; tea factory tours INR 50-100.
Kovalam beach (near Thiruvananthapuram) and Varkala are the main beach destinations with cliffside cafes.
Wayanad is a forested hill district with tribal heritage, waterfalls, and wildlife (elephants, leopards).
Kerala cuisine: sadya (banana leaf feast), fish molee, Kerala prawn curry, appam with stew; budget INR 200-500 per meal.
State buses (KSRTC) are reliable and cheap; houseboats must be booked 1-2 months ahead in peak season.
""",

    # ------------------------------------------------------------------ #
    #  VARANASI                                                            #
    # ------------------------------------------------------------------ #

    "Varanasi Travel Guide": """
Varanasi (Kashi/Benares) is one of the world's oldest living cities and Hinduism's holiest pilgrimage site.
Best time: October to March; April-June is extremely hot; monsoon brings Ganga flooding.
The 84 ghats (river steps) stretch 6.5 km along the Ganges; Dashashwamedh Ghat is the most sacred.
Ganga Aarti at Dashashwamedh Ghat at sunset (6-7pm) is mesmerizing; arrive 30 minutes early for good spots.
Dawn boat ride on the Ganga to see the ghats at sunrise is essential; hire a wooden boat for INR 200-500.
Manikarnika Ghat is the main cremation ghat; observe respectfully, no photography, dress modestly.
Kashi Vishwanath Temple (Shiva) is the city's most sacred temple; rebuilt behind the original by Marathas.
Sarnath (10 km north) is where Buddha gave his first sermon; Dhamek Stupa and museum worth a half-day trip.
Lassi shops in Vishwanath Gali sell thick clay-pot lassi for INR 60-100; famous morning ritual.
Ghats are best explored on foot; the narrow lanes (galis) are pedestrian only; expect cows and pilgrims.
""",

    # ------------------------------------------------------------------ #
    #  SOUTH INDIA OVERVIEW                                                #
    # ------------------------------------------------------------------ #

    "South India Travel Guide": """
South India covers Tamil Nadu, Kerala, Karnataka, Andhra Pradesh, and Telangana; best visited October to March.
The region is known for Dravidian temple architecture, classical dance (Bharatanatyam), silk, and spiced cuisine.
Tamil Nadu has the grandest temples: Madurai Meenakshi, Thanjavur Brihadeeswara, Chidambaram Nataraja.
Andhra Pradesh is known for spicy cuisine, Tirupati temple (the world's richest and most visited), and rich silk.
Karnataka blends Bangalore tech culture, Mysore palace heritage, Hampi ruins (UNESCO), and Coorg coffee.
Pondicherry (Puducherry) is a former French colony with colonial streets, ashrams, and tranquil beaches.
South Indian thali meals at local hotels (not restaurants) cost INR 80-200 and are incredibly filling.
Filter coffee served in tumbler-and-davara sets is a cultural ritual; find it at Darshinis and Brahmin cafes.
Chennai is a major transport hub with a busy international airport, good budget hotels, and Marina Beach.
""",

    "Chennai City Guide": """
Chennai, Tamil Nadu's capital, is a gateway to South India with colonial heritage, temples, and Tamil culture.
Best time: November to February; Chennai is hot and humid most of the year; cyclones occasionally in November.
Marina Beach is one of the world's longest beaches (13 km); sunrise walks are popular; swimming is dangerous.
Kapaleeshwarar Temple in Mylapore is a classic Dravidian gopuram temple; busy during morning puja at 6am.
T. Nagar is the shopping district for silk sarees, gold jewelry, and textiles; Pondy Bazaar for street shopping.
Egmore and Central are the hotel and railway hub areas; reasonably priced accommodation near transit.
Chennai Metro covers key routes; auto fares start at INR 30 (meter) or negotiate; Ola/Uber are widely used.
Filter coffee and idli-sambar breakfast at Saravana Bhavan (chain) or Murugan Idli Shop is INR 80-150.
Day trips: Mahabalipuram shore temples (60 km, UNESCO) and Kanchipuram silk city (75 km) are popular.
""",

    "Kolkata City Guide": """
Kolkata, West Bengal's capital, is India's cultural capital known for literature, art, football, and street food.
Best time: October to February; pre-monsoon (April-May) is extremely hot; Durga Puja in October is spectacular.
Victoria Memorial is a must-visit colonial monument (entry INR 30 Indians, INR 200 foreigners); beautiful gardens.
Howrah Bridge is iconic and best photographed at dawn; take a local ferry (INR 5) across the Hooghly river.
Park Street is the restaurant and café strip; New Market area has backpacker guesthouses and street food.
Kumartuli is the potters' quarter where Durga Puja clay idols are made year-round; free to walk through.
Kolkata Yellow Taxis are iconic; Ola/Uber also operate; Metro covers the north-south corridor cheaply.
Kolkata food: kathi rolls (egg and mutton wraps, INR 60-150), fish curry-rice, misti doi (sweet yogurt), rasgulla.
Arsalan and Peter Cat are famous restaurants; street food is exceptional and very affordable (INR 30-100).
""",

    # ------------------------------------------------------------------ #
    #  SAFETY & PRACTICAL TIPS                                            #
    # ------------------------------------------------------------------ #

    "India Safety & Practical Tips": """
India is generally safe for tourists; major tourist areas are well-patrolled and scams are mostly non-violent.
Common scams: fake guides at monuments, gem store touts, overpriced taxi from airport, tea ceremony overcharges.
Always book taxis via Ola or Uber apps to avoid fare disputes; show the route on your phone.
Drink only bottled or filtered water; street food is generally safe where turnover is high and food is cooked fresh.
Book trains on IRCTC website or app; use "tourist quota" allocation if regular quotas are full.
Travel insurance covering medical evacuation is strongly recommended; healthcare quality varies widely.
Bargaining is expected in markets and for auto-rickshaws without meters; start at 50% of quoted price.
Women travelers: dress conservatively outside beach/resort areas; use women-only metro compartments.
Emergency numbers: Police 100, Ambulance 108, Tourist Helpline 1800-11-1363 (toll-free).
SIM cards require passport, visa, and a local address; Jio and Airtel have the best coverage nationally.
""",

}

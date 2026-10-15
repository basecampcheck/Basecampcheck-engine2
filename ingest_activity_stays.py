import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing Supabase credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Format: (name, network, ext_id, state, country, lat, lon, url, golf, primary_act, ski, fish, boat, activities_list)
RAW_DATA = [
    # Alberta & BC (Home Turf & Mountain)
    ("Aspen Crossing Campground RV Resort", "independent", "aspen-crossing-ab", "AB", "CA", 50.7139, -113.3493, "https://www.aspencrossing.com/", False, "Camping", False, False, False, ["Camping", "Train Tours"]),
    ("Old MacDonald's Resort", "independent", "old-macdonalds-ab", "AB", "CA", 52.4208, -112.9644, "https://oldmacdonalds.com/", False, "Boating", False, True, True, ["Boating", "Beach Access", "Fishing"]),
    ("Kraay Family Farm", "independent", "kraay-family-farm-ab", "AB", "CA", 52.4831, -113.8152, "https://www.kraayfamilyfarm.com/", False, "Agri-Tourism", False, False, False, ["Farm Stay", "Family Attractions"]),
    ("Camp'n Class RV Park", "independent", "campn-class-stony-plain", "AB", "CA", 53.5303, -114.0041, "https://campnclass.com/", False, "RV Camping", False, False, False, ["RV Camping"]),
    ("Sir Winston Churchill Provincial Park", "alberta_parks", "sir-winston-churchill-ab", "AB", "CA", 54.8236, -111.9667, "https://albertaparks.ca/", False, "Boating", False, True, True, ["Boating", "Fishing", "Hiking"]),
    ("Writing-on-Stone Provincial Park", "alberta_parks", "writing-on-stone-ab", "AB", "CA", 49.0833, -111.6167, "https://albertaparks.ca/", False, "Hiking", False, False, True, ["Hiking", "Paddling"]),
    ("Mount Kidd RV Park", "independent", "mount-kidd-kananaskis", "AB", "CA", 50.8493, -115.1492, "https://www.mountkiddrv.com/", False, "Skiing", True, False, False, ["Skiing", "Hiking", "Biking", "Tennis"]),
    ("Dinosaur Provincial Park Campground", "alberta_parks", "dinosaur-pp-ab", "AB", "CA", 50.7570, -111.5170, "https://albertaparks.ca/", False, "Hiking", False, False, True, ["Hiking", "Fossil Hunting", "Paddling"]),
    ("Fairmont Hot Springs RV Resort", "independent", "fairmont-hot-springs-bc", "BC", "CA", 50.3347, -115.8617, "https://www.fairmonthotsprings.com/rv-resort/", True, "Golf", True, False, False, ["Golf", "Skiing", "Hot Springs"]),
    ("Whistler RV Park and Campground", "independent", "whistler-rv-park-bc", "BC", "CA", 50.0463, -123.0883, "https://whistlerrvpark.com/", False, "Skiing", True, False, False, ["Skiing", "Snowboarding", "Mountain Biking"]),
    ("Burnaby Cariboo RV Park", "independent", "burnaby-cariboo-rv", "BC", "CA", 49.2394, -122.9157, "https://www.bcrvpark.com/", False, "City Cycling", False, False, False, ["Cycling", "Hiking", "Sightseeing"]),
    # California (Golf, Fishing & Stargazing)
    ("The Springs at Borrego RV Resort & Golf", "independent", "springs-at-borrego-ca", "CA", "US", 33.2656, -116.3422, "https://www.springsatborrego.com/", True, "Golf", False, True, False, ["Golf", "Stargazing", "Fishing"]),
    ("Likely Place Golf & RV Resort", "independent", "likely-place-ca", "CA", "US", 41.2299, -120.5055, "https://likelyplace.com/", True, "Golf", False, True, True, ["Golf", "Fly Fishing", "ATVing", "Canoeing"]),
    ("The Lakes RV & Golf Resort", "independent", "lakes-rv-chowchilla-ca", "CA", "US", 37.1147, -120.2458, "https://thelakesrv.com/", True, "Golf", False, False, False, ["Golf", "National Park Touring"]),
    ("Rio Bend RV & Golf Resort", "independent", "rio-bend-el-centro-ca", "CA", "US", 32.7876, -115.6888, "https://www.riobendrvgolfresort.com/", True, "Golf", False, True, False, ["Golf", "Catch & Release Fishing"]),
    ("Camp Edison Huntington Lake", "independent", "camp-edison-ca", "CA", "US", 37.2341, -119.2223, "https://www.sce.com/campedison", False, "Boating", True, True, True, ["Boating", "Fishing", "Skiing"]),
    ("The Sands RV & Golf Resort", "independent", "sands-rv-desert-hot-springs", "CA", "US", 33.9312, -116.5186, "https://cal-am.com/resorts/the-sands/", True, "Golf", False, False, False, ["Golf", "Pickleball", "Hiking"]),
    # Colorado (Ski Basecamps)
    ("Tiger Run Resort", "independent", "tiger-run-breckenridge", "CO", "US", 39.5186, -106.0461, "http://www.tigerrunresort.com/", False, "Skiing", True, False, False, ["Skiing", "Indoor Aquatics", "Hiking"]),
    ("Sun Outdoors Rocky Mountains", "campspot", "sun-outdoors-rocky-mountains", "CO", "US", 40.0886, -105.9556, "https://www.sunoutdoors.com/colorado/sun-outdoors-rocky-mountains", False, "Skiing", True, True, True, ["Skiing", "Fly Fishing", "Kayaking"]),
    ("Steamboat Springs KOA Holiday", "koa", "steamboat-springs", "CO", "US", 40.5058, -106.8778, "https://koa.com/campgrounds/steamboat-springs/", False, "Skiing", True, False, False, ["Skiing", "Snowmobile Tours"]),
    ("Crested Butte RV Park", "independent", "crested-butte-rv", "CO", "US", 38.8697, -106.9878, "https://www.crestedbuttervpark.com/", False, "Skiing", True, False, False, ["Skiing", "Nordic Skiing"]),
    ("River Dance RV Resort", "independent", "river-dance-gypsum-co", "CO", "US", 39.6455, -106.9531, "https://www.riverdancervresort.com/", False, "Skiing", True, True, False, ["Skiing", "Riverfront Fishing"]),
    # US Regional Gems
    ("Moab Valley RV Resort", "campspot", "moab-valley-rv-resort", "UT", "US", 38.5956, -109.5758, "https://sunoutdoors.com/utah/moab-valley-rv-resort-campground", False, "Off-Roading", False, False, False, ["Off-Roading", "ATVing", "Hiking"]),
    ("Camp Gulf RV Resort", "independent", "camp-gulf-destin-fl", "FL", "US", 30.3792, -86.3688, "https://campgulf.com/", False, "Beach Access", False, True, True, ["Boating", "Beach Access", "Deep Sea Fishing"]),
    ("Boyne Mountain RV Resort", "independent", "boyne-mountain-mi", "MI", "US", 45.1633, -84.9317, "https://www.boynemountain.com/", True, "Skiing", True, False, False,

import os
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

K = ["name","provider_network","external_facility_id","state_province","country","latitude","longitude","booking_url","golf_on_site","primary_activity","ski_nearby","fishing","boating","activities"]

D = [
("Aspen Crossing RV Resort","independent","aspen-crossing-ab","AB","CA",50.7139,-113.3493,"https://aspencrossing.com",0,"Camping",0,0,0,["Camping"]),
("Old MacDonald's Resort","independent","old-macdonalds-ab","AB","CA",52.4208,-112.9644,"https://oldmacdonalds.com",0,"Boating",0,1,1,["Boating","Fishing"]),
("Kraay Family Farm","independent","kraay-family-farm-ab","AB","CA",52.4831,-113.8152,"https://kraayfamilyfarm.com",0,"Farm Stay",0,0,0,["Farm Stay"]),
("Wolf Creek Golf RV","independent","wolf-creek-golf-ab","AB","CA",52.6331,-113.5936,"https://wolfcreekgolf.com",1,"Golf",0,0,0,["Golf"]),
("Camp'n Class RV Park","independent","campn-class-stony-plain","AB","CA",53.5303,-114.0041,"https://campnclass.com",0,"Camping",0,0,0,["Camping"]),
("Sir Winston Churchill PP","alberta_parks","sir-winston-churchill-ab","AB","CA",54.8236,-111.9667,"https://albertaparks.ca",0,"Boating",0,1,1,["Boating","Fishing"]),
("Writing-on-Stone PP","alberta_parks","writing-on-stone-ab","AB","CA",49.0833,-111.6167,"https://albertaparks.ca",0,"Hiking",0,0,1,["Hiking","Paddling"]),
("Mount Kidd RV Park","independent","mount-kidd-kananaskis","AB","CA",50.8493,-115.1492,"https://mountkiddrv.com",0,"Skiing",1,0,0,["Skiing","Hiking"]),
("Dinosaur PP Campground","alberta_parks","dinosaur-pp-ab","AB","CA",50.7570,-111.5170,"https://albertaparks.ca",0,"Hiking",0,0,1,["Hiking","Paddling"]),
("Fairmont Hot Springs RV","independent","fairmont-hot-springs-bc","BC","CA",50.3347,-115.8617,"https://fairmonthotsprings.com",1,"Golf",1,0,0,["Golf","Skiing"]),
("Whistler RV Park","independent","whistler-rv-park-bc","BC","CA",50.0463,-123.0883,"https://whistlerrvpark.com",0,"Skiing",1,0,0,["Skiing","Biking"]),
("Springs at Borrego RV","independent","springs-at-borrego-ca","CA","US",33.2656,-116.3422,"https://springsatborrego.com",1,"Golf",0,1,0,["Golf","Fishing"]),
("Likely Place Golf RV","independent","likely-place-ca","CA","US",41.2299,-120.5055,"https://likelyplace.com",1,"Golf",0,1,1,["Golf","Fishing","Boating"]),
("Lakes RV & Golf Resort","independent","lakes-rv-chowchilla-ca","CA","US",37.1147,-120.2458,"https://thelakesrv.com",1,"Golf",0,0,0,["Golf"]),
("Rio Bend RV & Golf","independent","rio-bend-el-centro-ca","CA","US",32.7876,-115.6888,"https://riobendrvgolfresort.com",1,"Golf",0,1,0,["Golf","Fishing"]),
("Camp Edison Lake","independent","camp-edison-ca","CA","US",37.2341,-119.2223,"https://sce.com/campedison",0,"Boating",1,1,1,["Boating","Fishing","Skiing"]),
("Sands RV & Golf Resort","independent","sands-rv-desert-hot-springs","CA","US",33.9312,-116.5186,"https://cal-am.com",1,"Golf",0,0,0,["Golf","Hiking"]),
("Tiger Run Resort","independent","tiger-run-breckenridge","CO","US",39.5186,-106.0461,"http://tigerrunresort.com",0,"Skiing",1,0,0,["Skiing","Hiking"]),
("Sun Outdoors Rocky Mtns","campspot","sun-outdoors-rocky-mountains","CO","US",40.0886,-105.9556,"https://sunoutdoors.com",0,"Skiing",1,1,1,["Skiing","Fishing"]),
("Steamboat Springs KOA","koa","steamboat-springs","CO","US",40.5058,-106.8778,"https://koa.com",0,"Skiing",1,0,0,["Skiing"]),
("Crested Butte RV Park","independent","crested-butte-rv","CO","US",38.8697,-106.9878,"https://crestedbuttervpark.com",0,"Skiing",1,0,0,["Skiing"]),
("River Dance RV Resort","independent","river-dance-gypsum-co","CO","US",39.6455,-106.9531,"https://riverdancervresort.com",0,"Skiing",1,1,0,["Skiing","Fishing"]),
("Moab Valley RV Resort","campspot","moab-valley-rv-resort","UT","US",38.5956,-109.5758,"https://sunoutdoors.com",0,"Off-Roading",0,0,0,["Off-Roading","Hiking"]),
("Camp Gulf RV Resort","independent","camp-gulf-destin-fl","FL","US",30.3792,-86.3688,"https://campgulf.com",0,"Boating",0,1,1,["Boating","Fishing"]),
("Boyne Mountain RV","independent","boyne-mountain-mi","MI","US",45.1633,-84.9317,"https://boynemountain.com",1,"Skiing",1,0,0,["Skiing","Golf"]),
("Polson Motorcoach","independent","polson-motorcoach-mt","MT","US",47.6749,-114.1506,"https://polsonrvresort.com",0,"Boating",0,1,1,["Boating","Fishing"])
]

rows = [dict(zip(K, [r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],bool(r[8]),r[9],bool(r[10]),bool(r[11]),bool(r[12]),r[13]])) for r in D]
sb.table("campgrounds").upsert(rows, on_conflict="provider_network,external_facility_id").execute()
print(f"[+] Done: {len(rows)} upserted.")

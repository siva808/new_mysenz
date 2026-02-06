
import pandas as pd
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

CSV_FILE_NAME = '/home/dell/projects/mysenz/latti.csv'
TOP_N_SUGGESTIONS = 5


def get_coordinates_from_name(place_name):
    geolocator = Nominatim(user_agent="vendor_locator_global")
    location = geolocator.geocode(place_name)

    if location:
        return location.latitude, location.longitude
    else:
        return None, None


def clean_and_load_vendors(file_name):
    try:
        df = pd.read_csv(file_name)
    except FileNotFoundError:
        #print(f"ERROR: The file '{file_name}' was not found.")
        return None

    df.rename(columns={
        'Latitude': 'lat',
        'Longitude': 'lon',
        'Hotel Name': 'name'
    }, inplace=True)

    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    df.dropna(subset=['lat', 'lon'], inplace=True)

    print(f" Loaded {len(df)} vendors from CSV.")
    return df[['name', 'lat', 'lon']].copy()


# return nearest vendors globally 
def find_nearby_vendors(df_vendors, target_lat, target_lon, top_n):
    target_coords = (target_lat, target_lon)
    all_distances = []

    # cal distance to every vendor
    for _, row in df_vendors.iterrows():
        vendor_coords = (row['lat'], row['lon'])
        distance = geodesic(target_coords, vendor_coords).km

        all_distances.append({
            'name': row['name'],
            'latitude': row['lat'],
            'longitude': row['lon'],
            'distance_km': round(distance, 2)
        })

    # Sort all vendors by distance
    df_all = pd.DataFrame(all_distances)
    df_sorted = df_all.sort_values(by='distance_km')

    print("\n✅ Showing nearest vendors (no radius limit)")
    return df_sorted.head(top_n)



vendor_data = clean_and_load_vendors(CSV_FILE_NAME)

if vendor_data is not None:

    TARGET_LOCATION_NAME = input("Enter location: ")

    TARGET_LAT, TARGET_LON = get_coordinates_from_name(TARGET_LOCATION_NAME)

    if TARGET_LAT is None:
        print("Could not find coordinates for this place. Try a different name.")
        exit()

    suggested_vendors = find_nearby_vendors(
        df_vendors=vendor_data,
        target_lat=TARGET_LAT,
        target_lon=TARGET_LON,
        top_n=TOP_N_SUGGESTIONS
    )

    print("\n" + "="*50)
    print(f"Search Target: {TARGET_LOCATION_NAME}")
    print(f"Coordinates: Lat {TARGET_LAT}, Lon {TARGET_LON}")
    print("="*50)

    print("\n Nearest Vendor Suggestions:\n")
    print(suggested_vendors[['name', 'distance_km']].to_string(index=False))

    print("\n--- MAP PIN DATA ---")
    for _, row in suggested_vendors.iterrows():
        print(f"{{'name': '{row['name']}', 'lat': {row['latitude']}, 'lon': {row['longitude']}}}")


import  turtle,random

t = turtle.Turtle()
turtle.bgcolor("black")
t.speed(0)
for _ in range(200):
    t.color(random.random(),0,random.random())
    t.dot(random.randint(4,12))
    t.goto(random.randint(-300,200),
           random.randint(-200,200))
    


        

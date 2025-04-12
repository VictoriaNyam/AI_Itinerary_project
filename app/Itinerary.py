
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
import random
from app import db
from app.models import POI
from math import radians, cos, sin, sqrt, atan2

# Load and prepare the POI dataset
def load_poi_data():
    # Load POI dataset
    df = pd.read_csv('dataset/London_cleaned_with_all_pois.csv')
    
    # Drop POIs that don't have coordinates (not usable for clustering or mapping)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Store original coordinates for display or mapping later
    df['Original_Latitude'] = df['Latitude']
    df['Original_Longitude'] = df['Longitude']

    # Normalize coordinates for better clustering
    df = normalize_coordinates(df)

    return df

# Normalize lat/lon values between 0 and 1
def normalize_coordinates(df):
    scaler = MinMaxScaler()
    df[['Norm_Latitude', 'Norm_Longitude']] = scaler.fit_transform(df[['Latitude', 'Longitude']])
    return df

# Filter POIs based on user-selected activities
def filter_pois_by_activity(df, selected_activities):
    # Keep only POIs that match at least one of the selected activities
    df = df[df[selected_activities].sum(axis=1) > 0].reset_index(drop=True)
    return df

# Apply K-Means clustering using number of clusters = number of days
def apply_kmeans(df, days):
    activity_cols = [
        'nature', 'nightlife', 'drink', 'music', 'dance', 'history',
        'sports', 'art', 'museum', 'walk', 'restaurant', 'movie'
    ]
    X = df[['Norm_Latitude', 'Norm_Longitude'] + activity_cols].values

    # Set the number of clusters equal to number of trip days
    kmeans = KMeans(n_clusters=days, random_state=42)
    df['cluster'] = kmeans.fit_predict(X)
    return df, kmeans

# Select multiple POIs (default 5) per cluster based on proximity to cluster center
def select_representative_pois(df, kmeans, pois_per_day=5):
    representative_pois = []
    for cluster_num in range(len(kmeans.cluster_centers_)):
        cluster_group = df[df['cluster'] == cluster_num]
        if not cluster_group.empty:
            center = kmeans.cluster_centers_[cluster_num]
            cluster_group = cluster_group.copy()
            cluster_group['dist'] = ((cluster_group['Norm_Latitude'] - center[0])**2 + 
                                     (cluster_group['Norm_Longitude'] - center[1])**2)
            # Select top N closest POIs
            selected = cluster_group.sort_values('dist').head(pois_per_day)
            representative_pois.extend(selected.to_dict(orient='records'))
    return representative_pois

# Helper to split a list into N approximately equal parts
def split_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]

# Haversine formula to calculate distance between two geo-points
def calculate_haversine_distance(poi1, poi2):
    lat1, lon1 = radians(poi1['latitude']), radians(poi1['longitude'])
    lat2, lon2 = radians(poi2['latitude']), radians(poi2['longitude'])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius = 6371  # Earth radius in kilometers
    return radius * c

# 2-opt algorithm to optimize visit order by reducing travel distance
def opt2(itinerary):
    improved = True
    while improved:
        improved = False
        for i in range(1, len(itinerary) - 1):
            for j in range(i + 1, len(itinerary)):
                new_itinerary = itinerary[:i] + itinerary[i:j + 1][::-1] + itinerary[j + 1:]
                if calculate_total_distance(new_itinerary) < calculate_total_distance(itinerary):
                    itinerary = new_itinerary
                    improved = True
                    break
            if improved:
                break
    return itinerary

# Total travel distance for an itinerary (used in optimization)
def calculate_total_distance(itinerary):
    total_distance = 0
    for i in range(len(itinerary) - 1):
        total_distance += calculate_haversine_distance(itinerary[i], itinerary[i + 1])
    return total_distance

# Build final itineraries grouped by day, and optionally store them in the database
def generate_itineraries(representative_pois, selected_activities, days):
    # Remove duplicates by name (in case one POI ends up in multiple clusters)
    unique_pois = {poi['name']: poi for poi in representative_pois}
    
    # Prioritize POIs based on how well they match the selected activities
    sorted_pois = sorted(unique_pois.values(), key=lambda p: sum(p.get(act, 0) for act in selected_activities), reverse=True)
    
    # Distribute POIs across days
    daily_parts = split_list(sorted_pois, days)

    itineraries = []
    for day_num, part in enumerate(daily_parts, start=1):
        day_itinerary = []
        for poi in part:
            poi_data = {
                'name': poi['name'],
                'latitude': poi['Original_Latitude'],
                'longitude': poi['Original_Longitude'],
                'address': poi.get('address', ''),
                'day': day_num
            }
            # Attach activity tags if they exist
            poi_data.update({act: poi.get(act, 0) for act in selected_activities})
            day_itinerary.append(poi_data)
        itineraries.append(day_itinerary)

    # Optimize order of visits for each day
    for i in range(len(itineraries)):
        itineraries[i] = opt2(itineraries[i])

    # Save the final POIs to the database
    for itinerary in itineraries:
        for poi_data in itinerary:
            poi_instance = POI(
                name=poi_data.get('name'),
                address=poi_data.get('address'),
                latitude=poi_data.get('latitude'),
                longitude=poi_data.get('longitude'),
                original_latitude=poi_data.get('latitude'),
                original_longitude=poi_data.get('longitude'),
                day=poi_data.get('day'),
                itinerary_id=1  # itinerary ID
            )
            db.session.add(poi_instance)
    db.session.commit()

    return itineraries
>>>>>>> beb1998 (Intial commit)

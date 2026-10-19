import folium
from geopy.geocoders import Nominatim


def get_madrid_map(location_name: str = "Puerta del Sol"):
  """Peta Madrid interaktif via OpenStreetMap (100% gratis tanpa API key)."""
  geolocator = Nominatim(user_agent="tokyo_assistant_madrid")
  query = f"{location_name}, Madrid, Spain"
  try:
    location = geolocator.geocode(query, timeout=5)
    if location:
      lat, lon = location.latitude, location.longitude
      addr = location.address
    else:
      lat, lon = 40.4168, -3.7038
      addr = "Madrid Centro"
  except Exception:
    lat, lon = 40.4168, -3.7038
    addr = "Madrid Centro"

  m = folium.Map(location=[lat, lon], zoom_start=14)
  folium.Marker(
      [lat, lon],
      popup=addr,
      tooltip=location_name,
      icon=folium.Icon(color="red", icon="info-sign"),
  ).add_to(m)
  return m
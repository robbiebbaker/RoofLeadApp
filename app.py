import os
import streamlit as st
import pandas as pd
import requests
import openai

# ===== API KEYS =====
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")



# === Get Coordinates from Neighborhood ===
def get_coordinates_from_place(place_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get("results")
        if results:
            location = results[0]["geometry"]["location"]
            return location["lat"], location["lng"]
    return None, None

# === Get Nearby Places (Google Places API) ===
def get_nearby_places(lat, lon, radius=800):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius={radius}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    results = response.json().get("results", [])
    places = []
    for place in results:
        loc = place["geometry"]["location"]
        places.append({
            "Address": place.get("name", "N/A"),
            "latitude": loc["lat"],
            "longitude": loc["lng"]
        })
    return pd.DataFrame(places)

# === Use ChatGPT to extract location from prompt ===
def extract_location_from_prompt(prompt):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Extract the city or neighborhood from the prompt and return it plainly."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# === Dummy scoring logic ===
def score_row(row):
    score = 0
    if "ave" in row["Address"].lower():
        score += 2
    if "st" in row["Address"].lower():
        score += 3
    if row["latitude"] % 2 < 1:
        score += 1
    return score

# === Streamlit UI ===
st.title("Neighborhood Roof Lead Finder (Chat Style)")
prompt = st.text_input("Ask something like: 'Show me homes near Richmond Hill for leads'")

if prompt:
    try:
        location = extract_location_from_prompt(prompt)
        st.success(f"Extracted location: **{location}**")
        lat, lon = get_coordinates_from_place(location)

        if lat and lon:
            data = get_nearby_places(lat, lon)
            if not data.empty:
                data["LeadScore"] = data.apply(score_row, axis=1)
                data = data.sort_values(by="LeadScore", ascending=False)
                st.map(data[["latitude", "longitude"]])
                st.dataframe(data)
            else:
                st.warning("No leads found nearby.")
        else:
            st.error("Could not find coordinates for that location.")
    except Exception as e:
        st.error(f"Something went wrong: {e}")

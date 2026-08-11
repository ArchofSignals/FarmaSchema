"""
recommendation.py
------------------
This file is the "brain" of FarmaSchema. It does two separate jobs, and it is
important to keep them separate so the logic stays easy to explain to judges:

1. ML RELEVANCE SCORING (TF-IDF + cosine similarity)
   We turn the farmer's profile into a short piece of text, and we turn each
   scheme's description into a piece of text. We then use TF-IDF to convert
   both pieces of text into numeric vectors, and cosine similarity to measure
   how "close" the farmer's text is to each scheme's text. This produces the
   "relevance_score" (a number between 0 and 1).

2. RULE-BASED EXPLAINABILITY (matched_attributes / unknown_or_missing)
   Separately, we check simple, transparent rules: does the farmer's state,
   crop, category, land size and irrigation status match what the scheme
   states? This produces a human-readable list like:
       ["State: Karnataka matches", "Crop: Rice matches"]
   and a list of things we could not confirm, like:
       ["Land ownership status: Not provided"]

Both pieces of information are returned together for every scheme, but they
are calculated independently. This keeps each part small and understandable.
"""

import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Path to the schemes data file, relative to this file (works no matter
# which folder you run the script from).
SCHEMES_FILE = os.path.join(os.path.dirname(__file__), "data", "schemes.json")


def load_schemes():
    """Load the list of scheme dictionaries from the JSON data file."""
    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_land_category(land_size_acres):
    """
    Classify a land size (in acres) into the standard Indian farmer
    categories. This is only used as a helpful hint — it never overrides
    what the farmer selects in the profile form.
    Roughly: marginal < 2.5 acres, small 2.5-5, medium 5-25, large > 25.
    """
    if land_size_acres is None:
        return None
    if land_size_acres < 2.5:
        return "Marginal Farmer"
    if land_size_acres < 5:
        return "Small Farmer"
    if land_size_acres < 25:
        return "Medium Farmer"
    return "Large Farmer"


def build_farmer_text(profile):
    """
    Turn a farmer profile dict into a single text string for TF-IDF.

    We repeat the important fields (state, crop, category) a couple of
    times. This is a simple, explainable trick: TF-IDF gives more weight
    to words that appear more often in a document, so repeating the
    farmer's key facts makes sure they count strongly in the comparison,
    instead of being drowned out by generic words like "farmer" or
    "scheme" that appear in almost every document.
    """
    state = profile.get("state", "") or ""
    district = profile.get("district", "") or ""
    crop = profile.get("crop", "") or ""
    category = profile.get("category", "") or ""
    land_size = profile.get("land_size")
    irrigation = profile.get("irrigation", "") or ""
    details = profile.get("details", "") or ""

    irrigation_text = "irrigated irrigation available" if str(irrigation).lower() == "yes" else "rain-fed no irrigation"

    parts = [
        state, state,
        district,
        crop, crop,
        category, category,
        irrigation_text,
        f"{land_size} acres" if land_size is not None else "",
        details,
    ]
    return " ".join(str(p) for p in parts if p).strip()


def build_scheme_text(scheme):
    """
    Turn a scheme dict into a single text string for TF-IDF.

    Like build_farmer_text, we repeat the scheme's states/crops/categories
    so they carry meaningful weight in the comparison against the farmer's
    profile text.
    """
    states = " ".join(scheme.get("states", []) or [])
    crops = " ".join(scheme.get("crops", []) or [])
    categories = " ".join(scheme.get("farmer_categories", []) or [])
    eligibility = " ".join(scheme.get("eligibility", []) or [])

    parts = [
        scheme.get("name", ""),
        scheme.get("short_description", ""),
        scheme.get("description", ""),
        scheme.get("benefits", ""),
        eligibility,
        states, states,
        crops, crops,
        categories, categories,
        scheme.get("land_size_info", ""),
        scheme.get("irrigation_info", ""),
    ]
    return " ".join(str(p) for p in parts if p).strip()


def compute_relevance_scores(profile, schemes):
    """
    Core ML step: TF-IDF + cosine similarity.

    We build ONE TF-IDF vectorizer fitted on all the documents together
    (the farmer's text plus every scheme's text). Fitting on all documents
    together is what lets TF-IDF learn which words are common (like
    "farmer", "scheme", "support") and which are distinctive (like
    "Karnataka", "beekeeping", "drip"). Common words get a lower weight,
    distinctive words get a higher weight.

    Returns a list of floats (relevance scores between 0 and 1), in the
    same order as the `schemes` list passed in.
    """
    farmer_text = build_farmer_text(profile)
    scheme_texts = [build_scheme_text(s) for s in schemes]

    # All documents together, farmer profile first.
    all_documents = [farmer_text] + scheme_texts

    # stop_words="english" removes common English words (the, and, of, ...)
    # so they don't dilute the comparison.
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(all_documents)

    # Row 0 is the farmer's vector, the rest are the schemes' vectors.
    farmer_vector = tfidf_matrix[0:1]
    scheme_vectors = tfidf_matrix[1:]

    # cosine_similarity returns values from -1 to 1, but with TF-IDF
    # (non-negative weights) the result is always between 0 and 1.
    similarities = cosine_similarity(farmer_vector, scheme_vectors)[0]
    return similarities.tolist()


def rule_based_match(profile, scheme):
    """
    Second, independent step: simple transparent rule checks.

    For each attribute (state, crop, category, land size, irrigation) we
    check whether the farmer's profile satisfies what the scheme states.
    If the farmer did not provide a piece of information, we NEVER assume
    they are eligible — we mark it as "Not provided" instead.

    Returns (matched_attributes, unknown_or_missing) — two lists of
    human-readable strings.
    """
    matched = []
    unknown = []

    # --- State ---
    scheme_states = scheme.get("states", []) or []
    farmer_state = (profile.get("state") or "").strip()
    if not farmer_state:
        unknown.append("State: Not provided")
    elif "All States" in scheme_states or farmer_state in scheme_states:
        matched.append(f"State: {farmer_state} matches")
    else:
        unknown.append(f"State: {farmer_state} not listed for this scheme")

    # --- Crop ---
    scheme_crops = scheme.get("crops", []) or []
    farmer_crop = (profile.get("crop") or "").strip()
    if not farmer_crop:
        unknown.append("Crop: Not provided")
    elif "All Crops" in scheme_crops or any(
        farmer_crop.lower() == c.lower() for c in scheme_crops
    ):
        matched.append(f"Crop: {farmer_crop} matches")
    else:
        unknown.append(f"Crop: {farmer_crop} not specifically listed for this scheme")

    # --- Farmer category ---
    scheme_categories = scheme.get("farmer_categories", []) or []
    farmer_category = (profile.get("category") or "").strip()
    if not farmer_category:
        unknown.append("Farmer category: Not provided")
    elif "All Farmers" in scheme_categories or farmer_category in scheme_categories:
        matched.append(f"Category: {farmer_category} matches")
    else:
        unknown.append(f"Category: {farmer_category} not specifically listed for this scheme")

    # --- Land size ---
    land_size = profile.get("land_size")
    min_land = scheme.get("min_land_acres")
    max_land = scheme.get("max_land_acres")
    if land_size is None:
        unknown.append("Land size: Not provided")
    else:
        within_min = (min_land is None) or (land_size >= min_land)
        within_max = (max_land is None) or (land_size <= max_land)
        if within_min and within_max:
            matched.append(f"Land size: {land_size} acres fits this scheme's range")
        else:
            unknown.append(f"Land size: {land_size} acres may be outside this scheme's stated range")

    # --- Irrigation ---
    scheme_irrigation = scheme.get("irrigation_required", "Any")
    farmer_irrigation = profile.get("irrigation")
    if farmer_irrigation is None or farmer_irrigation == "":
        unknown.append("Irrigation availability: Not provided")
    elif scheme_irrigation == "Any":
        matched.append("Irrigation: not a requirement for this scheme")
    elif str(farmer_irrigation).lower() == str(scheme_irrigation).lower():
        matched.append(f"Irrigation: matches requirement ({scheme_irrigation})")
    else:
        unknown.append(f"Irrigation: this scheme expects '{scheme_irrigation}'")

    # Land ownership is commonly required by real schemes but our simple
    # profile form does not collect it — always flag it honestly rather
    # than silently assuming the farmer owns the land.
    unknown.append("Land ownership / title status: Not provided")

    return matched, unknown


def recommend(profile, top_n=None):
    """
    Main entry point used by the Flask API.

    1. Loads all schemes.
    2. Computes a TF-IDF + cosine similarity relevance score for each one.
    3. Computes the rule-based matched/unknown attributes for each one.
    4. Sorts schemes by relevance_score, highest first.
    5. Returns a list of result dictionaries ready to be turned into JSON.
    """
    schemes = load_schemes()
    scores = compute_relevance_scores(profile, schemes)

    results = []
    for scheme, score in zip(schemes, scores):
        matched, unknown = rule_based_match(profile, scheme)
        results.append({
            "id": scheme["id"],
            "name": scheme["name"],
            "short_description": scheme["short_description"],
            "relevance_score": round(float(score), 4),
            "matched_attributes": matched,
            "unknown_or_missing": unknown,
            "official_url": scheme.get("official_url", ""),
        })

    results.sort(key=lambda r: r["relevance_score"], reverse=True)

    if top_n is not None:
        results = results[:top_n]

    return results


if __name__ == "__main__":
    # Quick manual test — run this file directly with:
    #   python recommendation.py
    # to confirm the recommendation logic works before wiring up Flask.
    sample_profile = {
        "state": "Karnataka",
        "district": "Bengaluru Rural",
        "crop": "Rice",
        "land_size": 2,
        "category": "Small Farmer",
        "irrigation": "Yes",
        "details": "",
    }

    print("Sample farmer profile:", sample_profile)
    print("Farmer TF-IDF text  :", build_farmer_text(sample_profile))
    print()

    recommendations = recommend(sample_profile, top_n=5)
    for i, rec in enumerate(recommendations, start=1):
        print(f"{i}. {rec['name']}  (relevance_score={rec['relevance_score']})")
        print("   Matched :", rec["matched_attributes"])
        print("   Unknown :", rec["unknown_or_missing"])
        print()

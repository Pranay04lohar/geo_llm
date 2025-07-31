# Use: To parse name of the city from the user query
# Concepts used:
# 1. Gazetteer is a list of all the valid locations of indian cities from json file
# 2.Fuzzy match finds the best match for the queried city name if the spelling is incorrect
# 3.Using n-grams to match the multi word cities by checking group of words together

import json
from rapidfuzz import process, fuzz
import os

STOPWORDS = {
    "a", "an", "and", "the", "in", "on", "for", "with", "of", "at", "by",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "show", "rainfall", "weather", "forecast", "tomorrow", "today", "yesterday",
    "temperature", "like"
}


# Construct the path to the JSON file relative to this script's location
json_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'indian_cities.json')

with open(json_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)


# Create a flat list of original city names and states
original_gazetteer = [(location, "city") for state_info in data.values() for location in state_info["locations"]]
original_gazetteer.extend([(state, "state") for state in data.keys()])

# Create a mapping from lowercase names to their original casings and types
# and a list of lowercase names for matching.
gazetteer_map = {name.lower(): (name, type_) for name, type_ in original_gazetteer}
lowercase_gazetteer = list(gazetteer_map.keys())

def generate_ngrams(tokens, max_n=3):
    ngrams = []
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            ngrams.append(" ".join(tokens[i:i+n]))
    return ngrams

def fuzzy_match_place(query_ngram, confidence_threshold=85):
    """
    Finds the best match for a lowercase n-gram from the lowercase gazetteer.
    Returns the original cased name and type if a match is found.
    """
    # Match against the all-lowercase gazetteer
    result = process.extractOne(query_ngram, lowercase_gazetteer, scorer=fuzz.WRatio)
    
    if result:
        matched_name_lower, score, _ = result
        if score >= confidence_threshold:
            # Retrieve the original cased name and type from the map
            original_name, type_ = gazetteer_map[matched_name_lower]
            return {
                "query_text": query_ngram,
                "matched_name": original_name,
                "type": type_,
                "confidence": score
            }
    return None

def roi_parser(user_query, max_ngram_size=3):
    # Convert the entire query to lowercase for consistent processing
    tokens = user_query.lower().split()
    
    all_ngrams = generate_ngrams(tokens, max_n=max_ngram_size)
    sorted_ngrams = sorted(all_ngrams, key=len, reverse=True)
    
    found_locations = []
    used_tokens = [False] * len(tokens) 
    
    for ngram in sorted_ngrams:
        ngram_tokens = ngram.split()
        
        start_index = -1
        for i in range(len(tokens) - len(ngram_tokens) + 1):
            if tokens[i:i+len(ngram_tokens)] == ngram_tokens:
                start_index = i
                break

        if start_index == -1: continue

        if any(used_tokens[start_index : start_index + len(ngram_tokens)]):
            continue
            
        if any(token in STOPWORDS for token in ngram_tokens):
            continue
            
        # Pass the lowercase ngram to the matching function
        match = fuzzy_match_place(ngram)
        
        if match:
            # Use the original query text for the matched part
            original_ngram_tokens = user_query.split()[start_index : start_index + len(ngram_tokens)]
            match["query_text"] = " ".join(original_ngram_tokens)
            
            found_locations.append(match)
            for i in range(len(ngram_tokens)):
                used_tokens[start_index + i] = True
            
    return found_locations

if __name__ == "__main__":
    test_queries = [
        "Show rainfall for Nahlagun and Barpet tomorrow",
        "What is the weather like in Port Blair",
        "temperature in new delhi today",
        "forecast for Maharashtra and Goa"
    ]
    
    for query in test_queries:
        print(f"--- Parsing query: '{query}' ---")
        locations = roi_parser(query)
        print("Found locations:")
        print(json.dumps(locations, indent=2))
        print("\\n")
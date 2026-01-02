import re
import requests

# --- INITIALIZATION: Load Quran Data ---
try:
    _QURAN_DATA = {} # Format: { "Surah:Ayah": {"text": "Original Text", "clean": "Clean Text"} }
    print("Loading Quran Data (Uthmani & Cleaning)...")
    
    # Use the reliable Uthmani source
    _response = requests.get("https://raw.githubusercontent.com/risan/quran-json/main/dist/quran.json")
    _response.raise_for_status()
    _json_data = _response.json()
    
    def remove_diacritics(text):
        # Remove common Arabic diacritics
        # Tashkeel (Fatha, Damma, Kasra, etc.) + Tatweel
        return re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u06E5\u06E6]', '', text)

    for _surah in _json_data:
        _s_num = _surah['id']
        for _ayah in _surah['verses']:
            _a_num = _ayah['id']
            _text = _ayah['text']
            _clean = remove_diacritics(_text)
            
            _QURAN_DATA[f"{_s_num}:{_a_num}"] = {
                "text": _text,
                "clean": _clean
            }
            
    print(f"Loaded and indexed {_QURAN_DATA.__len__()} Ayahs.")
except Exception as e:
    print(f"Error loading Quran: {e}")

# --- THE SEARCH FUNCTION ---
def search_root_in_quran(root_letters):
    """
    Scans the entire Quran for words containing the specific 3-letter root sequence.
    Args:
        root_letters (list): e.g. ['k', 't', 'b']
    Returns:
        list: A list of strings formatted as "[Surah:Ayah] Text"
    """
    if not _QURAN_DATA: return ["Error: Database not loaded."]
    
    # Construct regex for CLEAN text search
    # Letter1 + (0-6 chars) + Letter2 + (0-6 chars) + Letter3
    l1, l2, l3 = root_letters
    pattern = fr"{l1}\w{{0,6}}{l2}\w{{0,6}}{l3}"
    
    matches = []
    for key, data in _QURAN_DATA.items():
        if re.search(pattern, data["clean"]):
            # Return the ORIGINAL Uthmani text for display
            matches.append(f"[{key}] {data['text']}")
    
    # Return top 20 distinct results for analysis
    return matches[:20]

if __name__ == "__main__":
    # Test
    print("Testing Root Search (K-T-B)...")
    results = search_root_in_quran(['ك', 'ت', 'ب'])
    for r in results[:5]:
        print(r)

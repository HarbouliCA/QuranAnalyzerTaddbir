COMMON_ROOTS = {
    "شيء": ["شيء", "اشياء", "شيئا", "كل شيء"],
    "علم": ["علم", "يعلم", "عليم", "اعلم"],
}

def root_match(query: str, verse_text: str) -> bool:
    for root, forms in COMMON_ROOTS.items():
        if query in forms:
            return any(f in verse_text for f in forms)
    return False

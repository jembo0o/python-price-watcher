STEAM_COUNTRY_CODE_ALIASES = {
    "eu": "de",
    "europe": "de",
    "euro": "de",
    "eurozone": "de",
    "ukraine": "ua",
    "ukr": "ua",
}

CANONICAL_REGION_ALIASES = {
    "europe": "eu",
    "euro": "eu",
    "eurozone": "eu",
    "ukraine": "ua",
    "ukr": "ua",
}


def normalize_region(region: str) -> str:
    normalized_region = region.strip().lower()
    if not normalized_region:
        raise ValueError("Region must be a non-empty value")

    return CANONICAL_REGION_ALIASES.get(normalized_region, normalized_region)


def get_steam_country_code(region: str) -> str:
    normalized_region = normalize_region(region)
    return STEAM_COUNTRY_CODE_ALIASES.get(normalized_region, normalized_region)

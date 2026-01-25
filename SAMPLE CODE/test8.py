from pyarr import RadarrAPI
import tmdbsimple as tmdb

# =========================
# CONFIG
# =========================

LIMIT = 100

DEFAULT_ROOT_IDX = 0
DEFAULT_PROFILE_IDX = 6
DEFAULT_TAG_IDX = 12

radarr_monitor = False
radarr_search = False

# RADARR
RADARR_HOST = "http://10.0.30.30:7878"
RADARR_API_KEY = "d6066eca134b4f9e84c6702ac68ab7df"
radarr_session = RadarrAPI(RADARR_HOST, RADARR_API_KEY)

# TMDB
tmdb.API_KEY = "5415f73b1c8db259623ca8fe9f3a8c4f"
tmdbMovies = tmdb.Movies()

# =========================
# LANGUAGE FILTER
# =========================

def language_filter(movie, allowed=None, excluded=None):
    """
    Filter movies by original language.

    allowed  = set of allowed language codes (e.g. {"en"})
    excluded = set of excluded language codes (e.g. {"hi"})
    """
    lang = movie.get("original_language")

    if allowed and lang not in allowed:
        return False

    if excluded and lang in excluded:
        return False

    return True

# =========================
# TMDB PAGED FETCH
# =========================

def fetch_tmdb_list(fetch_func, language_settings, limit=LIMIT, **kwargs):
    results = []
    page = 1

    while len(results) < limit:
        response = fetch_func(page=page, **kwargs)
        movies = response.get("results", [])

        if not movies:
            break

        for movie in movies:
            if language_filter(
                movie,
                allowed=language_settings.get("allowed"),
                excluded=language_settings.get("excluded"),
            ):
                results.append(movie)

                if len(results) == limit:
                    break

        page += 1

    return results

# =========================
# TMDB LISTS
# =========================

def popular_list(language_settings):
    return fetch_tmdb_list(tmdbMovies.popular, language_settings)

def top_rated_list(language_settings):
    return fetch_tmdb_list(tmdbMovies.top_rated, language_settings)

DISCOVER_KEYS = {
    "company": "company",
    "network": "with_networks",
}

def discover_by_provider(provider_id, provider_type, language_settings):
    discover = tmdb.Discover()

    if provider_type not in DISCOVER_KEYS:
        raise ValueError("provider_type must be 'company' or 'network'")

    return fetch_tmdb_list(
        discover.movie,
        language_settings,
        **{DISCOVER_KEYS[provider_type]: provider_id}
    )

# =========================
# RADARR HELPERS
# =========================

def load_quality():
    return [{"id": p["id"], "name": p["name"]}
            for p in radarr_session.get_quality_profile()]

def load_root_folders():
    return [{"id": f["id"], "path": f["path"]}
            for f in radarr_session.get_root_folder()]

def load_tags(tag_label):
    radarr_session.create_tag(tag_label)
    return [{"id": t["id"], "label": t["label"]}
            for t in radarr_session.get_tag()]

def check_radarr(movie):
    return bool(radarr_session.get_movie(movie["id"], tmdb=True))

def lookup_radarr(tmdb_id):
    result = radarr_session.lookup_movie(term=f"tmdb:{tmdb_id}")
    return bool(result), result

# =========================
# RADARR ACTIONS
# =========================

def send_to_radarr(movie, root, quality, monitor, search, tag):
    radarr_session.add_movie(
        movie=movie,
        root_dir=root["path"],
        quality_profile_id=quality["id"],
        monitored=monitor,
        search_for_movie=search,
        tags=[tag["id"]],
    )

def parse_list(movie_list, root, quality, tag):
    for item in movie_list:

        if check_radarr(item):
            print(f"[SKIP] TMDb ID: {item['id']}  TITLE: {item['title']}")
            continue

        print(f"[ADDING] TMDb ID: {item['id']}  TITLE: {item['title']}")

        found, lookup_data = lookup_radarr(item["id"])
        if not found:
            print("    --> [NOT FOUND IN RADARR LOOKUP]")
            continue

        send_to_radarr(
            lookup_data[0],
            root,
            quality,
            radarr_monitor,
            radarr_search,
            tag,
        )

# =========================
# SETUP
# =========================

def setup_radarr_data():
    tag_label = "test1"
    return load_root_folders(), load_quality(), load_tags(tag_label)

# =========================
# MAIN
# =========================

def main():
    roots, profiles, tags = setup_radarr_data()

    # =========================
    # USER LANGUAGE SELECTION
    # =========================

    language_settings = {
        "allowed": {"en"},        # e.g. {"en"}
        "excluded": None # {"hi"},     # exclude Hindi
    }

    # =========================
    # USER SOURCE SELECTION
    # =========================

    # movies = popular_list(language_settings)
    movies = top_rated_list(language_settings)

    # Apple TV (company)
    # movies = discover_by_provider(2552, "company", language_settings)

    # Netflix (network)
    # movies = discover_by_provider(213, "network", language_settings)

    parse_list(
        movies,
        roots[DEFAULT_ROOT_IDX],
        profiles[DEFAULT_PROFILE_IDX],
        tags[DEFAULT_TAG_IDX],
    )

if __name__ == "__main__":
    main()

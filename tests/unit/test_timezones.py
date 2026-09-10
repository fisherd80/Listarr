import zoneinfo

import pytest

from listarr.utils.timezones import CURATED_TIMEZONES, curated_zone_keys

pytestmark = pytest.mark.unit


def test_curated_zones_are_a_subset_of_available_timezones():
    available = zoneinfo.available_timezones()
    curated = curated_zone_keys()

    assert curated <= available, f"Missing from available_timezones(): {sorted(curated - available)}"


@pytest.mark.parametrize("key", sorted(curated_zone_keys()))
def test_every_curated_zone_resolves(key):
    zoneinfo.ZoneInfo(key)


def test_grouping_shape_and_ordering():
    groups = list(CURATED_TIMEZONES)

    assert isinstance(CURATED_TIMEZONES, dict)
    assert groups[0] == "UTC"
    assert CURATED_TIMEZONES["UTC"] == ["UTC"]
    assert groups[1:] == sorted(groups[1:])

    for zones in CURATED_TIMEZONES.values():
        assert zones
        assert all(isinstance(zone, str) for zone in zones)
        assert zones == sorted(zones)


def test_no_duplicate_zones_across_regions():
    all_zones = [zone for zones in CURATED_TIMEZONES.values() for zone in zones]

    assert len(all_zones) == len(curated_zone_keys())


def test_etc_utc_is_excluded_and_count_in_range():
    curated = curated_zone_keys()

    assert "UTC" in curated
    assert "Etc/UTC" not in curated
    assert 100 <= len(curated) <= 150

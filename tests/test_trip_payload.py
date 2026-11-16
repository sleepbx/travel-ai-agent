from ai_core.trip_payload import (
    _select_cheapest_items,
    _select_price_aligned_items,
    format_inr,
    parse_price_range,
    price_midpoint,
)


def _hotels(*prices):
    return [{"name": f"H{i}", "price": p} for i, p in enumerate(prices)]


def _prices(items):
    return [item["price"] for item in items]


def test_format_inr():
    assert format_inr(12345.6) == "INR 12,346"
    assert format_inr(None) == "INR estimate pending"


def test_parse_price_range_handles_text_numbers_and_dicts():
    assert parse_price_range("₹3,500 - ₹4,200") == (3500, 4200)
    assert parse_price_range(5000) == (5000, 5000)
    assert parse_price_range({"extracted_price": 2750}) == (2750, 2750)
    assert parse_price_range("price on request") == (None, None)
    assert parse_price_range(None) == (None, None)


def test_price_midpoint():
    assert price_midpoint("3,000 - 5,000") == 4000
    assert price_midpoint("no price") is None


def test_price_aligned_ranking_puts_over_cap_and_unpriced_last():
    items = _hotels(7000, 4800, 5600, None, 3000)

    ranked = _select_price_aligned_items(
        items, lambda h: h["price"], target_price=5000, max_price=6000, limit=5
    )

    # Within budget, closest to the target first; then over the cap; then no price.
    assert _prices(ranked) == [4800, 5600, 3000, 7000, None]


def test_price_aligned_ranking_respects_limit():
    items = _hotels(7000, 4800, 5600, None, 3000)

    ranked = _select_price_aligned_items(items, lambda h: h["price"], target_price=5000, max_price=6000)

    assert _prices(ranked) == [4800, 5600]


def test_price_aligned_ranking_anchors_on_median_without_target():
    items = _hotels(1000, 4000, 9000)

    ranked = _select_price_aligned_items(items, lambda h: h["price"], limit=3)

    assert _prices(ranked)[0] == 4000


def test_cheapest_ranking_puts_over_cap_last():
    items = _hotels(7000, 4800, 5600, None, 3000)

    ranked = _select_cheapest_items(items, lambda h: h["price"], max_price=6000, limit=5)

    assert _prices(ranked) == [3000, 4800, 5600, 7000, None]

"""Numbers as spoken in Hindi, Hinglish and English."""

from datetime import date

import pytest

from app.services.assistant import nlu, numbers


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("पचास", 50),
        ("बारह हज़ार", 12000),
        ("दो हज़ार पाँच सौ", 2500),
        ("डेढ़ सौ", 150),
        ("ढाई हज़ार", 2500),
        ("सवा सौ", 125),
        ("सवा लाख", 125000),
        ("साढ़े तीन सौ", 350),
        ("एक लाख पचास हज़ार", 150000),
        ("do hazaar paanch sau", 2500),
        ("ek lakh pachas hazaar", 150000),
        ("twelve thousand five hundred", 12500),
        ("two lakh", 200000),
        ("top 5 products", 5),
        ("निन्यानवे", 99),
        ("तिरेपन", 53),
    ],
)
def test_reads_spoken_amounts(text: str, value: int) -> None:
    assert numbers.first(text) == value


@pytest.mark.parametrize(
    "text", ["I want to do it", "so what", "बिक्री कितनी हुई", "what is my margin", ""]
)
def test_ordinary_words_are_not_numbers(text: str) -> None:
    assert numbers.first(text) is None


def test_finds_several_numbers_in_one_sentence() -> None:
    assert [v for *_, v in numbers.parse("दो सौ से पाँच सौ")] == [200, 500]


@pytest.mark.parametrize(
    ("text", "n"),
    [
        ("टॉप पाँच प्रोडक्ट", 5),
        ("top seven products", 7),
        ("सबसे ज़्यादा बिकने वाले दस", 10),
        ("top 3 products", 3),
        ("top products", 5),
    ],
)
def test_top_n_from_speech(text: str, n: int) -> None:
    assert nlu.route(text, date(2026, 11, 11)).top_n == n

"""Hindi names spoken to a shop whose catalogue is in English."""

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.models.commerce import Product
from app.models.user import User
from app.models.workspace import Workspace
from app.services.assistant import tools, translit

CATALOGUE = [
    ("RIC-5", "Basmati Rice 5 kg"),
    ("RIC-1", "Sona Masoori Rice 1 kg"),
    ("ATT-5", "Wheat Atta 5 kg"),
    ("DAL-1", "Toor Dal 1 kg"),
    ("SUG-1", "Sugar 1 kg"),
    ("SAL-1", "Iodised Salt 1 kg"),
    ("BIS-1", "Parle-G Biscuit"),
]


@pytest.fixture
def shop(db_session_factory: sessionmaker[Session]) -> Iterator[tuple[Session, uuid.UUID]]:
    with db_session_factory() as db:
        owner = User(email="o@x.com", full_name="O", hashed_password="x")
        db.add(owner)
        db.flush()
        ws = Workspace(name="S", slug="s", created_by_id=owner.id)
        db.add(ws)
        db.flush()
        for sku, name in CATALOGUE:
            db.add(Product(workspace_id=ws.id, sku=sku, name=name))
        db.commit()
        yield db, ws.id


@pytest.mark.parametrize(
    ("said", "sku"),
    [
        ("बासमती राइस कितना बचा है", "RIC-5"),
        ("आटा", "ATT-5"),
        ("चीनी का स्टॉक", "SUG-1"),
        ("तूर दाल", "DAL-1"),
        ("नमक", "SAL-1"),
        ("पारले बिस्कुट", "BIS-1"),
        ("basmati rice stock", "RIC-5"),
    ],
)
def test_finds_the_product_from_hindi_or_english(
    shop: tuple[Session, uuid.UUID], said: str, sku: str
) -> None:
    db, ws = shop
    found = tools.find_product_in_text(db, ws, said)
    assert found is not None
    assert found.sku == sku


def test_ambiguous_word_gives_candidates_not_a_guess(shop: tuple[Session, uuid.UUID]) -> None:
    db, ws = shop
    assert tools.find_product_in_text(db, ws, "चावल का स्टॉक") is None  # two kinds of rice
    names = tools.product_candidates(db, ws, "चावल का स्टॉक")
    assert set(names) == {"Basmati Rice 5 kg", "Sona Masoori Rice 1 kg"}


def test_unrelated_words_find_nothing(shop: tuple[Session, uuid.UUID]) -> None:
    db, ws = shop
    for said in ("आज की बिक्री कितनी हुई", "मौसम कैसा है", "how much did I sell"):
        assert tools.find_product_in_text(db, ws, said) is None, said


def test_sound_classes_meet_across_scripts() -> None:
    assert translit.sound_class(translit.to_roman("राइस")) == translit.sound_class("rice")
    assert translit.sound_class(translit.to_roman("बासमती")) == translit.sound_class("basmati")
    assert translit.expand("hello") == (set(), set())

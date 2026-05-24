from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.daily_log.catalog import CATEGORIES, TAG_BY_KEY


def _login(client, db):
    password = "strongpassword"
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password=password)
    db.flush()
    client.post("/login", json={"username": "alice", "password": password})


def test_catalog_uses_readable_chinese_labels():
    category_labels = [category.label for category in CATEGORIES]

    assert category_labels == ["亲密与性欲", "心情", "症状", "分泌物", "消化", "排卵测试", "生活"]
    assert TAG_BY_KEY["mood_happy"].label == "开心"
    assert TAG_BY_KEY["ovu_positive"].label == "阳性"


def test_today_page_uses_readable_chinese_text(client, db):
    _login(client, db)

    response = client.get("/", headers={"Accept": "text/html"})

    assert response.status_code == 200
    body = response.text
    assert "今天" in body
    assert "快捷记录" in body
    assert "今天的标签" in body
    assert "基础体温" in body
    assert "浠婂ぉ" not in body


def test_bottom_nav_uses_readable_chinese_text(client, db):
    _login(client, db)

    response = client.get("/", headers={"Accept": "text/html"})

    assert response.status_code == 200
    body = response.text
    for label in ["今天", "日历", "记录", "经期", "体温", "我们"]:
        assert label in body
    assert "馃" not in body

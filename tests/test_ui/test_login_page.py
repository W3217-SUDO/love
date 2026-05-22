def test_login_page_renders_form(client):
    r = client.get("/login")
    assert r.status_code == 200
    body = r.text
    assert 'name="username"' in body
    assert 'name="password"' in body
    assert 'action="/login"' in body or 'data-action="/login"' in body
    assert "Couple Diary" in body or "登录" in body

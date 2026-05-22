def test_static_css_served(client):
    r = client.get("/static/css/theme.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    body = r.text
    # Flo pink theme tokens must be present
    assert "--color-bg" in body
    assert "--color-accent" in body
    assert "#ff7a9c" in body or "rgb(255, 122, 156)" in body.lower()


def test_manifest_served(client):
    r = client.get("/static/manifest.webmanifest")
    assert r.status_code == 200
    assert "application/manifest+json" in r.headers["content-type"] or "json" in r.headers["content-type"]
    import json
    data = json.loads(r.text)
    assert data["name"]
    assert data["short_name"]
    assert "icons" in data
    assert data["display"] == "standalone"
    assert data["theme_color"]


def test_root_renders_base_with_pwa_meta(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    # PWA meta tags
    assert '<meta name="viewport"' in body
    assert 'manifest' in body and 'manifest.webmanifest' in body
    assert 'theme-color' in body
    # Flo theme CSS link
    assert 'theme.css' in body
    # HTMX + Alpine (vendored or CDN — we accept either reference)
    assert 'htmx' in body.lower()
    assert 'alpine' in body.lower()
    # base nav slot rendered
    assert 'data-nav' in body

def test_service_worker_served_at_root_scope(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    # Service workers MUST be served with a JS-ish content-type
    ct = r.headers["content-type"]
    assert "javascript" in ct or "application/javascript" in ct
    # Service-Worker-Allowed header lets a /sw.js worker control the entire site
    # (though we serve at root anyway, this is a forward-compat header).
    assert r.headers.get("service-worker-allowed", "/") == "/"
    body = r.text
    assert "self.addEventListener" in body or "addEventListener" in body
    # M1 SW: very minimal — at least handle 'install' and 'fetch' events
    assert "install" in body
    assert "fetch" in body

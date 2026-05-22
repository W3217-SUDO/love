"""Rate limiter setup (slowapi).

We use the in-memory backend - fine for a single-process, single-server
deployment. Multi-process would need Redis, but FastAPI/Uvicorn runs in a
single worker by default in our systemd unit (workers=2 ok but the limiter
is per-process; sufficient since brute force is dominated by Argon2 cost
in either case).
"""
import warnings

from slowapi import Limiter
from slowapi.util import get_remote_address

# Key by client IP. behind nginx, we trust X-Forwarded-For via proxy_set_header
# (configured in T55) - slowapi reads request.client.host which FastAPI
# populates from the proxy headers when --proxy-headers is set.
#
# We pass an explicit non-existent config_filename to bypass slowapi's auto
# .env loading: our repo's .env contains UTF-8 paths with non-ASCII chars
# and starlette's Config opens it with the system locale (gbk on Windows),
# which crashes during import. Our app config is read via app.config, not
# via slowapi, so this loader is unnecessary anyway.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[],
        config_filename="__slowapi_no_env__",
    )

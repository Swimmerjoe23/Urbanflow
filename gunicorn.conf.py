"""Gunicorn config, auto-loaded from the working directory regardless of
the exact start command used to invoke gunicorn (no -c flag needed).

timeout is the important one here: OSMnx network fetches can take well
over gunicorn's 30s default for anything but a tiny bounding box, and a
worker that exceeds the timeout gets killed mid-request — which the
browser sees as the connection just dying, not a clean error response.
"""

workers = 2
timeout = 120

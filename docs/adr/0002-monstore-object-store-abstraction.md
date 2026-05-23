# Monstore stores assets through obstore, not a hard-coded filesystem

Asset bytes (sprites, sheets, poses, cries) are read and written through `obstore` behind a single `settings.asset_store_url`, so the same code targets `file://`, `s3://`, `gs://`, `az://`, or `memory:///` without schema or call-site changes. The alternative — embedding filesystem paths in models — would lock deployment to one backend and make local-vs-cloud parity a code change rather than a config change. See `app/storage/monstore.py` and `app/settings.py:34`.


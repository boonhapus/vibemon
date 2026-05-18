# Wild catching concurrency is first-success-wins

The catch mechanic is deferred, and the first implementation should reserve language only rather than adding catch APIs or service placeholders. When catch exists, it is valid only during battle and only against **Wild** Vibemon. If multiple trainers concurrently attempt to catch and adopt the same wild Vibemon, only the first successful adoption transitions it from **Wild** to **Owned**. Later attempts fail because the Vibemon is no longer wild; player-facing copy should say it got away.

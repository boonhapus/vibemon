# Rejected candidates decay back into encounters

A trainer who rejects a generated candidate may encounter that Vibemon later after it enters the wild pool, but rejection applies a trainer-specific encounter adjustment starting at `0.00x` encounter weight and continuously decaying back to normal over a randomly assigned 1-3 day window. Candidate review timeout uses the same adjustment because it is a passive rejection. This keeps rejected known-good generations useful as wild content while making immediate resurfacing effectively unavailable without creating a separate hard-ban mechanism.

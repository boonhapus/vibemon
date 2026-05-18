# Encounter queries select only eligible wild Vibemon

Wild encounter selection should query only eligible **Wild** Vibemon, excluding candidate-review records and **Expired** Vibemon before weighting. The service still revalidates disposition before final selection because ownership, expiration, or candidate resolution can change after the query runs.

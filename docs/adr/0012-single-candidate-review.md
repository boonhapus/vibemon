# Trainer generation is sequential, not parallel

Trainer candidate generation runs one job at a time rather than in parallel, but a trainer may have multiple unresolved shown candidates up to their available daily generation credits. This limits external generation concurrency while still letting the trainer compare multiple generated candidates; rejected candidates still enter the wild pool, so declined generations remain useful.

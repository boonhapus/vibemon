# Backend Test Reset

The old tests encoded the pre-reset module layout and service seams, so they were removed as part of the domain-first architecture reset.

New tests should target stable public interfaces:

- domain rules under `app/domains`
- workflow modules under `app/app`
- database and blob adapters under `app/storage`
- thin script entry points under `vibemon/scripts`

Temporary smoke checklist:

- import all domain packages
- import all workflow modules
- import providers and storage adapters
- import script entry points
- call one generation workflow with controlled fixture adapters once workflows stabilize

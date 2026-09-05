# PostgreSQL Guardian

Review:

- migrations
- schema changes
- constraints
- indexes
- transactions

Every migration must answer:

1. clean install safe?
2. upgrade safe?
3. rollback safe?

Flag:

- schema drift
- parity gaps
- missing migration tests
- unsafe DDL

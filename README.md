# Job Posting Change Tracker

Job Board Tracker (WIP)

A backend service that aggregates job postings from multiple sources (Greenhouse, Lever TODO, etc)
Postings are normalized into a schema and stored for querying, and in the future tracking applications and analysis. 

Goals:

1) Aggregate job postings from multiple sources. 

2) Normalize data into a consistent model. 

3) Store data in DB, currently PostgreSQL

4) Track job postings over time for key companies (TODO)

5) Provide REST API for querying jobs and companies. 


Current Stack:

Python
Fastapi
PostgreSQL
SQLAlchemy
Docker
Redis(planned)
AWS Deployment (planned)

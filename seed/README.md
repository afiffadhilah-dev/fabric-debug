# Database Seeding

This folder contains scripts for seeding the database with sample data.

## Structure

```
seed/
├── __init__.py          # Package initialization
├── candidate_seed.py    # Seeding for candidate data
├── run_all.py          # Runner to execute all seeds
└── README.md           # This documentation
```

## Usage

### Running All Seeds

To run all seeding operations at once:

```bash
python -m seed.run_all
```

### Running Specific Seed

To run only the candidate seeding:

```bash
python -m seed.candidate_seed
```

### From Python Code

```python
from seed import seed_candidates

# Seed candidates
seed_candidates()
```

## Adding New Seeds

To add a new seeder (for example, for projects or job postings):

1. Create a new file, example: `seed/project_seed.py`
2. Create a seeding function, example:
   ```python
   def seed_projects():
       """Seed projects data."""
       # Your seeding logic here
       pass
   ```
3. Export in `seed/__init__.py`:
   ```python
   from .project_seed import seed_projects
   __all__ = ['seed_candidates', 'seed_projects']
   ```
4. Add to `seed/run_all.py`:
   ```python
   from .project_seed import seed_projects
   
   def run_all_seeds():
       seed_candidates()
       seed_projects()  # Add here
   ```

## Sample Data

### Candidates (10 candidates)

The `candidate_seed.py` script contains 10 sample candidates with various roles:
- Full Stack Developer
- Data Scientist
- Backend Developer
- Frontend Developer
- DevOps Engineer
- Mobile Developer
- Database Administrator
- QA Engineer
- Software Architect
- Product Manager

Each candidate has a complete description of their skills and experience.

## Notes

- Make sure the database has been migrated before running seeds:
  ```bash
  alembic upgrade head
  ```
- Make sure `.env` is properly configured (DATABASE_URL, API keys, etc.)
- Seeding will create new data, it will not update existing data
- To reset the database, drop and recreate the database, then run migrations and seeding again

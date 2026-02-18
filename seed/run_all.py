"""
Main seed runner script.
This script runs all seeding operations in the correct order.
"""

from .candidate_seed import seed_candidates


def run_all_seeds():
    """Run all seed operations."""
    print("=" * 60)
    print("STARTING ALL SEEDING OPERATIONS")
    print("=" * 60)
    print()
    
    # Run candidate seeding
    seed_candidates()
    
    # Add more seed operations here as needed
    # Example:
    # seed_projects()
    # seed_job_postings()
    
    print()
    print("=" * 60)
    print("ALL SEEDING OPERATIONS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_seeds()

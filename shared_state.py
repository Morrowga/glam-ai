# Shared in-memory state between main.py and worker.py
# Worker checks this set mid-flight to abort cancelled jobs

cancelled_jobs: set[str] = set()
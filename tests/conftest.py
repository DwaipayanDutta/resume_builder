import os
import tempfile
from pathlib import Path

# Use a throwaway accounts database for the whole test run (set before the app is imported).
os.environ["RESUME_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="rs_test_db_")) / "studio.db")

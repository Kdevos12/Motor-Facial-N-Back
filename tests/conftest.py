import os
import tempfile

# Keep tests away from the user's real data directory (profiles, imported packs).
os.environ["MFNB_HOME"] = tempfile.mkdtemp(prefix="mfnb-test-")

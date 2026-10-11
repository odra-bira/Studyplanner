import sys
from pathlib import Path

# Let tests import the `app` package when pytest runs from the backend folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

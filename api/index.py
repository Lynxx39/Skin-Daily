import sys
import os

# Add the root directory to the python path so we can import the backend package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

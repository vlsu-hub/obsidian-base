import sys
from pathlib import Path

script_dir = Path(__file__).parent.parent / "scripts"
sys.path.append(str(script_dir.resolve()))

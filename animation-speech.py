#!/usr/bin/env python3
"""Development wrapper — run the package directly."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animation_speech.main import main
main()

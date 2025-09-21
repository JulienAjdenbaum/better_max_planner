#!/usr/bin/env python3
"""
TGV Max Trip Planner - Main Entry Point
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5163, debug=False)

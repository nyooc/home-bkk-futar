#!/usr/bin/env python
"""Entry point for infinite operation"""
from dotenv import load_dotenv

load_dotenv()

from home_bkk_futar.matrix import run


if __name__ == "__main__":
    run()

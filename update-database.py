#!/usr/bin/env python
import os
import sys
from figment import app

if __name__ == "__main__":
    from cptmatch.update_database import *
    init_database()
    import_data()

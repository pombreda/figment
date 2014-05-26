#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "figment.settings")
    from cptmatch.update_database import *
    import_data()

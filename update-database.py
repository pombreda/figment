#!/usr/bin/env python
import os
import sys
from figment import app

if __name__ == "__main__":
    from cptmatch.update_database import *
    dupd = DatabaseUpdater()
    dupd.init_database()
    dupd.import_data()

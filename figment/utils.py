from gi.repository import Appstream

as_database = None

def get_db():
    global as_database
    if not as_database:
        as_database = Appstream.Database.new()
        as_database.open()
    return as_database

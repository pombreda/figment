
from flask.ext.sqlalchemy import SQLAlchemy
from figment import app

db = SQLAlchemy(app)
xadd = False

def init_db(app):
    global db
    global xadd
    from models import Component, ComponentVersion, Distribution, ProvidedItem, DistroPackage

    db.create_all()

    if not xadd:
        xadd = True

        cpt = Component(identifier='test', name='Ed Jones', summary='edspassword')
        ver = ComponentVersion(version="1.0")
        cpt.versions.append(ver)

        cpt2 = Component(identifier='test2', name='dhnfhm', summary='dfbfgn ')
        ver2 = ComponentVersion(version="2.0")
        cpt2.versions.append(ver2)

        db.session.add_all([cpt, ver, cpt2, ver2])

        db.session.commit()

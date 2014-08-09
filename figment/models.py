
from database import db
from sqlalchemy import Column, Integer, String

class Component(db.Model):
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    identifier = Column(String, unique=True)
    kind = Column(String)
    name = Column(String)
    summary = Column(String)
    description = Column(String)
    icon_url = Column(String)
    license = Column(String)
    homepage = Column(String)
    versions = db.relationship('ComponentVersion', backref='component',
                                lazy='dynamic', cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Component(uid='%s', name='%s', summary='%s')>" % (
                             self.identifier, self.name, self.summary)

class ComponentVersion(db.Model):
    __tablename__ = 'component_versions'

    id = Column(Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    version = Column(String)

    provided_items = db.relationship('ProvidedItem', backref='version',
                                lazy='dynamic', cascade="all, delete, delete-orphan")
    packages = db.relationship('DistroPackage', backref='component_version',
                                lazy='dynamic', cascade="all, delete, delete-orphan")

class ProvidedItem(db.Model):
    __tablename__ = 'provided_items'

    id = Column(Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('component_versions.id'))
    kind = Column(String)
    value = Column(String)

class Distribution(db.Model):
    __tablename__ = 'distributions'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    version = Column(String)
    codename = Column(String)

    packages = db.relationship('DistroPackage', backref='distribution',
                                lazy='dynamic', cascade="all, delete, delete-orphan")

class DistroPackage(db.Model):
    __tablename__ = 'distro_packages'

    id = Column(Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('component_versions.id'))
    distro_id = db.Column(db.Integer, db.ForeignKey('distributions.id'))

    pkgname = Column(String)
    package_url = Column(String)

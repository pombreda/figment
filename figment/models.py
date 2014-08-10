
import json
from database import db
from sqlalchemy import Column, Integer, String, Boolean

class Component(db.Model):
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    identifier = Column(String, unique=True)
    kind = Column(String)
    name = Column(String)
    summary = Column(String)
    description = Column(String)
    icon_url = Column(String)
    developer_name = Column(String)
    license = Column(String)
    homepage = Column(String)
    highest_version = Column(String)
    versions = db.relationship('ComponentVersion', backref='component',
                                lazy='dynamic', cascade="all, delete, delete-orphan")
    screenshots = db.relationship('Screenshot', backref='component',
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

class Screenshot(db.Model):
    __tablename__ = 'screenshots'

    id = Column(Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    default = Column(Boolean)
    caption = Column(String)
    images = Column(String)

    _img_data = list()

    def set_image_data(self, data):
        self._img_data = data
        self.images = json.dumps(self._img_data)

    def get_image_data(self):
        if not self._img_data:
            self._img_data = json.loads(self.images)
        return self._img_data

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

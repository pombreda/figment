
from figment.database import db
from figment.models import *
from gi.repository import Appstream
from distutils.version import LooseVersion
from figment import app
import shutil
import os

#from debian import *
from fedora import *
from tanglu import *

class DatabaseUpdater:
    def __init__(self):
        self.icon_cache_path = os.path.join(app.root_path, "..", "static", "images", "cpt-icons")

    def init_database(self):
        db.create_all()
        db.session.commit()

    def update_components_packages(self, distro):
        distro_name = distro.get_name()
        print("Adding data for: %s" % (distro_name))

        for pkg in distro.get_components_packages():
            cpt = pkg.cpt
            pkgname = pkg.name
            identifier = cpt.get_id().decode("utf-8")
            dbcpt = db.session.query(Component).filter_by(identifier=identifier).first()
            if not dbcpt:
               dbcpt = Component()
               dbcpt.identifier = identifier
               db.session.add(dbcpt)
               db.session.flush()

            # only update if we have new data
            if (not dbcpt.highest_version) or (pkg.upstream_version > LooseVersion(dbcpt.highest_version)):
                dbcpt.kind = Appstream.ComponentKind.to_string(cpt.get_kind()).decode("utf-8")
                dbcpt.identifier = identifier
                dbcpt.name = cpt.get_name().decode("utf-8")
                dbcpt.summary = cpt.get_summary().decode("utf-8")
                developer_name = cpt.get_developer_name()
                if developer_name:
                    developer_name = developer_name.decode("utf-8")
                dbcpt.developer_name = developer_name

                dbcpt.highest_version = str(pkg.upstream_version)

                screenshots = cpt.get_screenshots()
                dbcpt.screenshots = list()
                for shot in screenshots:
                    dbshot = Screenshot()
                    dbshot.default = shot.get_kind() == Appstream.ScreenshotKind.DEFAULT
                    dbshot.caption = shot.get_caption().decode("utf-8")
                    imgdata = list()
                    for img in shot.get_images():
                        d = dict()
                        d['kind'] = Appstream.Image.kind_to_string(img.get_kind())
                        if not d['kind']:
                            continue
                        d['kind'] = d['kind'].decode("utf-8")
                        d['url'] = img.get_url().decode("utf-8")
                        d['width'] = img.get_width()
                        d['height'] = img.get_height()
                        imgdata.append(d)
                    if imgdata:
                        dbshot.set_image_data(imgdata)
                        dbcpt.screenshots.append(dbshot)

                cptdesc = cpt.get_description().decode("utf-8").replace('\n', "<br/>")
                dbcpt.description = cptdesc

                license = cpt.get_project_license()
                if license:
                    license = license.decode("utf-8")
                dbcpt.license = license
                homepage = cpt.get_url(Appstream.UrlKind.HOMEPAGE)
                if homepage:
                    homepage = homepage.decode("utf-8")
                else:
                    homepage = "#"
                dbcpt.homepage = homepage

                icon_url = cpt.get_icon_url().decode("utf-8")
                # remove old icon
                if dbcpt.icon_url:
                    icon_dest = os.path.join(self.icon_cache_path, dbcpt.icon_url)
                    if os.path.isfile(dbcpt.icon_url):
                        os.remove(dbcpt.icon_url)

                dbcpt.icon_url = os.path.basename(icon_url)
                icon_dest = os.path.join(self.icon_cache_path, dbcpt.icon_url)
                try:
                    shutil.copyfile(icon_url, icon_dest)
                except:
                    dbcpt.icon_url = ""

            dbdistro = db.session.query(Distribution).filter_by(codename=pkg.distro_release, name=distro_name).first()
            if not dbdistro:
               continue
            ver = db.session.query(ComponentVersion).filter_by(component_id=dbcpt.id, version=pkg.upstream_version).first()

            if not ver:
                ver = ComponentVersion()
                db.session.add(ver)
                dbcpt.versions.append(ver)
                ver.version = pkg.upstream_version
                db.session.flush()
            ver.version = pkg.upstream_version

            dpk = db.session.query(DistroPackage).filter_by(version_id=ver.id, distro_id=dbdistro.id).first()
            if not dpk:
                dpk = DistroPackage()
                ver.packages.append(dpk)
                dbdistro.packages.append(dpk)
                dpk.pkgname = pkg.name
                dpk.package_url = pkg.url
                db.session.add(dpk)
                db.session.flush()

            for item_id in cpt.get_provided_items():
                kind = Appstream.provides_item_get_kind(item_id)
                kind_str = Appstream.provides_kind_to_string(kind).decode("utf-8")
                value = Appstream.provides_item_get_value(item_id)
                if not value:
                    continue
                value = value.decode("utf-8")

                pitem = db.session.query(ProvidedItem).filter_by(version_id=ver.id, kind=kind_str, value=value).first()
                # in case this item already exists, we move on
                if pitem:
                    continue
                pitem = ProvidedItem()

                ver.provided_items.append(pitem)
                pitem.kind = kind_str
                pitem.value = value
                db.session.add(pitem)
    db.session.commit()

    def import_data(self):
        distros = list()
        #distros.append(DebianDataRetriever())
        distros.append(FedoraDataRetriever())
        distros.append(TangluDataRetriever())

        for distro in distros:
            distro.update_caches()
            for release in distro.get_releases():
                d = db.session.query(Distribution).filter_by(codename=release['codename'], name=distro.get_name()).first()
                if d:
                   continue
                d = Distribution()
                d.name = distro.get_name()
                d.codename = release['codename']
                d.version = release['version']
                db.session.add(d)
                db.session.flush()
        # finalize and commit data
        for distro in distros:
            self.update_components_packages(distro)
        db.session.commit()

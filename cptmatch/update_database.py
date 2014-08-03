
from figment.database import db
from figment.models import *
from gi.repository import Appstream

from distro.debian import *
from distro.fedora import *
from distro.tanglu import *

def process_distro(distro):
    print("Collecting component information")
    dpool = Appstream.DataPool.new()

    dpool.set_data_source_directories(distro.get_metadata_paths())

    dpool.initialize()
    dpool.update()

    cpts = dpool.get_components()

    print("Processing data for %s" % (distro.get_name()))
    for cpt in cpts:
        identifier = cpt.get_id().decode("utf-8")
        dbcpt = db.session.query(Component).filter_by(identifier=identifier).first()
        if not dbcpt:
            dbcpt = Component()
            db.session.add(dbcpt)
        dbcpt.kind = Appstream.ComponentKind.to_string(cpt.get_kind()).decode("utf-8")
        dbcpt.identifier = identifier
        dbcpt.name = cpt.get_name().decode("utf-8")
        dbcpt.summary = cpt.get_summary().decode("utf-8")

        cptdesc = cpt.get_description().decode("utf-8").replace('\n', "<br/>")
        dbcpt.description = cptdesc

        dbcpt.license = cpt.get_project_license().decode("utf-8")
        homepage = cpt.get_url(Appstream.UrlKind.HOMEPAGE)
        if homepage:
            homepage = homepage.decode("utf-8")
        else:
            homepage = "#"
        dbcpt.homepage = homepage
        dbcpt.icon_url = cpt.get_icon_url().decode("utf-8")

        # we can only have one package name per component
        pkgname = cpt.get_pkgnames()[0]
        if pkgname:
            pkgname = pkgname.decode("utf-8")

        pkgs = distro.get_packages_info(pkgname)
        for pkg in pkgs:
            dbdistro = db.session.query(Distribution).filter_by(codename=pkg.codename, name=distro.get_name()).first()
            if not dbdistro:
               continue
            ver = db.session.query(ComponentVersion).filter_by(component_id=dbcpt.id, version=pkg.version_upstream).first()

            if not ver:
                ver = ComponentVersion()
                db.session.add(ver)
            dbcpt.versions.append(ver)
            ver.version = pkg.version_upstream

            dpk = db.session.query(DistroPackage).filter_by(version_id=ver.id, distro_id=dbdistro.id).first()
            if not dpk:
                dpk = DistroPackage()
                ver.packages.append(dpk)
                dbdistro.packages.append(dpk)
                dpk.package_url = pkg.url
                db.session.add(dpk)

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

def init_database():
    db.create_all()
    db.session.commit()

def import_data():
    distros = list()
    distros.append(DebianPkgInfoRetriever())
    #distros.append(FedoraPkgInfoRetriever())
    distros.append(TangluPkgInfoRetriever())

    for distro in distros:
        for release in distro.get_releases():
            d = db.session.query(Distribution).filter_by(codename=release['codename'], name=distro.get_name()).first()
            if d:
               continue
            d = Distribution()
            d.name = distro.get_name()
            d.codename = release['codename']
            d.version = release['version']
            db.session.add(d)
            db.session.commit()
        distro.update_caches()
        process_distro(distro)
    db.session.commit()


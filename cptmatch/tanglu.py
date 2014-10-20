
from helpers.distro import *
import gzip
import re
from apt_pkg import TagFile, version_compare, init
import requests
import os

def package_list_to_dict(pkg_list):
    pkg_dict = dict()
    for pkg in pkg_list:
        # replace it only if the version of the new item is higher (required to handle epoch bumps and new uploads)
        if pkg.pkgname in pkg_dict:
            regVersion = pkg_dict[pkg.pkgname].version
            compare = version_compare(regVersion, pkg.version)
            if compare >= 0:
                continue
        pkg_dict[pkg.pkgname] = pkg
    return pkg_dict

class TangluDataRetriever(DistroDataRetriever):
    def __init__(self):
        DistroDataRetriever.__init__(self, "Tanglu")
        self._packages = None
        self._archive_components = ["main", "contrib", "non-free"]

    def get_releases(self):
        releases = list()
        for suite in self.config['suites']:
            releases.append({'codename': suite['name'], 'version': suite['version']})
        return releases

    def update_caches(self):
        cache_dir = self.get_cache_path()
        for suite in self.config['suites']:
            for component in ["main", "contrib", "non-free"]:
                url = "%s/tanglu/dists/%s/%s/binary-amd64/Packages.gz" % (self.config['archive_url'], suite['name'], component)
                save_dir = os.path.join(cache_dir, suite['name'], component)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                r = requests.get(url)
                with open(os.path.join(save_dir, "Packages-amd64.gz"), "wb") as code:
                    code.write(r.content)

    def _get_upstream_version (self, version):
        v = no_epoch(version)
        if "-" in v:
            v = v[:v.index("-")]
        return v

    def get_components_packages(self):
        pkgs = list()
        for suite in self.config['suites']:
            suite_name = suite['name']
            metadatadir = os.path.join(self.get_metadata_path(), suite_name)

            # get list of AppStream components for the given distro
            ascpts = self.get_appstream_components(metadatadir)

            for archive_component in self._archive_components:
                index_path = os.path.join(self.get_cache_path(), suite_name, archive_component, "Packages-amd64.gz")

                f = gzip.open(index_path, 'rb')
                tagf = TagFile(f)
                for section in tagf:
                    pkgversion = section.get('Version')
                    if not pkgversion:
                        print("Tanglu: Bad package data found!")
                    pkgname = section['Package']
                    cpt = ascpts.get(pkgname)
                    if not cpt:
                        continue
                    pkg = PackageInfo(pkgname,
                              pkgversion,
                              self._get_upstream_version(pkgversion),
                              "unknown-amd64",
                              suite_name)
                    pkg.url = "http://packages.tanglu.org/%s/%s" % (suite_name, pkgname)
                    pkg.cpt = cpt
                    pkgs.append(pkg)
        return pkgs

### apt_pkg needs to be initialized
init()

if __name__ == '__main__':
    test = TangluDataRetriever()
    print(test.get_components_packages())

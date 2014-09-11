
from helpers import *
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

class DebianPkgInfoRetriever(PkgInfoRetriever):
    def __init__(self):
        PkgInfoRetriever.__init__(self, "Debian")
        self._packages = None

    def get_releases(self):
        releases = list()
        for suite in self.config['suites']:
            releases.append({'codename': suite['name'], 'version': suite['version']})
        return releases

    def update_caches(self):
        cache_dir = self.get_cache_path()
        for suite in self.config['suites']:
            for component in ["main", "contrib", "non-free"]:
                url = "%s/debian/dists/%s/%s/binary-amd64/Packages.gz" % (self.config['archive_url'], suite['name'], component)
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

    def _get_packages_for(self, suite, component):
        index_path = os.path.join(self.get_cache_path(), suite, component, "Packages-amd64.gz")

        f = gzip.open(index_path, 'rb')
        tagf = TagFile(f)
        package_list = list()
        for section in tagf:
            pkgversion = section.get('Version')
            if not pkgversion:
                print("Debian: Bad package data found!")
            pkgname = section['Package']
            pkg = PackageInfo(pkgname,
                              pkgversion,
                              self._get_upstream_version(pkgversion),
                              suite,
                              component)
            pkg.url = "https://packages.debian.org/%s/%s" % (suite, pkgname)

            package_list.append(pkg)
        packages_dict = package_list_to_dict(package_list)

        return packages_dict

    def _initialize(self):
        self._packages = dict()
        for suite in self.config['suites']:
            suite_name = suite['name']
            self._packages[suite_name] = dict()
            for component in ["main", "contrib", "non-free"]:
                pkg_dict = self._get_packages_for(suite_name, component)
                self._packages[suite_name] = dict(pkg_dict.items() + self._packages[suite_name].items())


    def get_packages_info(self, pkgname):
        if not self._packages:
            self._initialize()
        pkgs = list()
        for suite in self.config['suites']:
            suite_name = suite['name']
            pkg = self._packages[suite_name].get(pkgname)
            if pkg:
                pkgs.append (pkg)
        return pkgs

    def get_metadata_paths(self):
        return [os.path.join(self.get_cache_path(), "metadata")]


### apt_pkg needs to be initialized
init()

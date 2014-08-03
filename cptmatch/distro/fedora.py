
from distro import *
import requests
import os
import json

BASE_URL = "https://apps.fedoraproject.org/packages/fcomm_connector"

def _make_request(path, query):
    """ Internal util function to make a request of the connector API. """
    query_as_json = json.dumps(query)
    url = "/".join([BASE_URL, path, query_as_json])
    response = requests.get(url)
    d = response.json

    if callable(d):
        d = d()

    return d

class FedoraPkgInfoRetriever(PkgInfoRetriever):
    def __init__(self):
        PkgInfoRetriever.__init__(self, "Fedora")

    def get_releases(self):
        releases = list()
        for release in self.config['releases']:
            releases.append({'codename': release['name'], 'version': release['version']})
        return releases

    def update_caches(self):
        return

    def _get_upstream_version (self, version):
        v = no_epoch(version)
        if "-" in v:
            v = v[:v.index("-")]
        return v

    def get_packages_info(self, pkgname):
        path = "bodhi/query/query_active_releases"
        query = {
            "filters": {"package": pkgname},
            "rows_per_page": 1,
            "start_row": 1,
        }

        rel_data = _make_request(path, query)
        pkgs = list()
        for release in rel_data['rows']:
            version = release['stable_version']
            if not version:
                continue
            pkg = PackageInfo(pkgname,
                              version,
                              self._get_upstream_version(version),
                              release['release'],
                              "main")
            pkg.url = "https://apps.fedoraproject.org/packages/%s" % (pkgname)
            pkgs.append(pkg)
        return pkgs

    def get_metadata_paths(self):
        return [os.path.join(self.get_cache_path(), "metadata")]

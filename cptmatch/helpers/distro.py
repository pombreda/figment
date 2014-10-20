
import yaml
import os
from gi.repository import Appstream
from distutils.version import LooseVersion

def no_epoch(version):
    v = version
    if ":" in v:
        return v[v.index(":")+1:]
    else:
        return v

class PackageInfo():
    def __init__(self, name, version, upstream_version, arch, distro_release):
        self.name = name
        self.version = version
        self.arch = arch
        self.source_package = None
        self.upstream_version = upstream_version
        self.distro_release = distro_release

        self.url = "#"

        self.cpt = None

    def to_yaml(self):
        data = dict()
        data['Package'] = self.name
        data['Version'] = self.version
        data['UpstreamVersion'] = self.upstream_version
        data['Architecture'] = self.arch
        data['DistroRelease'] = self.distro_release
        data['Url'] = self.url
        if self.source_package:
            data['Source'] = self.source_package

        return yaml.dump(data, indent=2, default_flow_style=False, explicit_start=True)

    def __str__(self):
        return "Package { name: %s | version: %s }" % (self.pkgname, self.version)

class DistroDataRetriever():
    def __init__(self, distro_name):
        self._conf = yaml.safe_load(open("%s/%s" % (self._get_config_path(), 'distributions.yml'), 'r'))
        self._distro_name = distro_name
        cache_path = self.get_cache_path()
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)

    @property
    def config(self):
        return self._conf[self._distro_name]

    def get_cache_path(self):
        path = os.path.join (os.path.dirname(__file__), "..", "..", "cache", self._distro_name)
        return os.path.abspath(path)

    def _get_config_path(self):
        path = os.path.join (os.path.dirname(__file__), "..", "..", "config")
        return os.path.abspath(path)

    def get_name(self):
        return self._distro_name

    def update_caches(self):
        """ Update the cached AppStream and package information """
        pass

    def get_components_packages(self):
        return list()

    def get_releases(self):
        """ Get releases of this distribution """
        releases = list()
        for release in self.config['releases']:
            releases.append({'codename': str(release['name']), 'version': release['version']})
        return releases

    def get_metadata_path(self):
        return os.path.join(self.get_cache_path(), "metadata")

    def get_appstream_components(self, metadata_path):
        dpool = Appstream.DataPool.new()
        dpool.set_data_source_directories([metadata_path])
        dpool.set_locale("C")

        dpool.initialize()
        dpool.update()

        res = dict()
        cpts = dpool.get_components()
        for cpt in cpts:
            identifier = cpt.get_id().decode("utf-8")

            # we can only have one package name per component
            pkgname = cpt.get_pkgnames()[0]
            if pkgname:
                pkgname = pkgname.decode("utf-8")
            else:
                continue
            res[pkgname] = cpt
        return res

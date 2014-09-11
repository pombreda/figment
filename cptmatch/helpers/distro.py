
import yaml
import os

def no_epoch(version):
    v = version
    if ":" in v:
        return v[v.index(":")+1:]
    else:
        return v

class PackageInfo():
    def __init__(self, name, version, upstream_version, arch, source_package):
        self.name = name
        self.version = version
        self.arch = arch
        self.source_package = source_package
        self.upstream_version = upstream_version

        self.url = "#"

    def to_yaml(self):
        data = dict()
        data['Package'] = self.name
        data['Version'] = self.version
        data['UpstreamVersion'] = self.upstream_version
        data['Architecture'] = self.arch
        data['SourcePackage'] = self.source_package
        data['Url'] = self.url

        return yaml.dump(data, indent=2, default_flow_style=False, explicit_start=True)

    def __str__(self):
        return "Package { name: %s | version: %s }" % (self.pkgname, self.version)

class PkgInfoRetriever():
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
        pass

    def get_packages_info(self, pkgname):
        return list()

    def get_releases(self):
        pass

    def get_metadata_paths(self):
        return [os.path.join(self.get_cache_path(), "metadata")]

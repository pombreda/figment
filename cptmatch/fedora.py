
from helpers.distro import *
from helpers.rpm_export import RpmMd, RpmMdException
import os
import sys
from urllib2 import urlopen
import re
import libarchive
import gzip

class FedoraComponentInfoRetriever(ComponentInfoRetriever):
    def __init__(self):
        ComponentInfoRetriever.__init__(self, "Fedora")

    def update_caches(self):
        for r in self.config['releases']:
            fedora_release = str(r['version'])
            cachedir = os.path.join(self.get_cache_path(), "tmp")
            metadatadir = os.path.join(self.get_metadata_path(), fedora_release)

            if r.get('development'):
                repo_url = "http://dl.fedoraproject.org/pub/fedora/linux/development/%s/x86_64/os/" % (fedora_release)
            else:
                repo_url = "http://dl.fedoraproject.org/pub/fedora/linux/releases/%s/Fedora/x86_64/os/" % (fedora_release)

            metadata = RpmMd(repo_url, cachedir)
            try:
                metadata.fetch_and_parse()
            except RpmMdException as e:
                metadata.cleanup()
                print(e)
                sys.exit(2)

            outdir = os.path.join(self.get_cache_path(), "packages", fedora_release)
            metadata.export_data(fedora_release, "fedora", outdir=outdir)
            metadata.cleanup(keep_cache=True)

            # download AppStream data
            urlpath = urlopen(os.path.join(repo_url, "Packages/a/"))
            string = urlpath.read().decode('utf-8')

            pattern = re.compile('appstream-data.*.noarch.rpm"')
            filelist = pattern.findall(string)
            if not filelist:
                continue

            filename = filelist[0][:-1]
            remotefile = urlopen(os.path.join(repo_url, "Packages/a/", filename))

            tmpfile = os.path.join(cachedir, filename)
            localfile = open(tmpfile,'wb')
            localfile.write(remotefile.read())
            localfile.close()
            remotefile.close()

            common_prefix = "./usr/share/app-info/"
            with libarchive.SeekableArchive(tmpfile) as a:
                for entry in a:
                    path = os.path.join(metadatadir, os.path.relpath(entry.pathname, common_prefix))
                    if entry.isdir():
                        if not os.path.exists(path):
                            os.makedirs(path)
                    else:
                        f = open(path, 'wb')
                        f.write(a.read(entry.pathname))
                        f.close()


    def _get_upstream_version (self, version):
        v = no_epoch(version)
        if "-" in v:
            v = v[:v.index("-")]
        return v

    def get_components_packages(self):
        for rel in self.config['releases']:
            fedora_release = str(rel['version'])
            pkgcache = os.path.join(self.get_cache_path(), "packages", fedora_release, "dist-%s" % (fedora_release))
            metadatadir = os.path.join(self.get_metadata_path(), fedora_release)

            # get list of AppStream components for the given distro
            ascpts = self.get_appstream_components(metadatadir)

            pkgs = list()
            docs = list()
            try:
                docs = yaml.load_all(gzip.open(os.path.join(pkgcache, "packages.gz"), 'r'))
            except:
                print("Skipping Fedora %s: No packages found" % (fedora_release))
            for doc in docs:
                pkgname = doc['Package']
                cpt = ascpts.get(pkgname)
                if not cpt:
                    continue
                pkg = PackageInfo(pkgname,
                              doc['Version'],
                              doc['UpstreamVersion'],
                              fedora_release,
                              "main")
                pkg.url = "https://apps.fedoraproject.org/packages/%s" % (pkgname)
                pkg.cpt = cpt
                pkgs.append(pkg)
        return pkgs

if __name__ == '__main__':
    test = FedoraComponentInfoRetriever()
    print test.get_components_packages()

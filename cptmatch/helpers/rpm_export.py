#!/usr/bin/python
# vim: set ts=4 sw=4 et: coding=UTF-8
#
# Copyright (c) 2012 SUSE
# Copyright (c) 2014 Matthias Klumpp <matthias@tenstral.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Vincent Untz <vuntz@opensuse.org>"
__license__ = """
    Copyright (C) 2012 Vincent Untz <vuntz@opensuse.org>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import os
import sys

import errno
import gzip
import hashlib
import logging
import operator
import optparse
import re
import shutil
import tempfile
import urlparse
import urllib2

from posixpath import join as posixjoin # Handy for URLs

from distro import PackageInfo

try:
    from lxml import etree as ET
except ImportError:
    try:
        from xml.etree import cElementTree as ET
    except ImportError:
        import cElementTree as ET

RPM_MD_NS='{http://linux.duke.edu/metadata/common}'
RPM_MD_NS_REPO='{http://linux.duke.edu/metadata/repo}'
RPM_MD_NS_RPM='{http://linux.duke.edu/metadata/rpm}'
RPM_MD_NS_FILELISTS='{http://linux.duke.edu/metadata/filelists}'

KNOWN_METADATA_TYPE = ['rpm-md', 'yast2']

log = logging.getLogger(__name__)


class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"


def get_hash_from_file(algo, path):
    """ Return the hash of a file, using the specified algorithm. """
    if not os.path.exists(path):
        return None

    # hashlib.algorithms is from python 2.7; for earlier versions, just
    # hardcode the default list of algorithms
    if hasattr(hashlib, 'algorithms'):
        algorithms = hashlib.algorithms
    else:
        algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

    if algo not in algorithms:
        print >>sys.stderr, 'Cannot compute hash with hash algorithm: %s' % algo
        return None

    hash = hashlib.new(algo)
    file = open(path, 'rb')
    while True:
        data = file.read(32768)
        if not data:
            break
        hash.update(data)
    file.close()
    return hash.hexdigest()


class RpmMdException(Exception):
    pass
class Yast2Exception(Exception):
    pass


class DistOutput(object):
    def __init__(self, outdir, tag, style):
        d = os.path.join(outdir, "dist-" + tag)
        try:
            os.makedirs(d)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise e

        self.fn_style = os.path.join(d, "style")
        self.fn_pkgs = os.path.join(d, "packages.gz")
        self.of_style = open(self.fn_style + ".tmp", "w")
        self.of_pkgs = gzip.GzipFile(self.fn_pkgs + ".tmp", "w")

        print >>self.of_style, style

    def close(self):
        self.of_style.close()
        self.of_pkgs.close()
        os.rename(self.fn_style + ".tmp", self.fn_style)
        os.rename(self.fn_pkgs + ".tmp", self.fn_pkgs)


class Metadata(object):
    def __init__(self, resource, cachedir, skip_arches=['src', 'i386', 'i686'], skip_suffixes=['-32bit', '-debuginfo', '-debugsource']):
        self.resource = resource

        parsed = urlparse.urlparse(self.resource)
        self._is_local = (parsed.scheme == '')
        if self._is_local:
            self._tmpdir = None
            self._cachedir = None
        else:
            self._tmpdir = tempfile.mkdtemp()
            self._cachedir = cachedir
            try:
                os.makedirs(os.path.dirname(cachedir))
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise e

        self.packages = []
        self._skip_arches = skip_arches
        self._skip_suffixes = skip_suffixes

    def cleanup(self, keep_cache=False):
        if self._tmpdir:
            if keep_cache:
                shutil.rmtree(self._cachedir, True)
                try:
                    shutil.move(self._tmpdir, self._cachedir)
                except:
                    shutil.rmtree(self._cachedir, True)
                    shutil.rmtree(self._tmpdir, True)
            else:
                shutil.rmtree(self._tmpdir, True)
            self._tmpdir = None

    def _fetch(self, subpath, expected_hash_type = None, expected_hash = None):
        if self._is_local:
            return

        cache = os.path.join(self._tmpdir, subpath)
        if os.path.exists(cache):
            return

        dirname = os.path.join(self._tmpdir, os.path.dirname(subpath))
        try:
            os.makedirs(dirname)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise e

        if expected_hash_type and expected_hash:
            old_cache = os.path.join(self._cachedir, subpath)
            old_hash = get_hash_from_file(expected_hash_type, old_cache)
            if old_hash == expected_hash:
                shutil.copy(old_cache, cache)
                return

        fout = open(cache, 'w')
        fin = None
        try:
            fin = urllib2.urlopen(posixjoin(self.resource, subpath))
            while True:
                bytes = fin.read(500 * 1024)
                if len(bytes) == 0:
                    break
                fout.write(bytes)
            fout.close()
        except urllib2.HTTPError, e:
            if fin:
                fin.close()
            fout.close()
            os.unlink(cache)
            raise e
        fin.close()
        fout.close()

    def _get_local_path(self, subpath, fetch = True, expected_hash_type = None, expected_hash = None):
        if self._is_local:
            return os.path.join(self.resource, subpath)
        else:
            if fetch:
                self._fetch(subpath, expected_hash_type, expected_hash)
            return os.path.join(self._tmpdir, subpath)

    def _append_package(self, package):
        if self._should_skip_package(package):
            return
        self.packages.append(package)

    def _should_skip_package(self, package):
        for suffix in self._skip_suffixes:
            if package.name.endswith(suffix):
                return True
        if package.arch in self._skip_arches:
            return True
        return False

    def _set_url_for_package(self, tag, style, pkg):
        url = "#"
        if style == "suse":
            if tag == "opensuse-factory":
                url = "https://build.opensuse.org/package/show?project=openSUSE%3AFactory&package={0}".format(pkg.source_package)
            else:
                parts = tag.split()
                if len(parts) > 1:
                    url = "https://build.opensuse.org/package/show?project=openSUSE%3A{0}&package={1}".format(parts[1], pkg.source_package)
        elif style == "fedora":
            # TODO
            pass

        pkg.url = url

    def export_data(self, tag, style, outdir='.'):
        log.info("Exporting data.")
        of = DistOutput(outdir, tag, style)
        # It's always much more readable to sort the output
        self.packages.sort(key=operator.attrgetter('name'))
        for package in self.packages:
            # Output package data
            self._set_url_for_package(tag, style, package)
            of.of_pkgs.write(package.to_yaml())

        of.close()
        log.info("Done exporting data.")


class RpmMd(Metadata):
    sourcerpm_re = re.compile(r'(.+)-[^-]+-[^-]+.src.rpm')

    def __init__(self, resource, cachedir):
        Metadata.__init__(self, resource, cachedir)

        self._parsed_repomd = False
        self._parsed_primary = False
        self._parsed_filelists = False

        self._primary_filename = None
        self._primary_hash = None
        self._filelists_filename = None
        self._filelists_hash = None

        self._pkgs_by_id = {}

    def _fetch(self, subpath, expected_hash_type = None, expected_hash = None):
        try:
            Metadata._fetch(self, subpath, expected_hash_type, expected_hash)
        except urllib2.HTTPError, e:
            raise RpmMdException('Cannot fetch %s from %s: %s' % (subpath, self.resource, e))

    def fetch_and_parse(self):
        self._parse_repomd()

        (hash_type, expected_hash) = self._primary_hash
        primary_path = self._get_local_path(self._primary_filename, expected_hash_type=hash_type, expected_hash=expected_hash)
        real_hash = get_hash_from_file(hash_type, primary_path)
        if real_hash != expected_hash:
            raise RpmMdException('Hash of %s from %s is different from the expected value.' % (self._primary_filename, self.resource))

        if self._filelists_filename:
            (hash_type, expected_hash) = self._filelists_hash
            filelists_path = self._get_local_path(self._filelists_filename, expected_hash_type=hash_type, expected_hash=expected_hash)
            real_hash = get_hash_from_file(hash_type, filelists_path)
            if real_hash != expected_hash:
                raise RpmMdException('Hash of %s from %s is different from the expected value.' % (self._filelists_filename, self.resource))

        self._parse_primary()

    def _parse_repomd(self):
        def get_location(node):
            location_node = node.find(RPM_MD_NS_REPO + 'location')
            if location_node is None:
                return None
            return location_node.get('href')

        def get_hash(node):
            checksum_node = node.find(RPM_MD_NS_REPO + 'checksum')
            if checksum_node is None:
                return None
            hash_type = checksum_node.get('type')
            if not hash_type or not checksum_node.text:
                return None
            if hash_type == 'sha':
                hash_type = 'sha1'
            return (hash_type, checksum_node.text)

        if self._parsed_repomd:
            return

        repomd_path = self._get_local_path('repodata/repomd.xml')
        if not os.path.exists(repomd_path):
            raise RpmMdException('%s in %s does not exist.' % ('repodata/repomd.xml', self.resource))

        try:
            root = ET.parse(repomd_path).getroot()
        except SyntaxError, e:
            raise RpmMdException('Cannot parse metadata: %s' % (e,))

        for data_node in root.findall(RPM_MD_NS_REPO + 'data'):
            if data_node.get('type') == 'primary':
                self._primary_filename = get_location(data_node)
                self._primary_hash = get_hash(data_node)
            elif data_node.get('type') == 'filelists':
                self._filelists_filename = get_location(data_node)
                self._filelists_hash = get_hash(data_node)

    def _parse_primary(self):
        log.info("Parsing primary xml.")
        if self._parsed_primary:
            return

        if self._primary_filename is None:
            raise RpmMdException('No primary metadata in %s.' % (self.resource,))

        (hash_type, expected_hash) = self._primary_hash
        primary_path = self._get_local_path(self._primary_filename, expected_hash_type=hash_type, expected_hash=expected_hash)
        if not os.path.exists(primary_path):
            raise RpmMdException('%s in %s does not exist.' % (self._primary_filename, self.resource))

        try:
            root = ET.parse(gzip.open(primary_path)).getroot()
        except SyntaxError, e:
            raise RpmMdException('Cannot parse primary metadata: %s' % (e,))

        for package_node in root.findall(RPM_MD_NS + 'package'):
            (pkgid, package) = self._parse_package_node(package_node)
            self._pkgs_by_id[pkgid] = package
            self._append_package(package)

        self._parsed_primary = True
        log.info("Done parsing primary xml.")

    def _parse_package_node(self, package_node):
        name = None
        arch = None
        src_package = None
        files = []

        name_node = package_node.find(RPM_MD_NS + 'name')
        if name_node is not None:
            name = name_node.text
        if not name:
            raise RpmMdException('No name found for package.')

        arch_node = package_node.find(RPM_MD_NS + 'arch')
        if arch_node is not None:
            arch = arch_node.text
        if not arch:
            raise RpmMdException('No arch found for package %s.', name)

        format_node = package_node.find(RPM_MD_NS + 'format')
        if format_node is None:
            raise RpmMdException('No <format> tag for %s.' % name)

        sourcerpm_node = format_node.find(RPM_MD_NS_RPM + 'sourcerpm')
        if sourcerpm_node is not None:
            match = self.sourcerpm_re.match(sourcerpm_node.text)
            if match:
                src_package = match.group(1)
        if not src_package and arch != 'src':
            raise RpmMdException('No source package for %s.' % name)

        version_node = package_node.find(RPM_MD_NS + 'version')
        if version_node is None:
            raise RpmMdException('No <version> tag for %s.' % name)
        upstream_version = version_node.attrib.get("ver")
        if not upstream_version:
            raise RpmMdException('No upstream version found in <version> tag for %s.' % name)
        version = "%s-%s" % (upstream_version, version_node.attrib.get("rel"))

        checksum_node = package_node.find(RPM_MD_NS + 'checksum')
        if checksum_node is not None and checksum_node.get('pkgid').lower() == 'yes':
            pkgid = checksum_node.text or None
        else:
            pkgid = None

        pkg = PackageInfo(name, version, upstream_version, arch, None)
        pkg.source_package = src_package
        return (pkgid, pkg)


class Yast2(Metadata):
    def __init__(self, resource, cachedir):
        Metadata.__init__(self, resource, cachedir)

        self._parsed_content = False
        self._parsed_packages = False

        self._descrdir = None
        self._distribution = None
        self._version = None
        self._packages_filename = None
        self._packages_hash = None

    def _fetch(self, subpath, expected_hash_type = None, expected_hash = None):
        try:
            Metadata._fetch(self, subpath, expected_hash_type, expected_hash)
        except urllib2.HTTPError, e:
            raise Yast2Exception('Cannot fetch %s from %s: %s' % (subpath, self.resource, e))

    def fetch_and_parse(self):
        self._parse_content()

        (hash_type, expected_hash) = self._packages_hash
        packages_path = self._get_local_path(os.path.join(self._descrdir, self._packages_filename), expected_hash_type=hash_type, expected_hash=expected_hash)
        real_hash = get_hash_from_file(hash_type, packages_path)
        if real_hash != expected_hash:
            raise Yast2Exception('Hash of %s from %s is different from the expected value.' % (self._packages_filename, self.resource))

        self._parse_packages()

    def _parse_content(self):
        if self._parsed_content:
            return

        content = self._get_local_path('content')
        if not os.path.exists(content):
            raise Yast2Exception('%s in %s does not exist.' % ('content', self.resource))

        fin = open(content, 'r')
        line = fin.readline()
        if not line:
            raise Yast2Exception('%s in %s is empty.' % ('content', self.resource))

        contentstyle = line[:-1].split()
        if contentstyle != ['CONTENTSTYLE', '11']:
            raise Yast2Exception('Cannot parse %s in %s: unknown format.' % ('content', self.resource))

        while True:
            line = fin.readline()
            if not line:
                break

            line = line[:-1]
            items = line.split()
            if items[0] == 'DESCRDIR':
                if len(items) != 2:
                    raise Yast2Exception('Cannot parse %s line in %s from %s: not the expected number of items in \'%s\'' % ('DESCRDIR', 'content', self.resource, line))
                self._descrdir = items[1]
            elif items[0] == 'DISTRIBUTION':
                if len(items) != 2:
                    raise Yast2Exception('Cannot parse %s line in %s from %s: not the expected number of items in \'%s\'' % ('DISTRIBUTION', 'content', self.resource, line))
                self._distribution = items[1]
            elif items[0] == 'VERSION':
                if len(items) != 2:
                    raise Yast2Exception('Cannot parse %s line in %s from %s: not the expected number of items in \'%s\'' % ('VERSION', 'content', self.resource, line))
                self._version = items[1]
            elif items[0] == 'META':
                if len(items) != 4:
                    raise Yast2Exception('Cannot parse %s line in %s from %s: not the expected number of items in \'%s\'' % ('META', 'content', self.resource, line))
                if items[1] not in ('SHA1', 'SHA256'):
                    raise Yast2Exception('Unknown hash type \'%s\' in %s.' % (items[1], self.resource))
                if items[3] != 'packages.gz':
                    continue
                self._packages_filename = items[3]
                if items[1] == 'SHA1':
                    self._packages_hash = ('sha1', items[2])
                elif items[1] == 'SHA256':
                    self._packages_hash = ('sha256', items[2])

        fin.close()
        self._parsed_content = True

    def _parse_packages(self):
        if self._parsed_packages:
            return

        if self._descrdir is None or self._packages_filename is None:
            raise Yast2Exception('No metadata about packages in %s.' % (self.resource,))

        (hash_type, expected_hash) = self._packages_hash
        packages_path = self._get_local_path(os.path.join(self._descrdir, self._packages_filename), expected_hash_type=hash_type, expected_hash=expected_hash)
        if not os.path.exists(packages_path):
            raise Yast2Exception('%s in %s does not exist.' % (self._packages_filename, self.resource))

        self._packages_fin = open(packages_path, 'r')
        try:
            self._packages_fin = gzip.GzipFile(packages_path, 'r')
            firstline = self._packages_fin.readline()
        except IOError:
            self._packages_fin = open(packages_path, 'r')
            firstline = self._packages_fin.readline()

        if firstline[:-1] != '=Ver: 2.0':
            raise Yast2Exception('Cannot parse %s in %s: unknown format.' % (self._packages_filename, self.resource))

        self._readline_packages()
        while True:
            line = self._getline_packages()
            if not line:
                break

            if line.startswith('=Pkg:'):
                package = self._parse_package()
                self._append_package(package)
            else:
                self._readline_packages()

        self._packages_fin.close()
        self._parsed_packages = True

    def _readline_packages(self):
        line = self._packages_fin.readline()
        self._line_packages = line[:-1]
        return self._line_packages

    def _getline_packages(self):
        return self._line_packages

    def _parse_pkgdata(self, text, linetype):
        text = text[len(linetype+':'):]
        text.strip()
        pkg_data = text.split()
        if len(pkg_data) != 4:
            raise Yast2Exception('Cannot parse %s line in %s from %s: %s' % (linetype, self._packages_filename, self.resource, line))
        return pkg_data

    def _parse_package(self):
        name = None
        arch = None
        src_package = None

        line = self._getline_packages()
        if not line.startswith('=Pkg:'):
            raise Yast2Exception('Internal error, not a =Pkg line in %s from %s: %s' % (self._packages_filename, self.resource, line))

        pkg_data = self._parse_pkgdata(line, '=Pkg')
        name = pkg_data[0]
        upstream_version = pkg_data[1]
        version = "%s-%s" % (upstream_version, pkg_data[2])
        arch = pkg_data[3]

        while True:
            line = self._readline_packages()
            if not line or line.startswith('=Pkg:'):
                break

            if line.startswith('=Src:'):
                if src_package is not None:
                    raise Yast2Exception('Error while parsing package %s in %s from %s: two =Src lines.' % (name, self._packages_filename, self.resource))
                pkg_data = self._parse_pkgdata(line, '=Src')
                src_package = pkg_data[0]

        if not src_package:
            raise Yast2Exception('No source package for %s in %s from %s.' % (name, self._packages_filename, self.resource))

        return PackageInfo(name, version, upstream_version, arch, src_package)


def guess_distro_style(resource):
    if resource.find('/download.opensuse.org/distribution/') != -1 or resource.find('/download.opensuse.org/update/') != -1 or resource.find('/download.opensuse.org/factory/') != -1:
        return 'suse'
    if resource.find('/fedora/linux/') != -1:
        return 'fedora'

    return None


def guess_metadata_type(resource):
    parsed = urlparse.urlparse(resource)

    if not parsed.scheme:
        if os.path.exists(os.path.join(resource, 'repodata', 'repomd.xml')):
            return 'rpm-md'
        elif os.path.exists(os.path.join(resource, 'content')):
            return 'yast2'
    else:
        try:
            url = posixjoin(resource, 'repodata', 'repomd.xml')
            urllib2.urlopen(HeadRequest(url))
            return 'rpm-md'
        except urllib2.HTTPError, e:
            if e.code != 404:
                raise e
        try:
            url = posixjoin(resource, 'content')
            urllib2.urlopen(HeadRequest(url))
            return 'yast2'
        except urllib2.HTTPError, e:
            if e.code != 404:
                raise e

    return None

def main(args):
    parser = optparse.OptionParser(usage="usage: %prog [options] RESOURCE DISTRO_TAG",
                    description="Export distromatch info from RPM-MD/YaST2 metadata")
    parser.add_option("--metadata-type", default="auto", help="Metadata type (%s). Default: %%default" % ', '.join(KNOWN_METADATA_TYPE))
    parser.add_option("--outdir", default=".", help="Destination directory. Default: %default")
    parser.add_option("--cachedir", default="./cache", help="Cache directory. Default: %default")
    parser.add_option("--verbose", action="store_true", help="Verbose output")

    (opts, args) = parser.parse_args()

    date_format = "%c"
    log_format = "[%(levelname)s] %(asctime)s: %(message)s"
    if opts.verbose:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr, datefmt=date_format, format=log_format)
    else:
        logging.basicConfig(level=logging.WARNING, stream=sys.stderr, datefmt=date_format, format=log_format)

    if len(args) != 2:
        print >>sys.stderr, 'No file metadata passed as argument.'
        sys.exit(1)

    resource = args[0]
    distro_tag = args[1]

    parsed = urlparse.urlparse(resource)

    if not parsed.scheme:
        if not os.path.exists(resource):
            print >>sys.stderr, '\'%s\' does not exist.' % resource
            sys.exit(1)
        if not os.path.isdir(resource):
            print >>sys.stderr, '\'%s\' is not a directory.' % resource
            sys.exit(1)

    if opts.metadata_type != 'auto' and opts.metadata_type not in KNOWN_METADATA_TYPE:
        print >>sys.stderr, 'Unknown metadata type \'%s\'.' % opts.metadata_type
        print >>sys.stderr, 'Please use one of: %s.' % ', '.join(KNOWN_METADATA_TYPE)
        sys.exit(1)

    distro_style = guess_distro_style(resource)
    if not distro_style:
        print >>sys.stderr, 'Cannot detect what style of distribution is in \'%s\'.' % resource
        sys.exit(1)

    if opts.metadata_type == 'auto':
        metadata_type = guess_metadata_type(resource)
        if not metadata_type:
            print >>sys.stderr, 'Cannot detect what kind of metadata is in \'%s\'.' % resource
            sys.exit(1)
    else:
        metadata_type = opts.metadata_type

    metadata = None
    cachedir = os.path.join(opts.cachedir, distro_tag)

    if metadata_type == 'rpm-md':
        metadata = RpmMd(resource, cachedir)
    elif metadata_type == 'yast2':
        metadata = Yast2(resource, cachedir)
    else:
        raise Exception('Internal error: unknown metadata type \'%s\'.' % metadata_type)

    try:
        metadata.fetch_and_parse()
    except (RpmMdException, Yast2Exception), e:
        metadata.cleanup()
        print >>sys.stderr, '%s' % e
        sys.exit(2)

    metadata.export_data(distro_tag, distro_style, outdir=opts.outdir)

    metadata.cleanup(keep_cache=True)

if __name__ == '__main__':
    try:
        ret = main(sys.argv)
        sys.exit(ret)
    except KeyboardInterrupt:
        sys.exit(0)

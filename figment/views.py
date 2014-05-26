
from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader

from figment.models import *
from figment import settings
import os

def index(request):
    #context = {'latest_question_list': latest_question_list}
    return render(request, 'index.html', None)

def provides_type_text(kind):
    MAPPING = {'mimetype': "Mimetypes",
               'codec': "Codec",
               'bin': "Binaries",
               'lib': "Libraries"}
    text = MAPPING.get(kind)
    if not text:
        text = kind
    return text

def get_component(request):
    if 'id' in request.GET and request.GET['id']:
        q = request.GET['id']

        cpt = Component.objects.filter(identifier=q).first()
        if not cpt:
            return render(request, 'id_notfound.html',
                {'identifier': q})

        icon_url = cpt.icon_url
        if icon_url == "":
            icon_url = "images/notfound.png"
        icon_url = "/static/cpt-icons/%s" % (icon_url)

        versions = ComponentVersion.objects.filter(component=cpt)
        veritems = list()
        v_internal_id = 1
        for ver in versions:
            pitems = list()
            pdata = dict()
            distro_data = list()
            provides_items = ProvidesItem.objects.filter(version=ver)
            for pi in provides_items:
                if not pdata.get(pi.kind):
                    pdata[pi.kind] = list()
                pdata[pi.kind].append(pi.value)

            distros_assoc = DistroPackage.objects.filter(version=ver)
            for distro_a in distros_assoc:
                distro = distro_a.distro
                distro_data.append({'name': distro.name,
                                    'version': distro.version_str,
                                    'codename': distro.codename,
                                    'pkgurl': distro_a.package_url})

            for kind in pdata.keys():
                pitems.append({'typename': provides_type_text(kind), 'values': pdata[kind]})
            veritems.append({'version': ver.version_str,
                    'provides': pitems,
                    'distros': distro_data,
                    'version_id': v_internal_id})
            v_internal_id += 1

        item = {
            'identifier': cpt.identifier,
            'name': cpt.name,
            'summary': cpt.summary,
            'description': cpt.description,
            'icon_url': icon_url,
            'versions': veritems,
            'license': cpt.license,
            'homepage': cpt.homepage
        }

        return render(request, 'component_page.html',
            {'item': item,
             'title': cpt.name})
    else:
        return render(request, 'index.html', {'error': True})

def component_to_item(cpt):
    icon_url = cpt.icon_url

    if os.path.isfile(os.path.join("static", "cpt-icons", icon_url)):
        icon_url = "/static/cpt-icons/%s" % (icon_url)
    else:
        icon_url = "/static/images/notfound.png"

    item = {
        'kind': cpt.kind,
        'identifier': cpt.identifier,
        'name': cpt.name,
        'summary': cpt.summary,
        'icon_url': icon_url
    }
    return item

def search_component(request):
    if 'q' in request.GET and request.GET['q']:
        q = request.GET['q']
        db_backend = settings.DATABASES['default']['ENGINE'].split('.')[-1]
        if db_backend == 'postgresql_psycopg2':
            cpts = Component.search_manager.search(q)
        else:
            cpts = Component.objects.filter(description__icontains=q)

        items = list()
        for cpt in cpts:
            items.append(component_to_item(cpt))

        return render(request, 'results.html',
            {'title': "Search results",
             'items': items})
    else:
        return render(request, 'index.html', {'error': True})

def find_feature(request):
    if ('q' in request.GET and request.GET['q']) and ('type' in request.GET and request.GET['type']):
        pvalue = request.GET['q']
        pkind = request.GET['type']
        feature_items = ProvidesItem.objects.filter(kind=pkind, value=pvalue)

        items = list()
        for feature_item in feature_items:
            cpt = feature_item.version.component
            item = component_to_item(cpt)
            item['name'] = "%s (%s)" % (item['name'], feature_item.version.version_str)
            items.append(item)

        return render(request, 'results.html',
            {'title': "Search results",
             'items': items})
    else:
        return render(request, 'index.html', {'error': True})

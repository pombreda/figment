
from flask import render_template, redirect, Markup, url_for
from figment import app
from forms import GetIdForm, SearchForm, SearchItemsForm
from database import db
from models import *
from utils import get_db
from werkzeug.urls import url_quote, url_unquote
import os.path

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    idform = GetIdForm(prefix="get")
    if idform.validate_on_submit():
        return redirect(url_for('component_page', identifier=url_quote(idform.identifier.data, safe='')))

    sform = SearchForm(prefix="search")
    if sform.validate_on_submit():
        return redirect(url_for('component_search', search_str=url_quote(sform.text.data, safe='')))

    itemform = SearchItemsForm(prefix="search-item")
    if itemform.validate_on_submit():
        return redirect(url_for('find_feature', kind=itemform.kind.data, value=url_quote(itemform.text.data, safe='')))

    return render_template('index.html',
        title = 'Home',
        idform = idform,
        sform = sform,
        itemform = itemform)

def get_icon_url(icon_url):
    if os.path.isfile(os.path.join(app.root_path, "..", "static", "images", "cpt-icons", icon_url)):
        icon_url = url_for('static', filename="images/cpt-icons/%s" % (icon_url))
    else:
        icon_url = url_for('static', filename='images/notfound.png')

    return icon_url

def provides_type_text(kind):
    MAPPING = {'mimetype': "Mimetypes",
               'codec': "Codec",
               'bin': "Binaries",
               'lib': "Libraries"}
    text = MAPPING.get(kind)
    if not text:
        text = kind
    return text

@app.route('/get/<identifier>', methods=['GET', 'POST'])
def component_page(identifier):
    identifier = url_unquote(identifier)
    cpt = db.session.query(Component).filter_by(identifier=identifier).first()
    if not cpt:
        notfound_msg = Markup("Component with identifier <b>%s</b> was not found.") % (identifier)
        return render_template('notfound.html', message = notfound_msg)

    cptdesc = cpt.description.replace('\n', "<br/>")
    cptdesc = Markup(cptdesc)

    screenshots = list()

    for shot in cpt.screenshots:
        imgs = shot.get_image_data()
        sdata = dict()
        max_height = 0
        for img in imgs:
            if img['height'] <= 200:
                sdata['url_thumb'] = img['url']
            elif img['height'] > max_height:
                sdata['url_large'] = img['url']
            max_height = img['height']
        if sdata:
            if shot.caption:
                sdata['caption'] = shot.caption
            else:
                sdata['caption'] = "Screenshot: %s" % (cpt.name)
            screenshots.append(sdata)

    veritems = list()
    v_internal_id = 1
    for ver in cpt.versions:
        pitems = list()
        pdata = dict()
        distro_data = list()
        for pi in ver.provided_items:
            if not pdata.get(pi.kind):
                pdata[pi.kind] = list()
            pdata[pi.kind].append(pi.value)

        for distro_pkg in ver.packages:
            distro = db.session.query(Distribution).filter_by(id=distro_pkg.distro_id).one()
            distro_data.append({'name': distro.name,
                                'version': distro.version,
                                'codename': distro.codename,
                                'pkgurl': distro_pkg.package_url})

        for kind in pdata.keys():
            pitems.append({'typename': provides_type_text(kind), 'values': pdata[kind]})

        veritems.append({'version': ver.version,
                'provides': pitems,
                'distros': distro_data,
                'version_id': v_internal_id})
        v_internal_id += 1

    item = {
        'identifier': cpt.identifier,
        'name': cpt.name,
        'summary': cpt.summary,
        'description': cpt.description,
        'icon_url': get_icon_url(cpt.icon_url),
        'versions': veritems,
        'developer': cpt.developer_name,
        'license': cpt.license,
        'homepage': cpt.homepage,
        'screenshots': screenshots
    }

    return render_template('component_page.html',
        title = cpt.name,
        item = item)

def component_to_item(cpt):
    icon_url = get_icon_url(cpt.icon_url)

    item = {
        'kind': cpt.kind,
        'identifier': cpt.identifier,
        'name': cpt.name,
        'summary': cpt.summary,
        'icon_url': icon_url
    }
    return item

@app.route('/search/<search_str>', methods=['GET', 'POST'])
def component_search(search_str):
    search_str = url_unquote(search_str)
    cpts = db.session.query(Component).filter(Component.description.like("%"+search_str+"%")).all()
    if not cpts:
        notfound_msg = Markup("Could not find software matching the search terms: <b>%s</b>") % (search_str)
        return render_template('notfound.html', message = notfound_msg)

    items = list()
    for cpt in cpts:
        items.append(component_to_item(cpt))

    return render_template('results.html',
        title = "Search results",
        items = items)

@app.route('/provides/<kind>/<value>', methods=['GET', 'POST'])
def find_feature(kind, value):
    value = url_unquote(value)
    feature_items = db.session.query(ProvidedItem).filter_by(kind=kind, value=value).all()
    print value
    if not feature_items:
        notfound_msg = Markup("Could not find software providing \"<b>[<i>%s</i>] %s</b>\"") % (kind, value)
        return render_template('notfound.html', message = notfound_msg)

    items = list()
    for feature_item in feature_items:
        cpt = feature_item.version.component
        item = component_to_item(cpt)
        item['name'] = "%s (%s)" % (item['name'], feature_item.version.version)
        items.append(item)

    return render_template('results.html',
        title = "Search results",
        items = items)

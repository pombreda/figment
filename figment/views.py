
from flask import render_template, redirect, Markup, url_for
from figment import app
from forms import SearchIdForm, SearchForm
from gi.repository import Appstream
from database import db
from models import *
from utils import get_db
import os.path

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    idform = SearchIdForm(prefix="id")
    if idform.validate_on_submit():
        return redirect(url_for('component_page', identifier=idform.identifier.data))

    sform = SearchForm(prefix="search")
    if sform.validate_on_submit():
        return redirect(url_for('component_search', search_str=sform.text.data))

    return render_template('index.html',
        title = 'Home',
        idform = idform,
        sform = sform)

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
    cpt = db.session.query(Component).filter_by(identifier=identifier).first()
    if not cpt:
        return render_template('id_notfound.html', identifier = identifier)

    cptdesc = cpt.description.replace('\n', "<br/>")
    cptdesc = Markup(cptdesc)

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
        for x in pitems:
            print x['values']
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
        'license': cpt.license,
        'homepage': cpt.homepage
    }

    return render_template('component_page.html',
        title = cpt.name,
        item = item)

@app.route('/search/<search_str>', methods=['GET', 'POST'])
def component_search(search_str):
    db = get_db()
    cpts = db.find_components_by_term(search_str, "")
    if not cpts:
        return render_template('id_notfound.html', identifier="Crap!")

    items = list()
    for cpt in cpts:
        icon_url = get_icon_url(cpt.get_icon_url().decode("utf-8"))

        item = {
            'kind': Appstream.ComponentKind.to_string(cpt.get_kind()).decode("utf-8"),
            'identifier': cpt.get_id().decode("utf-8"),
            'name': cpt.get_name().decode("utf-8"),
            'summary': cpt.get_summary().decode("utf-8"),
            'icon_url': icon_url
        }
        items.append(item)

    return render_template('results.html',
        title = "Search results",
        items = items)

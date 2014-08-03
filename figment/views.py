
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
        return redirect(url_for('search_string', search_str=sform.text.data))

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

@app.route('/get/<identifier>', methods=['GET', 'POST'])
def component_page(identifier):
    cpt = db.session.query(Component).filter_by(identifier=identifier).first()
    if not cpt:
        return render_template('id_notfound.html', identifier = identifier)

    cptdesc = cpt.description.replace('\n', "<br/>")
    cptdesc = Markup(cptdesc)

    pitems = list()
    pitems = [
        {
            'typename': "Mimetypes",
            'values': "ABC",
        }
    ]

    print cpt.icon_url
    item = {
        'identifier': cpt.identifier,
        'name': cpt.name,
        'summary': cpt.summary,
        'description': cptdesc,
        'icon_url': get_icon_url(cpt.icon_url),
        'license': cpt.license,
        'homepage': cpt.homepage,
        'provides': pitems
    }

    return render_template('component_page.html',
        title = cpt.name,
        item = item)

@app.route('/search/<search_str>', methods=['GET', 'POST'])
def search_string(search_str):
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

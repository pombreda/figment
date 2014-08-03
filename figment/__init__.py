from flask import Flask
import os

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')

app = Flask("figment", template_folder=tmpl_dir, static_folder=static_dir)
app.config.from_object('config')

from figment import views

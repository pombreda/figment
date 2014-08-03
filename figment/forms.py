from flask.ext.wtf import Form
from wtforms import TextField, BooleanField
from wtforms.validators import Required

class SearchIdForm(Form):
    identifier = TextField('identifier', validators = [Required()])

class SearchForm(Form):
    text = TextField('text', validators = [Required()])

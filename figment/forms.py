from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, SelectField
from wtforms.validators import Required

class GetIdForm(Form):
    identifier = TextField('identifier', validators = [Required()])

class SearchForm(Form):
    text = TextField('text', validators = [Required()])

class SearchItemsForm(Form):
    kind_choices = [('mimetype', 'Mimetype'), ('lib', 'Library'), ('bin', 'Binary'),
                    ('python2', 'Python-2 module'), ('python3', 'Python-3 module')]

    text = TextField('text', validators = [Required()])
    kind = SelectField('kind', choices = kind_choices, default = '1')


from django.db import models
from djorm_pgfulltext.models import SearchManager
from djorm_pgfulltext.fields import VectorField
from figment import settings

class Component(models.Model):
    identifier = models.CharField(max_length=200)
    kind = models.CharField(max_length=200)
    name = models.TextField()
    summary = models.TextField()
    description = models.TextField()
    icon_url = models.TextField()
    license = models.CharField(max_length=200)
    homepage = models.TextField()

    if settings.DATABASES['default']['ENGINE'].split('.')[-1] == 'postgresql_psycopg2':
        search_index = VectorField()
        objects = models.Manager()
        search_manager = SearchManager(
        fields=('name', 'summary', 'description'),
            config='pg_catalog.english',
            search_field='search_index',
            auto_update_search_field=True
        )

class ComponentVersion(models.Model):
    component = models.ForeignKey(Component)
    version = models.CharField(max_length=200)

class Distribution(models.Model):
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    codename = models.CharField(max_length=200)

class ProvidesItem(models.Model):
    cpt_version = models.ForeignKey(ComponentVersion)
    kind = models.TextField()
    value = models.TextField()

class DistroPackage(models.Model):
    cpt_version = models.ForeignKey(ComponentVersion)
    distro = models.ForeignKey(Distribution)
    package_url = models.TextField()

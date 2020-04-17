# stdlib imports
import csv
import json
import os
# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.text import slugify
# project imports
from dbdb.core.models import CitationUrl
from dbdb.core.models import Feature
from dbdb.core.models import FeatureOption
from dbdb.core.models import License
from dbdb.core.models import OperatingSystem
from dbdb.core.models import ProgrammingLanguage
from dbdb.core.models import ProjectType
from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVersionMetadata


class Command(BaseCommand):

    help = '''Creates a fixture based on the files on initial_data folder
    This should be run only for a newly created system deployment and if there's no better database dump to apply.

    Please be sure you have a databasees.csv file in initial_data folder along with spring2017 and spring2016
    '''

    def handle(self, *args, **options):
        if System.objects.exists():
            print('You should only run this command if there are no databases in the system')
            return

        # choose paths
        path_csv = os.path.join(settings.BASE_DIR, 'data', 'initial_data', 'databases.csv')
        path_sp2016 = os.path.join(settings.BASE_DIR, 'data', 'initial_data', 'spring2016')
        path_sp2017 = os.path.join(settings.BASE_DIR, 'data', 'initial_data', 'spring2017')

        with transaction.atomic():
            # create initial account
            User = get_user_model()
            user = User.objects.filter(username='developer').first()
            if user is None:
                user = User.objects.create_superuser('developer', None, 'temporarypassword')

            self.load_systems(path_csv, user)
            self.crawl_folder(path_sp2016)
            self.crawl_folder(path_sp2017)
            pass
        return

    def crawl_folder(self, path):
        for filename in os.listdir(path):
            self.parse_json_database( os.path.join(path, filename) )
        return

    def load_systems(self, path, user):
        print(path)

        slugs = set()

        with open(path, 'r') as fin:
            reader = csv.reader(fin)

            for name,url,tech_docs,description in reader:
                if not name: continue
                slug = slugify(name)
                if slug in slugs: continue

                print( '>', '%s (%s)' % (name, slug) )

                system = System.objects.create(
                    slug=slug,
                    name=name,
                    ver=1
                )

                SystemVersion.objects.create(
                    system=system,
                    creator=user,
                    tech_docs=tech_docs,
                    url=url,
                    description=description
                )
                pass
            pass
        return

    def parse_json_database(self, path):
        User = get_user_model()

        print(path)

        with open(path, 'r') as fin:
            db = json.load(fin)

            slug = slugify( db['Name'] )
            system = System.objects.filter(slug=slug).first()

            if not system:
                system = System.objects.create(
                    slug=slug,
                    name=db['Name'],
                    ver=1
                )
                pass

            username = db['Email'].split('@')[0].lower()
            email = db['Email'].lower()
            password = 'dbdbiouser'

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = User.objects.create_user(username, email, password)

            meta = SystemVersionMetadata.objects.create()

            derived_from = db.get('Derived From')
            if derived_from:
                try:
                    derived_from_system = System.objects.get(name__iexact=derived_from)
                    meta.derived_from.add( derived_from_system )
                except System.DoesNotExist:
                    pass
                pass

            for lang in db.get('Programming Language', []):
                pl, _ = ProgrammingLanguage.objects.get_or_create(slug=slugify(lang), defaults=dict(name=lang))
                meta.supported_languages.add(pl)
                pass
            for l in db.get('License', []):
                license, _ = License.objects.get_or_create(slug=slugify(l), defaults=dict(name=l))
                meta.licenses.add(license)
                pass
            for os_name in db.get('Operating Systems', []):
                op_sys, _ = OperatingSystem.objects.get_or_create(slug=slugify(os_name), defaults=dict(name=os_name))
                meta.oses.add(op_sys)
                pass

            empty_values = set(('','NA','N/A','Active','Present','YYYY-MM','On-going'))

            sv = SystemVersion.objects.create(
                system=system,
                creator=user,
                meta=meta,

                developer=db['Developer'],
                start_year=None if ('Start Date' not in db or db['Start Date'] in empty_values) else db['Start Date'].split('-')[0],
                end_year=None if ('End Date' not in db or db['End Date'] in empty_values) else db.get('End Date', '').split('-')[0],
                url=db['Website'],

                description=db['Description'],
                history=db['History']
            )

            for url in db.get('Description Citations', []):
                cu, _ = CitationUrl.objects.get_or_create(url=url)
                sv.description_citations.add(cu)
                pass
            for url in db.get('History Citations', []):
                cu, _ = CitationUrl.objects.get_or_create(url=url)
                sv.history_citations.add(cu)
                pass
            for url in db.get('Start Date Citations', []):
                cu, _ = CitationUrl.objects.get_or_create(url=url)
                sv.start_year_citations.add(cu)
                pass
            for url in db.get('End Date Citations', []):
                cu, _ = CitationUrl.objects.get_or_create(url=url)
                sv.end_year_citations.add(cu)
                pass

            for pt_name in db.get('Project Type', []):
                pt, _ = ProjectType.objects.get_or_create(slug=slugify(pt_name), defaults=dict(name=pt_name))
                sv.project_types.add(pt)
                pass

            sv.save()

            features = [x for x in db.keys() if 'Options' in x]
            for feature_label in features:
                name = feature_label[:-8]
                feature, _ = Feature.objects.get_or_create(label=name)
                sf = SystemFeature.objects.create(
                    system=sv,
                    feature=feature,

                    description=db.get(name + ' Description', '')
                )
                for f in db[feature_label]:
                    option, _ = FeatureOption.objects.get_or_create(
                        feature=feature,
                        value=f
                    )
                    sf.options.add(option)
                    pass
                for url in db.get(name + ' Citations', []):
                    cu, _ = CitationUrl.objects.get_or_create(url=url)
                    sf.citations.add(cu)
                    pass
                pass
            pass
        return

    pass
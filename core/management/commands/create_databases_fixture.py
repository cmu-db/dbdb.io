import csv

import json
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, call_command
from os import listdir
from os.path import join

from core.models import System, SystemVersion, CitationUrls, ProjectType, SystemVersionMetadata, ProgrammingLanguage, \
    License, Feature, SystemFeatures, FeatureOption, OperatingSystem


class Command(BaseCommand):
    help = '''Creates a fixture based on the files on initial_data folder
    This should be run only for a newly created system deployment and if there's no better database dump to apply.
    
    Please be sure you have a databasees.csv file in initial_data folder along with spring2017 and spring2016
    '''

    def handle(self, *args, **options):
        if System.objects.count() > 0:
            print('You should only run this command if there are no databases in the system')
            return

        user = User.objects.create_superuser('pavlo', None, 'temporarypassword')
        csv_path = join(settings.BASE_DIR, 'core', 'initial_data', 'databases.csv')
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            for name, website, tech_docs, description in reader:
                if not name:
                    continue
                system = System.objects.create(
                    name=name,
                    current_version=1
                )
                SystemVersion.objects.create(
                    system=system,
                    creator=user,
                    website=website,
                    tech_docs=tech_docs,
                    description=description
                )
        sp2016_path = join(settings.BASE_DIR, 'core', 'initial_data', 'spring2016')
        sp2017_path = join(settings.BASE_DIR, 'core', 'initial_data', 'spring2017')

        self.crawl_folder(sp2016_path)
        self.crawl_folder(sp2017_path)

    def crawl_folder(self, path):
        for filename in listdir(path):
            self.parse_json_database(join(path, filename))

    def parse_json_database(self, path):
        print(path)
        with open(path, 'r') as f:
            db = json.load(f)
            system = System.objects.filter(name=db['Name']).first()
            if not system:
                system = System.objects.create(name=db['Name'])
            try:
                last_version = SystemVersion.objects.filter(system=system).first().version_number
            except AttributeError:
                last_version = 0
            username = db['Email'].split('@')[0]
            email = db['Email']
            password = 'dbdbiouser'
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = User.objects.create_user(username, email, password)

            sv = SystemVersion.objects.create(
                system=system,
                version_number=last_version + 1,
                description=db['Description'],
                history=db['History'],
                website=db['Website'],
                developer=db['Developer'],
                start_year=db['Start Date'].split('-')[0],
                end_year=db.get('End Date', '').split('-')[0],
                creator=user
            )
            for url in db.get('Description Citations', []):
                cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                sv.description_citations.add(cit_url)
            for url in db.get('History Citations', []):
                cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                sv.history_citations.add(cit_url)
            for url in db.get('Start Date Citations', []):
                cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                sv.start_year_citations.add(cit_url)
            for url in db.get('End Date Citations', []):
                cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                sv.end_year_citations.add(cit_url)
            for t in db.get('Project Type', []):
                p_type, _ = ProjectType.objects.get_or_create(name=t)
                sv.project_type.add(p_type)

            meta = SystemVersionMetadata.objects.create(
                derived_from=db.get('Derived From', '')
            )
            for lang in db.get('Programming Language', []):
                lang_obj, _ = ProgrammingLanguage.objects.get_or_create(
                    name=lang
                )
                meta.supported_languages.add(lang_obj)
            for l in db.get('License', []):
                license, _ = License.objects.get_or_create(
                    name=l
                )
                meta.licenses.add(license)
            for l in db.get('Licenses', []):
                license, _ = License.objects.get_or_create(
                    name=l
                )
                meta.licenses.add(license)
            for os in db.get('Operating Systems', []):
                op_sys, _ = OperatingSystem.objects.get_or_create(
                    name=os
                )
                meta.oses.add(op_sys)
            sv.meta = meta
            sv.save()
            features = [x for x in db.keys() if 'Options' in x]
            for feature in features:
                name = feature[:-8]
                feat, _ = Feature.objects.get_or_create(label=name)
                sf = SystemFeatures.objects.create(
                    system=sv,
                    feature=feat,
                    description=db.get(name + ' Description', '')
                )
                for f in db[feature]:
                    option, _ = FeatureOption.objects.get_or_create(
                        feature=feat,
                        value=f
                    )
                    sf.value.add(option)
                for url in db.get(name + ' Citations', []):
                    cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                    sf.citation.add(cit_url)
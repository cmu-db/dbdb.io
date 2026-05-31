import re

from anyascii import anyascii

from dbdb.core.models import SystemFeature, SystemVersion


def generate_searchtext(ver : SystemVersion):
    words = [ver.system.name]
    words += [org.name for org in ver.developer_orgs.all()]
    words += [f.name for f in ver.governance.all()]
    words += [x.name for x in ver.countries]
    if ver.former_names:
        words += ver.former_names.split(",")
    words += [acq.organization.name for acq in ver.acquisitions.select_related('organization').all()]
    words += [x.name for x in ver.written_in.all()]
    words += [x.slug for x in ver.written_in.all()]

    # URLs (just include domain names)
    for url in [ver.system_url, ver.sourcerepo_url]:
        if url:
            words += [url.get_domain(), url.get_domain(include_suffix=False)]

    # Add tags with and without hyphens
    # Example: time-series vs. timeseries
    for tag in ver.tags.all():
        words += [tag.name, tag.name.replace("-", "")]

    # It's debatable whether people actually want to do keyword search for the supported languages
    # From the logs, it looks like people really want to know the language a DBMS was written in
    # words += [x.name for x in ver.supported_languages.all()]
    # words += [x.slug for x in ver.supported_languages.all()]

    words += [x.name for x in ver.oses.all()]
    words += [x.slug for x in ver.oses.all()]
    words += [x.name for x in ver.licenses.all()]
    words += [x.slug for x in ver.licenses.all()]
    for sf in SystemFeature.objects.filter(version=ver):
        for o in sf.options.all():
            value = o.value
            # Special case the data model by adding the word "database" to end of it
            if sf.feature.slug == "data-model":
                value += " database"
            # Split values by slashes
            if value.find("/") != -1:
                value = " ".join(value.split("/"))
            words += [o.slug, value]
        if sf.description: words.append(sf.description)
    words += [ver.description]

    # Automatically add different variations of the name for better searching
    names = [ver.system.name]
    if ver.former_names:
        names += ver.former_names.split(",")

    # If they are using unicode characters, convert them to ASCII
    clean_name = re.sub('[^a-zA-Z0-9]', '', anyascii(ver.system.name)).strip()
    if ver.system.name != clean_name and clean_name not in names:
        names.append(clean_name)
        words.append(clean_name)
        # print("Cleaned '%s' -> '%s'" % (ver.system.name, clean_name))

    # We also add the name of the DBMS with/without common suffixes
    # Examples: MongoDB->Mongo, Kuzu->KuzuDB
    suffixes = ["DB", "SQL", "BASE", "STORE"]
    for name in names:
        has_suffix = False
        for s in suffixes:
            if name.upper().endswith(s):
                words.append(name[:-len(s)])
                has_suffix = True
        if not has_suffix:
            # print("Added variations: ", [name + s for s in suffixes])
            words += [name + s for s in suffixes]

    return " ".join([w.replace('\r', '').replace('\n', ' ') for w in words])
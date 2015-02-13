import os
from systems.models import *
from systems.views import DatabaseCreationPage

metadata_mapping = {
  "Name": "name",
  "Description": "description",
  "Website": "website",
  "Technical documentation": "tech_docs", # html href
  "Developer": "developer",
  "Initial release": "start_year",
}

manytomany_mapping = {
  "Database model": "dbmodel", # list of models
  "License": "license", # list of liscenses
  "APIs and other access methods": "access_methods", # list of things
  "Implementation language": "written_in", #list of languages"
  "Server operating systems": "oses",
  "Supported programming languages": "support_languages"
}

features_mapping = {
  "SQL": "sql", #yes no 
  "Foreign keys": "foreignkeys", #yes, no
  "Server-side scripts": "serverside", #yes, no, javascript
  "MapReduce": "mapreduce", # no, yes
  "Secondary indexes": "secondary", # yes,no, resitricted
  "Durability": "durability",
  "Triggers": "triggers", # yes or no
  "Concurrency": "concurrency", # yes or not there
  "Data scheme": "datascheme", # yes or schema-free
  "XML support": "xml",
  "Typing": "typing",
  "User concepts": "userconcepts",
  "Transaction concepts": "transactionconcepts",
}

def make_truefalse_fields(model):
  for field in model:
    if "description_" in field:
      if model[field] == "no":
        model["support_" + field[12:]] = False
        model[field] = ""
      elif model[field] == "yes":
        model["support_" + field[12:]] = True
        model[field] = ""
  return model

def getDBModel(db_file_name):
  f = open(db_file_name)
  data = eval(f.read())
  f.close()

  db = {}
  manytomany = {}
  for key in data:
    if key in metadata_mapping:
      if len(data[key]) == 1:
        val = data[key][0]
      else:
        val = data[key]
      db[metadata_mapping[key]] = val
    elif key in features_mapping:
      val = data[key][0]
      canon_key = features_mapping[key]
      if type(val) == tuple:
        if val[0] == "no":
          db["support_" + canon_key] = False
        elif val[0] == "yes":
          db["support_" + canon_key] = True
        if (len(val) > 1):
          db["description_" + canon_key] = val[1]
      elif type(val) == str:
        if val[0] == "no":
          db["support_" + canon_key] = False
        elif val[0] == "yes":
          db["support_" + canon_key] = True
        else:
          db["support_" + canon_key] = True
          db["description_" + canon_key] = val
    elif key in manytomany_mapping:
      stuff = []
      for thing in data[key]:
        if type(thing) == tuple:
          stuff.append(thing[0])
        else:
          stuff.append(thing)
      manytomany[manytomany_mapping[key]] = stuff

  db = make_truefalse_fields(db)
  return db, manytomany
  

def getModels():
  dataDir = "data"
  outputDir = "models_data"
  for fileName in os.listdir(dataDir):
    db_file_name = dataDir + "/" + fileName
    (db_model, m2m_model) = getDBModel(db_file_name)
    outFileName = outputDir + "/" + fileName
    outputFile = open(outFileName, "w")
    outputFile.write(str(db_model) + "\n" + str(m2m_model))
    outputFile.close()
    print "Completed %s...!" % fileName

# getModels()

def addLicenses(models, m2m_model, system):
  for license_name in m2m_model["license"]:
    if not License.objects.filter(name = license_name).count():
      license = License(name = license_name)
      license.save()
      models["licenses"][license_name] = license
    else:
      if license_name in models["licenses"]:
        license = models["licenses"][license_name]
      else:
        license = License.objects.get(name = license_name)
        license.save()
        models["licenses"][license_name] = license
    system.license.add(license)

def addWrittenIn(models, m2m_model, system):
  for lang_name in m2m_model["written_in"]:
    if not ProgrammingLanguage.objects.filter(name = lang_name).count():
      lang = ProgrammingLanguage(name = lang_name)
      lang.save()
      models["languages"][lang_name] = lang
    else:
      if lang_name in models["languages"]:
        lang = models["languages"][lang_name]
      else:
        lang = ProgrammingLanguage.objects.get(name = lang_name)
        lang.save()
        models["languages"][lang_name] = lang
    system.written_in.add(lang)

def addSupportLangs(models, m2m_model, system):
  for lang_name in m2m_model["support_languages"]:
    if not ProgrammingLanguage.objects.filter(name = lang_name).count():
      lang = ProgrammingLanguage(name = lang_name)
      lang.save()
      models["languages"][lang_name] = lang
    else:
      if lang_name in models["languages"]:
        lang = models["languages"][lang_name]
      else:
        lang = ProgrammingLanguage.objects.get(name = lang_name)
        lang.save()
        models["languages"][lang_name] = lang
    system.support_languages.add(lang)

def addOses(models, m2m_model, system):
  for os_name in m2m_model["oses"]:
    if not OperatingSystem.objects.filter(name = os_name).count():
      os = OperatingSystem(name = os_name)
      os.save()
      models["oses"][os_name] = os
    else:
      if os_name in models["oses"]:
        os = models["oses"][os_name]
      else:
        os = OperatingSystem.objects.get(name = os_name)
        os.save()
        models["oses"][os_name] = os
    system.oses.add(os)

def addAccessMethods(models, m2m_model, system):
  for a_name in m2m_model["access_methods"]:
    if not APIAccessMethods.objects.filter(name = a_name).count():
      am = APIAccessMethods(name = a_name)
      am.save()
      models["access_methods"][a_name] = am
    else:
      if a_name in models["access_methods"]:
        am = models["access_methods"][a_name]
      else:
        am = APIAccessMethods.objects.get(name = a_name)
        am.save()
        models["access_methods"][a_name] = am
    system.access_methods.add(am)

def addDBModels(models, m2m_model, system):
  for model_name in m2m_model["dbmodel"]:
    if not DBModel.objects.filter(name = model_name).count():
      dbmodel = DBModel(name = model_name)
      dbmodel.save()
      models["dbmodels"][model_name] = dbmodel
    else:
      if model_name in models["dbmodels"]:
        dbmodel = models["dbmodels"][model_name]
      else:
        dbmodel = DBModel.objects.get(name = model_name)
        dbmodel.save()
        models["dbmodels"][model_name] = dbmodel
    system.dbmodel.add(dbmodel)

def cleanWrittenIn(m2m_model):
  written_in = []
  for lang_name in m2m_model["written_in"]:
    if "and" in lang_name:
      written_in.extend(lang_name.split(" and "))
    else:
      written_in.append(lang_name)
  m2m_model["written_in"] = written_in

def cleanData(db_model):
  for field in db_model:
    if type(db_model[field]) == tuple:
      db_model[field] = db_model[field][0]

def enterModels(dryRun = True):
  dataDir = "current_data/models_data"
  models = {"licenses": {}, "dbmodels": {}, "access_methods": {},
            "languages": {}, "oses": {}}
  for fileName in os.listdir(dataDir):
    print "Doing %s ..." % (fileName.split(".")[0]),
    db_file_name = dataDir + "/" + fileName
    dbFile = open(db_file_name, "r")
    (db_model, m2m_model) = map(eval, dbFile.read().splitlines())
    cleanData(db_model)
    if "written_in" in m2m_model:
      cleanWrittenIn(m2m_model)
    dbSystemName = db_model["name"]
    if System.objects.filter(name = dbSystemName).count():
      print "done. Already made!"
      continue
    system = System(**db_model)
    system.secret_key = DatabaseCreationPage.create_secret_key()
    if dryRun:
      pass
    elif not m2m_model:
      system.save()
      pass
    else:
      print "saving model...",
      system.save()
      if "dbmodel" in m2m_model:
        addDBModels(models, m2m_model, system)
      if "oses" in m2m_model:
        addOses(models, m2m_model, system)
      if "license" in m2m_model:
        addLicenses(models, m2m_model, system)
      if "access_methods" in m2m_model:
        addAccessMethods(models, m2m_model, system)
      if "support_languages" in m2m_model:
        addSupportLangs(models, m2m_model, system)
      if "written_in" in m2m_model  :
        addWrittenIn(models, m2m_model, system)
    print "done!"
  return True

# enterModels(True)
    
    
    














# stdlib imports
import glob
import gzip
import re
import os
import sys
import dateutil.parser
from pprint import pprint

# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.db import connection

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVisit

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error


class Command(BaseCommand):
    
    def handle(self, *args, **options):
        
        # Get the list of all unique IPs
        ip_addresses = [ ]
        with connection.cursor() as cursor:
            cursor.execute("SELECT ip_address, user_agent, count(*) AS cnt FROM core_systemvisit GROUP BY ip_address, user_agent HAVING cnt > 2")
            ip_addresses = [ (row[0],row[1]) for row in cursor.fetchall() ]

        # For each ip/user pair, get the systems that they viewed
        all_visits = { }
        user_info = { }
        system_id_xref = { }
        next_user_id = 0
        next_system_id = 0
        for ip, ua in ip_addresses:
            systems = set()
            visits = SystemVisit.objects.filter(ip_address=ip, user_agent=ua)
            for v in visits:
                if not v.system.id in system_id_xref:
                    system_id_xref[v.system.id] = next_system_id
                    next_system_id += 1
                systems.add(system_id_xref[v.system.id])
            all_visits[next_user_id] = systems
            user_info[next_user_id] = (ip, ua)
            next_user_id += 1
        ## FOR
        system_cnt = System.objects.all().count()
        
        print("# of Users:", next_user_id)
        print("# of Sytems: %d (total=%d)" % (next_system_id, system_cnt))
        
        data = np.zeros((next_user_id, next_system_id))
        for user_id in all_visits.keys():
            for system_id in all_visits[user_id]:
                data[user_id, system_id] = 1
                
        print(data)
        sparsity = float(len(data.nonzero()[0]))
        sparsity /= (data.shape[0] * data.shape[1])
        sparsity *= 100
        print('Sparsity: {:4.2f}%'.format(sparsity))

        train_data, test_data = self.train_test_split(data)
        
        similarity = self.compute_similarity(train_data)
        pred = data.dot(similarity) / np.array([np.abs(similarity).sum(axis=1)])
        
        print('MSE: ' + str(self.get_mse(pred, test_data)))

        #print("# of IPs: %s" % len(ip_addresses))

        return
    
    def train_test_split(self, data):
        test = np.zeros(data.shape)
        train = data.copy()
        for user_id in range(data.shape[0]):
            test_data = np.random.choice(data[user_id, :].nonzero()[0], 
                                            size=10, 
                                            replace=True)
            train[user_id, test_data] = 0.
            test[user_id, test_data] = data[user_id, test_data]
            
        # Test and training are truly disjoint
        assert(np.all((train * test) == 0)) 
        return train, test

    def compute_similarity(self, data, epsilon=1e-9):
        # epsilon -> small number for handling dived-by-zero errors
        sim = data.T.dot(data) + epsilon
        norms = np.array([np.sqrt(np.diagonal(sim))])
        return (sim / norms / norms.T)
    
    def get_mse(self, pred, actual):
        # Ignore nonzero terms.
        pred = pred[actual.nonzero()].flatten()
        actual = actual[actual.nonzero()].flatten()
        return mean_squared_error(pred, actual)

    

    pass

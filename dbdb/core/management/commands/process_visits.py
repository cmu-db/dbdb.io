# stdlib imports
import glob
import gzip
import re
import os
import sys
import operator
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
from dbdb.core.models import SystemRecommendation

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error


class Command(BaseCommand):
    
    def add_arguments(self, parser):
        parser.add_argument('--max-threshold', type=int, default=99999,
                            help="Max visit count threshold per user")
        parser.add_argument('--min-threshold', type=int, default=2,
                            help="Min visit count threshold per user")
        parser.add_argument('--min-visit', type=int, default=2,
                            help="Min visit count threshold per system")
        parser.add_argument('--ignore', action='append', type=str,
                            help="List of IP addresses to ignore")
        parser.add_argument('--clear', action='store_true',
                            help="Clear out existing recommendations in the database")
        parser.add_argument('--store', action='store_true',
                            help="Store the recommendation in the database")
        return
    
    def handle(self, *args, **options):
        
        # Get the list of all unique IPs
        ip_addresses = [ ]
        with connection.cursor() as cursor:
            sql = "SELECT ip_address, user_agent, count(*) AS cnt FROM core_systemvisit "
            sql_args = [ ]

            # Remove ignored IPs
            if options['ignore']:
                sql += "WHERE ip_address NOT IN %s "
                sql_args.append(options['ignore'])
            
            sql += "GROUP BY ip_address, user_agent HAVING cnt BETWEEN %s AND %s"
            sql_args.append(options['min_threshold'])
            sql_args.append(options['max_threshold'])
            
            print(sql)
            print(sql_args)
            
            cursor.execute(sql, tuple(sql_args))
            ip_addresses = set([ (row[0],row[1]) for row in cursor.fetchall() ])
        # WITH
        
        # Get the # of visits per system
        visits_per_system = { }
        with connection.cursor() as cursor:
            sql = "SELECT system_id, count(*) AS cnt FROM core_systemvisit GROUP BY system_id HAVING cnt > %s"
            cursor.execute(sql, (str(options['min_visit']),))
            visits_per_system = dict([ (row[0],int(row[1])) for row in cursor.fetchall() ])
        # WITH
        #for system_id in sorted(visits_per_system.keys(), key=lambda x: -1*visits_per_system[x]):
            #print(System.objects.get(id=system_id), "=>", visits_per_system[system_id])
        #sys.exit(1)

        # For each ip/user pair, get the systems that they viewed
        all_visits = { }
        user_info = { }
        system_idx_xref = { }
        idx_system_xref = { }
        next_user_idx = 0
        next_system_idx = 0
        for ip, ua in ip_addresses:
            systems = list()
            #systems = set()
            visits = SystemVisit.objects.filter(ip_address=ip, user_agent=ua)
            
            for v in visits:
                # Skip anything that did not have enough total visits
                if not v.system.id in visits_per_system: continue
                
                if not v.system.id in system_idx_xref:
                    system_idx_xref[v.system.id] = next_system_idx
                    idx_system_xref[next_system_idx] = v.system.id
                    next_system_idx += 1
                if type(systems) is set:
                    systems.add(system_idx_xref[v.system.id])
                else:
                    systems.append(system_idx_xref[v.system.id])
            all_visits[next_user_idx] = systems
            user_info[next_user_idx] = (ip, ua)
            next_user_idx += 1
        ## FOR
        assert len(visits_per_system) == len(idx_system_xref)
        system_cnt = System.objects.all().count()
        #sys.exit(1)
        
        #for user_idx in sorted(all_visits.keys(), key=lambda x: -1*len(all_visits[x]))[:10]:
            #print(user_info[user_idx], "=>", len(all_visits[user_idx]))
        #sys.exit(1)
        
        print("# of Users:", next_user_idx)
        print("# of Sytems: %d (total=%d)" % (next_system_idx, system_cnt))
        
        data = np.zeros((next_user_idx, next_system_idx))
        for user_idx in all_visits.keys():
            for system_idx in all_visits[user_idx]:
                data[user_idx, system_idx] += 1
        print(data)
        sparsity = float(len(data.nonzero()[0]))
        sparsity /= (data.shape[0] * data.shape[1])
        sparsity *= 100
        print('Sparsity: {:4.2f}%'.format(sparsity))

        train_data, test_data = self.train_test_split(data)
        
        similarity = self.compute_similarity(train_data)
        print(similarity[:4, :4])
        pred = data.dot(similarity) / np.array([np.abs(similarity).sum(axis=1)])
        
        print('MSE: ' + str(self.get_mse(pred, test_data)))

        #print("# of IPs: %s" % len(ip_addresses))
        
        if options['clear']:
            SystemRecommendation.objects.all().delete()
        
        for system_idx in range(0, next_system_idx):
            recommendations = self.top_k_systems(similarity, system_idx, 5)
            system = System.objects.get(id=idx_system_xref[system_idx])
            print(system)
            for i in range(1, len(recommendations)):
                score = similarity[system_idx, recommendations[i]]
                other_sys = System.objects.get(id=idx_system_xref[recommendations[i]])
                
                if system == other_sys: continue
                
                if options['store']:
                    rec = SystemRecommendation(system=system, recommendation=other_sys, score=score)
                    rec.save()
                print("  + %s [%f]" % (other_sys, score))
            print()
        ## FOR

        return
    
    def top_k_systems(self, similarity, system_idx, k=6):
        #assert system_idx in mapper
        return [x for x in np.argsort(similarity[system_idx,:])[:-k-1:-1]]
    
    def train_test_split(self, data):
        test = np.zeros(data.shape)
        train = data.copy()
        for user_idx in range(data.shape[0]):
            test_data = np.random.choice(data[user_idx, :].nonzero()[0], 
                                            size=10, 
                                            replace=True)
            train[user_idx, test_data] = 0.
            test[user_idx, test_data] = data[user_idx, test_data]
            
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

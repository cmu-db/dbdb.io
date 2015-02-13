


rankings = """1.    1.  Oracle  Relational-DBMS 1439.72 +0.56
2.    2.  MySQL Relational-DBMS 1272.45 -5.06
3.    3.  Microsoft-SQL-Server Relational-DBMS 1177.48 -21.13
4.    5.  MongoDB Document-store  267.24  +16.35
5.    4.  PostgreSQL  Relational-DBMS 262.34  +7.85
6.    6.  DB2 Relational-DBMS 202.42  +2.29
7.    7.  Microsoft Access-Relational-DBMS 140.54  +1.41
8.    8.  Cassandra Wide-column-store 107.08  +8.34
9.    9.  SQLite  Relational-DBMS 99.56 +3.37
10.   10. Redis Key-value-store 99.21 +4.97
11.   11. Sybase ASE-Relational-DBMS 86.34 +2.55
12.   12. Solr  Search-engine 81.48 +4.74
13.   13. Teradata  Relationa-DBMS 69.45 +2.40
14.   14. HBase Wide-column-store 57.15 +3.56
15.   15. FileMaker Relational-DBMS 53.44 +1.74
16.   16. Elasticsearch Search-engine 52.84 +3.80
17.   17. Hive  Relational-DBMS 36.56 +1.17
18.   18. Informix  Relational-DBMS 35.90 +1.09
19.   20. Splunk  Search-engine 35.63 +2.56"""

def parseRankings(rankings):
  order = []
  for (i, line) in enumerate(rankings.splitlines()):
    line = line.split()
    data = {
    }
    data["order"] = i + 1
    data["name"] = line[2]
    data["score"] = int(float(line[4]))
    order.append(data)
  return order

for rank in parseRankings(rankings):
  print rank











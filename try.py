import csv
with open('keywordlist.csv','r') as a:
    reader=csv.reader(a,delimiter=',')
    for r in reader:
        for x in r:
            print(x)

import datetime
import os
import json
import csv
path = "D:\\TPTPFO\\sample\\(0,0,0)"
jsondata = None
csvpaths = []
results={}
def read_file(path):
        with open(path, "r") as rf:
            values = json.load(rf)
        return values
def defaultconverter(o):
  if isinstance(o, datetime.datetime):
      return o.__str__()

for root, dirs, files in os.walk(path):
    for file in files:
        if 'input.json' in files:
            jsondata=read_file(os.path.join(root, file))
        if file.startswith('TPT_') and file.endswith('.csv'):
            csvpaths.append(os.path.join(root, file))

if len(csvpaths)>0 and jsondata is not None:
    Board = jsondata['TestToolInfo']['SerialNumber']
    dut = str(jsondata['DutInfo']['ProductName'])+str(jsondata['DutInfo']['SerialNumber'])
    position = jsondata['TestToolInfo']['Position']
    if Board not in results:results[Board]={}
    if dut not in results[Board]: results[Board][dut]={}
    if position not in results[Board][dut]:results[Board][dut][position]={}
    #add csv data
    for cpath in csvpaths:
        pathli = cpath.split('\\')
        run = pathli[len(pathli)-3]
        Power = str(pathli[len(pathli)-2]).replace('W','')
        if Power not in results[Board][dut][position]:results[Board][dut][position][Power]={}
        #read from CSV
        finaldata = {"Time":[],"Prect":[],"PFO":[]}
        data = open(cpath)
        csvFile = csv.reader(data)
        cnt=0
        for lines in csvFile:
            if cnt !=0:
                finaldata['Time'].append(lines[0])
                finaldata['Prect'].append(lines[2])
                finaldata['PFO'].append(float(lines[14])/1000)
            cnt+=1
        # break
        results[Board][dut][position][Power][len(results[Board][dut][position][Power])+1]=finaldata
#update to final json
if len(results)>0:
    with open('Scripts\\Charts\\results.json', "w") as outfile:
        json.dump(results, outfile, default=defaultconverter)
    



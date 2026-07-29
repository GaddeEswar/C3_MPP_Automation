from Scripts.MainModule import JsonOperations
from datetime import datetime
class JsonReports():
    def __init__(self):
        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        self.MergeBestResults()
    def MergeBestResults(self):
        results={}
        if len(self.JsettingsData['JsonMerge']['JsonMergePath'])>0:
            for js in self.JsettingsData['JsonMerge']['JsonMergePath']:
                jsval = JsonOperations(js)
                jsonvalues = jsval.read_file()
                #Get SW,FW,DUT info
                key = jsonvalues['TestToolInfo']['SoftwareVersion']+'_'+jsonvalues['TestToolInfo']['FirmwareVersion']+'_'+jsonvalues['DutInfo']['BrandName']+'_'+jsonvalues['DutInfo']['SerialNumber']
                if key not in results:
                    results[key]={
                        "TestLab":{},
                        "TestExecutionDetails":{},
                        "ReportRemark":"",
                        "TestToolInfo":{},
                        "DutInfo":{},
                        "TestingScope":[],
                        "DigitalSignatureInfo":{}}
                if len(results[key]['TestLab']) == 0:
                    results[key]['TestLab'] = jsonvalues['TestLab']
                    results[key]['TestExecutionDetails'] = jsonvalues['TestExecutionDetails']
                    results[key]['ReportRemark'] = jsonvalues['ReportRemark']
                    results[key]['TestToolInfo'] = jsonvalues['TestToolInfo']
                    results[key]['DutInfo'] = jsonvalues['DutInfo']
                    results[key]['DigitalSignatureInfo'] = jsonvalues['DigitalSignatureInfo']
                    results[key]['TestExecutionDetails']['TestScope'].clear()
                    for TC in jsonvalues['TestingScope']:
                        if len(results[key]['TestingScope']) == 0:
                            results[key]['TestingScope'].append(TC)
                            results[key]['TestExecutionDetails']['TestScope'].append(TC['TestName'])
                        else:
                            status = False
                            id=0
                            while id < len(results[key]['TestingScope']):
                                if results[key]['TestingScope'][id]['TestName'] == TC['TestName']:
                                    status =True
                                    #popup operation
                                    if results[key]['TestingScope'][id]['TestResult'] != TC['TestResult']:
                                        if results[key]['TestingScope'][id]['TestResult'] in ['Inconclusive','Fail','NotRun'] and TC['TestResult'] in ['Pass'] or results[key]['TestingScope'][id]['TestResult'] in ['Inconclusive','NotRun'] and TC['TestResult'] in ['Pass','Fail']:
                                            results[key]['TestingScope'][id] = TC
                                    break
                                id+=1
                            if status == False:
                                #TC to be added
                                results[key]['TestingScope'].append(TC)
                                results[key]['TestExecutionDetails']['TestScope'].append(TC['TestName'])
        if len(results)>0:
            #put summary & export
            for key in results:
                passcount = 0
                failcount = 0
                Inclcount = 0
                NRcount = 0
                for TCS in results[key]['TestingScope']:
                    if TCS['TestResult'] == 'Pass':
                        passcount+=1
                    elif TCS['TestResult'] == 'Fail':
                        failcount+=1
                    elif TCS['TestResult'] == 'cls':
                        Inclcount+=1
                    elif TCS['TestResult'] == 'NotRun':
                        NRcount+=1
                ResStr = "Pass: "+str(passcount)+", Fail: "+str(failcount)+", Inconclusive: "+str(Inclcount)+", Not Run: "+str(NRcount)
                results[key]['TestExecutionDetails']['TestResult']=ResStr
                now = datetime.now()
                timestamp = now.strftime("%d%m%Y_%H%M%S")
                exportjson = JsonOperations(f'Results\\JsonReports\\'+'JSONmerge_'+key+'_'+timestamp+'.json')
                exportjson.update_file(results[key])
# jm = JsonReports()
# jm.MergeBestResults()
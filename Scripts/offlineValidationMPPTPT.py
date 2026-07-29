import traceback
import uuid
import os
import zipfile
import csv

from Scripts.MainModule import JsonOperations,APIOperations,GeneralMethods
from datetime import datetime,date
import time

class OfflineValidationMPPTPT():
    def __init__(self,TestID='',ProjectJson='',TracePath='',mode='TPT'):
        print('val call TPT')
        self.TestID =TestID
        self.ProjectJson = ProjectJson
        self.TracePath = TracePath
        self.mode = mode
        self.Header = {}
        self.timing_map = {}
        self.stability=None
        self.initialVoltage=None
        #Get inputs from JSON
        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        self.Jtester = JsonOperations('json/Tester.json')
        self.JtesterData =self.Jtester.read_file()
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JQI = JsonOperations('json/QIconfig.json')
        self.JQIData = self.JQI.read_file()
        self.JMOI = JsonOperations('json/MOIJson.json')
        self.JMOIData = self.JMOI.read_file()
        self.Json_TC = self.JMOIData[self.TestID]
        self.TimeTolr = self.JMOIData['TT_4']
        self.Json_Def = self.JMOIData['default_Values']
        self.JTestConf = JsonOperations('json/TestConfig.json')
        self.JTestConfData = self.JTestConf.read_file()  
        self.JPhaPkt = JsonOperations('json/PhasePackets.json')
        self.JPhaPktData = self.JPhaPkt.read_file()  
        self.JTCP = JsonOperations('json/Test_config_properties.json')
        self.JTCPData = self.JTCP.read_file()
        self.FinalRep = JsonOperations(self.JTCPData['test_config_data']['Report_path'])
        self.FinalRepData = self.FinalRep.read_file()
        self.conRep = JsonOperations(self.JsettingsData['ConsolidatedJSON'])
        self.conRepData = self.conRep.read_file()
        #Get Packets###########################
        self.PktAPI = APIOperations(url=self.JapiData[self.mode]['GetCCLinePackets'],retype='json')
        self.file_list = self.PktAPI.GetRequest()
        #Get Signales##########################
        self.AllChannelData = self.GetAllChannelData(index='2')
        self.AllChannelData3 =self.GetAllChannelData(index='3')
        #call func
        self.UpdateHeaderInfo()
        self.flows = self.SegricatePackets()
        self.ValidationForFlow()
    #1
    def UpdateHeaderInfo(self):
        now = datetime.now()
        timestamp = now.strftime("%d%m%Y_%H%M%S")
        jsondata = JsonOperations(self.ProjectJson)
        jsonValues = jsondata.read_file()
        self.Header['DBStatus']= 'NotUpdated'
        self.Header['UID'] = str(uuid.uuid1())
        self.Header['TestcaseID'] = self.Json_TC['TC_id']
        self.Header['TestcaseName']= self.Json_TC['Testcase_Name']
        self.Header['ChapterID']=self.Json_TC['TC_ChapterID']
        self.Header['ChapterName']=self.Json_TC['TC_Chapter']
        self.Header['CoilUsed']= self.Json_TC['Coils'][0]
        self.Header['potentialPower']=self.JQIData[self.mode]['potentialPower']
        self.Header['Position'] = self.Json_TC['Pos_applicable'][0]
        self.Header['SWVersion'] = jsonValues['TestToolInfo']['SoftwareVersion']
        self.Header['FWVersion'] = jsonValues['TestToolInfo']['FirmwareVersion']
        self.Header['HWVersion'] = jsonValues['TestToolInfo']['HardwareVersion']
        self.Header['BoardNo'] = jsonValues['TestToolInfo']['SerialNumber']
        self.Header['BoardModel'] = jsonValues['TestToolInfo']['ModelName']
        self.Header['CapturePath'] = self.TracePath
        pathlist = self.TracePath.split("\\")
        self.Header['ProjectName'] = pathlist[len(pathlist)-4]
        # self.Header['Run'] = int(pathlist[len(pathlist)-3].split('Run')[1])
        self.Header['Run'] = pathlist[len(pathlist)-3]
        #TBD 
        self.Header['TestedTime'] ='NA'
        self.Header['ValidatedTime']=timestamp
        self.Header['DUTName']= jsonValues['DutInfo']['BrandName']
        self.Header['DUTID']= jsonValues['DutInfo']['ProductName']
        self.Header['DUTSL']= jsonValues['DutInfo']['SerialNumber']
        self.Header['QiID'] = jsonValues['DutInfo']['QiID']
        self.Header['TestLab']=self.JQIData[self.mode]['testLab'] = jsonValues['TestLab']['LabName'] 
        self.Header['Engineer']=self.JQIData[self.mode]['testEngineer'] = jsonValues['TestLab']['TestEngineer']

        # self.Header['DUTName']= self.JQIData[self.mode]['manufacturer'] if jsonValues['DutInfo']['ProductName'] =='' else jsonValues['DutInfo']['ProductName']
        # self.Header['DUTID']=self.JQIData[self.mode]['modelNumber'] if jsonValues['DutInfo']['SerialNumber'] =='' else jsonValues['DutInfo']['SerialNumber']
        # self.Header['TestLab']=self.JQIData[self.mode]['testLab'] if jsonValues['TestLab']['LabName'] =='' else jsonValues['TestLab']['LabName']
        # self.Header['Engineer']=self.JQIData[self.mode]['testEngineer'] if jsonValues['TestLab']['TestEngineer'] =='' else jsonValues['TestLab']['TestEngineer']
    #2
    def SegricatePackets(self):
        packets = {}
        cnt = 0
        sid = 0
        limit=[]
        #Find applicable length
        while sid < len(self.file_list)-1:
            if all(rs in self.file_list[sid].get('pktType') for rs in ['Test_Started',self.Json_TC['SeqID']]):
                eid = sid+1
                while eid < len(self.file_list)-1:
                    if all(rs in self.file_list[eid].get('pktType') for rs in ['Test_Stop',self.Json_TC['SeqID']]): 
                        limit=[sid,eid]
                        break
                    elif all(rs in self.file_list[eid].get('pktType') for rs in ['Shutdown','next_subtest']): 
                        limit=[sid,eid]
                        break
                    eid+=1
                break
            sid+=1
        print('Limit',limit)
        if len(limit)>1:
            id = limit[0]
            while id < limit[1]:
                start = 0
                end = 0
                if 'Ping Initiated' in self.file_list[id].get('pktType'):
                    print('pd',id)
                    #find Shutdown
                    sd= self.GetPacketDetails(packet='Shutdown',limit=[id,limit[1]])
                    if len(sd)>2:
                        # print('sd',sd)
                        #ensure no PD recevied btw PD-SD
                        ilPD = self.GetPacketDetails(packet='Ping Initiated',limit=[id+1,sd[2]])
                        if len(ilPD)>1: id = ilPD[2]
                        # #check TestStop recevied before SD
                        # ilTS = self.GetPacketDetails(packet='Shutdown',limit=[id,sd[2]])
                        # if len(ilTS)>1: sd = ilTS
                        start = id
                        end = sd[2]
                        id = end
                    else:
                        #consider for the End of packet
                        start = id
                        end = limit[1]
                        id = end
                    #consider seq. has length > 3 and ss in flow
                    SS = self.GetPacketDetails(packet='Signal strength',limit=[start,end])
                    if (end -start) > 3 and len(SS)>1:
                        cnt +=1
                        # print(start,end)
                        fq = GeneralMethods.GetFloatFromStr(self.file_list[start].get("value"))
                        index = 2 if fq[0] >= 300 else 1
                        packets[cnt]={"Limit":[start,end],"Flow":index}
                else: id+=1
            #consider last 2 seq.
            flow1=None
            flow2=None
            tmpflow1=None
            for seq in packets:
                if packets[seq]['Flow']!=0:
                    if packets[seq]['Flow']==1 and flow2==None:
                        flow1 = packets[seq]
                    elif packets[seq]['Flow']==2 and flow1!=None:
                        if tmpflow1 ==None:
                            flow2 = packets[seq]
                        else:
                            flow1=tmpflow1
                            flow2 = packets[seq]
                            tmpflow1=None
                    elif  packets[seq]['Flow']==1 and flow2!=None:
                        tmpflow1=packets[seq]
            print('pkts',packets)
            return {1:flow1,2:flow2}
    #3
    def ValidationForFlow(self):     
        if len(self.flows)>0:
            #find last best flow and perform the validation
            for flow in self.flows:
                if self.flows[flow] is not None:
                    print(self.flows[flow])
                    lmt = self.flows[flow]['Limit']
                    index = self.flows[flow]['Flow']
                    remarks =[]
                    result = []
                    # self.timing_map['Illegal'] =[]
                    # self.timing_map['AddPkt']={}
                    # self.timing_map['EPT'] ={}
                    # self.timing_map['XCE'] =[]
                    # self.timing_map['PLA'] =[]
                    # self.timing_map['Loads']={}
                    # self.Generalcall(lmt,self.timing_map)
                    self.CheckPktSequnce(lmt,index)
                    #Calculat finalresult
            self.Header['TCresult']=self.CheckFinalResult()
            self.UpdateToJsonReport()
            print(self.timing_map)
    #4
    def CheckPktSequnce(self,limit,index):
        # print('initial',limit,type(index))
        PkseqData = self.JPhaPkt.read_file()
        packets = PkseqData[self.mode]['Packets']
        Pkseq = PkseqData[self.mode]['PacketSeq']
        PTPkts = []
        # print(Pkseq['Standard'])
        seq = Pkseq['Standard']
        # print('ini',seq)
        # if index==1 : seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['127_nego'])
        if index not in self.timing_map:self.timing_map[index]={}
        self.timing_map[index]['Illegal']=[]
        seqpos = 1
        id = limit[0]+1
        while id < limit[1]:
            # print(id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),seq[seqpos],seq)
            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                pktstatus = False
                if len(packets[seq[seqpos]]['values']):
                    if any(rs in self.file_list[id].get('value') for rs in packets[seq[seqpos]]['values']) and packets[seq[seqpos]]['Descr'] in self.file_list[id].get('pktType'):pktstatus=True
                else:
                    if packets[seq[seqpos]]['Descr'] in self.file_list[id].get('pktType'):pktstatus=True
                if pktstatus == True:
                    if packets[seq[seqpos]]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[seq[seqpos]]['PhaseID']]={}
                    if seq[seqpos] not in self.timing_map[index][packets[seq[seqpos]]['PhaseID']] : self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]] = []
                    #check response if required, id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')
                    # if len(packets[seq[seqpos]]['Response'])>0:
                    rid = id+1
                    while rid <= limit[1]:
                        if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                            if all(rs not in self.file_list[rid].get('pktType') for rs in packets[seq[seqpos]]['Response']):
                                self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                            else:
                                self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                            break
                        elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                            self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                            # print('Received Pkt instead of response')
                            break
                        rid+=1
                    if len(self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]]) == 0: self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                    # Check for PT pkts
                    if packets[seq[seqpos]]['PhaseID'] == 'PT' and 'PT' in self.file_list[id].get('description'):
                        id+=1
                        while id < limit[1]:
                            # print(id)
                            PTpktstatus = False
                            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                                if 'PT' in self.file_list[id].get('description'):
                                    print(PTPkts)
                                    for PTpkt in PTPkts:
                                        if packets[PTpkt]['Descr'] in self.file_list[id].get('pktType'):
                                            PTpktstatus=True
                                    # for PTpkt in PTPkts:
                                        # print(packets[PTpkt]['Descr'] ,self.file_list[id].get('pktType'))
                                        # if packets[PTpkt]['Descr'] in self.file_list[id].get('pktType') :
                                            # print(id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),PTpkt)
                                            if packets[PTpkt]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[PTpkt]['PhaseID']]={}
                                            if PTpkt not in self.timing_map[index][packets[PTpkt]['PhaseID']] : self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt] = []
                                            # if len(packets[PTpkt]['Response'])>0:
                                            rid = id+1
                                            while rid < limit[1]:
                                                if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                                                    if all(rs not in self.file_list[rid].get('pktType') for rs in packets[PTpkt]['Response']):
                                                        self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                                    else:
                                                        self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                                                    break
                                                elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                                                    self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                                    # print('Received Pkt instead of response')
                                                    break
                                                rid+=1
                                            id=rid
                                        # else: id+=1
                                    if PTpktstatus == False : id+=1
                                else:
                                    print('Not expected1')
                                    #check for Cloak
                                    if 'Cloak' in self.file_list[id].get('pktType'):
                                        self.GetCloakPkts(index,id,packets)
                                        id+=1
                                    else:
                                        #add to illegal
                                        pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                                        resp =None
                                        tmpid = id+1
                                        #check for response
                                        while tmpid < limit[1]:
                                            if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                                break
                                            elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                                resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                                            tmpid+=1
                                        self.timing_map[index]['Illegal'].append([pkt,resp])
                                        id=tmpid
                            else:id+=1
                    #Check for ID packet
                    # print(seq[seqpos])
                    if seq[seqpos] =='ID':
                        res = self.GetPayloadValue('Ext',id)
                        if all(rs in '0x01' for rs in res):
                            seq.extend(Pkseq['ExID'])
                        seq.extend(Pkseq['CNF'])
                    # ExtID
                    if seq[seqpos] =='ExID':
                        res = self.GetPayloadValue('Restricted',id)
                        # print(res,'ExID')
                        if all(rs in '0x00' for rs in res):
                            if index == 1:
                                seq.extend(Pkseq['127_nego'])
                            if index == 2:
                                seq.extend(Pkseq['360_nego'])
                                seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['MPP_PT'])
                                PTPkts = self.JPhaPktData[self.mode]['PacketSeq']['MPP_PT']
                        else:
                            if index == 2:
                                # print('BPP mode')
                                seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['BPP_PT'])
                                PTPkts = self.JPhaPktData[self.mode]['PacketSeq']['BPP_PT']
                    id=rid
                    seqpos+=1
                else:
                    print('Not expected2')
                    opt_pktstatus = False
                    opt_pkt = None
                    #if phase = Nego , check the packet is a optional packet
                    if packets[seq[seqpos]]['PhaseID'] == "Nego":
                        optseq = '360_nego_opt' if index == 2 else '128_nego_opt'
                        if optseq in  Pkseq:
                            print('Op pkt check nego')
                            for optnegopkt in Pkseq['360_nego_opt']:
                                if len(packets[optnegopkt]['values']):
                                    if any(rs in self.file_list[id].get('value') for rs in packets[optnegopkt]['values']) and packets[optnegopkt]['Descr'] in self.file_list[id].get('pktType'):
                                        opt_pktstatus=True
                                        opt_pkt = optnegopkt
                                        break
                                else:
                                    if packets[optnegopkt]['Descr'] in self.file_list[id].get('pktType'):
                                        opt_pktstatus=True
                                        opt_pkt = optnegopkt
                                        break
                    if opt_pktstatus == True:
                        if packets[opt_pkt]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[opt_pkt]['PhaseID']]={}
                        if opt_pkt not in self.timing_map[index][packets[opt_pkt]['PhaseID']] : self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt] = []
                        rid = id+1
                        while rid <= limit[1]:
                            if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                                if all(rs not in self.file_list[rid].get('pktType') for rs in packets[seq[seqpos]]['Response']):
                                    self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                else:
                                    self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                                break
                            elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                                self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                # print('Received Pkt instead of response')
                                break
                            rid+=1
                        id=rid
                        # seqpos+=1
                    else:
                        # id+=1
                        # pass
                        #check for ill / add pkts
                        # if self.file_list[id].get('description') !=  packets[seq[seqpos]]['PhaseID'] or (self.file_list[id].get('description') =='Nego' and any(rs in self.file_list[id].get('pktType') for rs in ['ADC','DSR','SADC','SADT'])):
                        pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                        resp =None
                        tmpid = id+1
                        #check for response
                        while tmpid < limit[1]:
                            print(tmpid)
                            if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                break
                            elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                            tmpid+=1
                        self.timing_map[index]['Illegal'].append([pkt,resp])
                        # print(tmpid,id)
                        id=tmpid
            else: id+=1
        #add PD&SD
        self.timing_map[index]['General'] ={
            "PD":[limit[0],self.file_list[limit[0]].get('startTime'),self.file_list[limit[0]].get('stopTime')],
            "SD":[limit[1],self.file_list[limit[1]].get('startTime'),self.file_list[limit[1]].get('stopTime')]
        }
        #Get Freq data
        if 'PD' in self.timing_map[index]['General']:
            fq = GeneralMethods.GetFloatFromStr(self.file_list[limit[0]].get("value"))
            self.timing_map[index]['General']['FOP']=[limit[0],self.file_list[limit[0]].get('startTime'),self.file_list[limit[0]].get('stopTime'),fq[0]]
        #GetLoads
        self.timing_map[index]['Loads']={}
        id = limit[0]
        while id < limit[1]:
            # print(id,self.file_list[id].get('pktType'))
            if 'Set_Load' in self.file_list[id].get('pktType'):
                self.timing_map[index]['Loads'][self.file_list[id].get('pktType').split(':')[0].split(' ')[1]] = id
            id+=1
        # apply validations
        self.timing_map[index]['Timings']=self.timing_checks(index)
        self.timing_map[index]['Measures'] = self.Measures(index)
        self.timing_map[index]['OtherChecks'] = self.OtherChecks(index)
    ##support func______________________________
    def GetRunTime(self):
        TcStartAPI = APIOperations(url=self.JapiData[self.mode]['GetWaveformStartTime'],retype='json')
        TCstartTime = TcStartAPI.GetRequest()
        TcStopAPI = APIOperations(url=self.JapiData[self.mode]['GetWaveformStopTime'],retype='json')
        TCstopTime = TcStopAPI.GetRequest()
        return[TCstartTime,TCstopTime/100000000]
    def GetAllChannelData(self,index='2'):
        ACD={}
        TestTime = self.GetRunTime()
        if TestTime[1]/60 >15:
            print(TestTime[1]/60)
            plottime = int(((TestTime[1]*1000)/2.5)-80)
        else:
            plottime = int(((TestTime[1]*1000)/1.0510)-80)
        SignalAPI = APIOperations(url=self.JapiData[self.mode]['GetAllChannelData'],retype='json',param1=TestTime[1],param2=plottime)
        data = SignalAPI.GetRequest()
        if index in data:
            ACD['RV']=data[index]
            ACD['starttime'] = data[index]['absoluteStartTime']
            ACD['endtime'] = data[index]['absoluteEndTime']
            ACD['records'] = len(data[index]['displayDataChunk'])
            ACD['Diff'] =  ((ACD['endtime']-ACD['starttime'])/100000)
            ACD['Interval'] = (ACD['Diff']/ACD['records'])
        return ACD
    def GetPacketDetails(self,packet='',value=None,limit=[],timelimit=None):
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                if packet in self.file_list[id].get('pktType') and value in self.file_list[id].get('value') if value is not None else packet in self.file_list[id].get('pktType'):
                    if timelimit is None:
                        return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                    else:
                        if self.file_list[id].get('startTime') >= timelimit:
                            return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        else:
            while id != limit[1]:
                if all(rs in self.file_list[id].get('pktType') for rs in packet) and value in self.file_list[id].get('value') if value is not None else packet in self.file_list[id].get('pktType'):
                    return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1

        return[0]
    def Findflow(self,limit):
        id = limit[0]
        index = 0
        while id<limit[1]:
            if 'Identification' in self.file_list[id].get('pktType'):
                index=1
            if 'Specific Request' in self.file_list[id].get('pktType') and 'Frequency Selection: 360 Khz' in self.file_list[id].get('value'):
                index = 1
                break
            if 'Extended_Power_Receiver_Capabilities' in self.file_list[id].get('pktType'):
                index = 2
                break
            elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' in self.file_list[id].get('value'):
                index = 1
                break
            elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' not in self.file_list[id].get('value'):
                index = 2
                break
            elif 'FOP:' in  self.file_list[id].get('value'):
                if float(self.file_list[id].get('value').split(':')[1].split(' ')[0]) >300:
                    index =2
                    break
                else:
                    index=1
                    break
            id+=1
        # print(limit,index)
        return index
    def GetPayloadValue(self,payloadname,index):
        # print('Payload check',self.file_list[index].get('pktType'))
        results=[]
        for d1 in self.file_list[index]['header_Payload']['childelement']:
            for d2 in d1['childelement']:
                # print(d2['sDecodedValue'])
                if payloadname in d2['sDecodedValue']:
                    results.append(d2['sRawData'])
        return results 
    def timing_checks(self,index):
        AllTimings={"tresponse":[],"twake":[],"tstart":[],"tsilent":[],"tintervalXCE-XCE":[],"treceviedPLA-PLA":[]}
        ##Twake check--------------------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['twake']
        AllTimings['twake_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['twake']='NA'
        AllTimings['twake_res']='NA'
        try:
            if 'Ping' in self.timing_map[index] and 'General' in self.timing_map[index]:
                AllTimings['twake']=[]
                res = round((self.timing_map[index]['Ping']['SS'][0][0][1] - self.timing_map[index]['General']['PD'][1])*1000,2)+5.5
                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                    AllTimings['twake'].append(res)
                    remarks.append(f"Measured twake {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{self.timing_map[index]['General']['PD'][0]}")
                if len(remarks)>0:
                    AllTimings['twake_res'] ='Fail'
                    AllTimings['twake']=','.join(map(str,AllTimings['twake']))
                else:
                    AllTimings['twake_res'] ='Pass'
                    AllTimings['twake']='No Mismatch'
                AllTimings['twake_remark'] = '.'.join(remarks)
        except Exception as e:
            er = traceback.print_exc()
            AllTimings['twake_remark'] = '' if er is None else er
            AllTimings['twake_res'] ='Fail'
        ##Tstart check-------------------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['tstart']
        AllTimings['tstart_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tstart_res']='NA'
        AllTimings['tstart']='NA'
        Pktslist =[]
        for phase in self.timing_map[index]:
            if phase in ['Ping','ID&CFG']:
                for pkts in self.timing_map[index][phase]:
                    pk = self.timing_map[index][phase][pkts]
                    if type(pk)==list:
                        Pktslist.append(pk[0][0])
        if len(Pktslist)>0:
            id=0
            AllTimings['tstart']=[]
            AllTimings['tstart_res']='Fail'
            while id < len(Pktslist)-1:
                res = round((Pktslist[id+1][1]-Pktslist[id][2])*1000,2)+5.5
                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                    AllTimings['tstart'].append(res)
                    remarks.append(f"Measured tstart {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{Pktslist[id][0]}")
                id+=1
            if len(remarks)>0:
                AllTimings['tstart_res'] ='Fail'
                AllTimings['tstart']=','.join(map(str,AllTimings['tstart']))
            else:
                AllTimings['tstart_res'] ='Pass'
                AllTimings['tstart']='No Mismatch'
            AllTimings['tstart_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
            AllTimings['tstart_remark'] = '.'.join(remarks)
        ##tsilent check-------------------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['tsilent']
        AllTimings['tsilent_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tsilent_res']='NA'
        AllTimings['tsilent']='NA'
        Pktslist =[]
        for phase in self.timing_map[index]:
            if phase in ['Ping','ID&CFG']:
                for pkts in self.timing_map[index][phase]:
                    pk = self.timing_map[index][phase][pkts]
                    if type(pk)==list:
                        Pktslist.append(pk[0][0])
        if len(Pktslist)>0:
            id=0
            AllTimings['tsilent']=[]
            AllTimings['tsilent_res']='Fail'
            while id < len(Pktslist)-1:
                res = round((Pktslist[id+1][1]-Pktslist[id][2])*1000,2)
                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                    AllTimings['tsilent'].append(res)
                    remarks.append(f"Measured tsilent {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{Pktslist[id][0]}")
                id+=1
            if len(remarks)>0:
                AllTimings['tsilent_res'] ='Fail'
                AllTimings['tsilent']=','.join(map(str,AllTimings['tsilent']))
            else:
                AllTimings['tsilent_res'] ='Pass'
                AllTimings['tsilent']='No Mismatch'
            AllTimings['tsilent_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
            AllTimings['tsilent_remark'] = '.'.join(remarks)
        #tresponse, pass all flows and get the tresponse for the pkts has response
        remarks = []
        tol= self.Json_Def['tresponse']
        for phase in self.timing_map[index]:
            if phase not in ['Illegal','Cloak']:
                for pkts in self.timing_map[index][phase]:
                    pk = self.timing_map[index][phase][pkts]
                    if type(pk) == list:
                        for pks in pk:
                            if type(pks) == list:
                                if len(pks)>1:
                                    print(pks)
                                    res = round((pks[1][2] - pks[0][2])*1000,2)
                                    if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                                        AllTimings['tresponse'].append(res)
                                        remarks.append(f"Measured tresponse {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{pks[1][0]} ")
        if len(remarks)>0:
            AllTimings['tresponse_res'] ='Fail'
            AllTimings['tresponse']=','.join(map(str,AllTimings['tresponse']))
        else:
            AllTimings['tresponse_res'] ='Pass'
            AllTimings['tresponse']='No Mismatch'
        AllTimings['tresponse_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tresponse_remark'] = '.'.join(remarks)
        #Tintervel XCE-----------------------------------------------------------
        remarks = []
        tol= self.Json_Def['tintervalXCE-XCE']
        AllTimings['tintervalXCE-XCE_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tintervalXCE-XCE_res']='NA'
        AllTimings['tintervalXCE-XCE']='NA'
        try:
            if 'PT' in self.timing_map[index]:
                if 'XCE' in self.timing_map[index]['PT']:
                    XCEpkt = self.timing_map[index]['PT']['XCE']
                    AllTimings['tintervalXCE-XCE']=[]
                    if len(XCEpkt)>0:
                        id = 0
                        while id < len(XCEpkt)-1:
                            if (XCEpkt[id+1][0][0] - XCEpkt[id][0][0]) <=4:
                                res= round((XCEpkt[id+1][0][1] - XCEpkt[id][0][2])*1000,2)
                                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                                        AllTimings['tintervalXCE-XCE'].append(res)
                                        remarks.append(f"Measured tintervalXCE-XCE {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{XCEpkt[id][0][0]}")
                            id+=1
                        if len(remarks)>0:
                            AllTimings['tintervalXCE-XCE_res'] ='Fail'
                            AllTimings['tintervalXCE-XCE']=','.join(map(str,AllTimings['tintervalXCE-XCE']))
                        else:
                            AllTimings['tintervalXCE-XCE_res'] ='Pass'
                            AllTimings['tintervalXCE-XCE']='No Mismatch'
                        AllTimings['tintervalXCE-XCE_remark'] = '.'.join(remarks)  
        except Exception as e:
            er = traceback.print_exc()
            AllTimings['tintervalXCE-XCE_remark'] = '' if er is None else er
            AllTimings['tintervalXCE-XCE_res'] ='Fail'
        #Treceived PLA--------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['treceviedPLA-PLA']
        AllTimings['treceviedPLA-PLA_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['treceviedPLA-PLA_res']='NA'
        AllTimings['treceviedPLA-PLA']='NA'
        try:
            if 'PT' in self.timing_map[index]:
                if 'PLA' in self.timing_map[index]['PT']:
                    PLApkt = self.timing_map[index]['PT']['PLA']
                    AllTimings['treceviedPLA-PLA']=[]
                    if len(PLApkt)>0:
                        id = 0
                        while id < len(PLApkt)-1:
                            res= round((PLApkt[id+1][0][1] - PLApkt[id][0][2])*1000,2)
                            if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                                    AllTimings['treceviedPLA-PLA'].append(res)
                                    remarks.append(f"Measured treceviedPLA-PLA {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{PLApkt[id][0][0]}")
                            id+=1
                        if len(remarks)>0:
                            AllTimings['treceviedPLA-PLA_res'] ='Fail'
                            AllTimings['treceviedPLA-PLA']=','.join(map(str,AllTimings['treceviedPLA-PLA']))
                        else:
                            AllTimings['treceviedPLA-PLA_res'] ='Pass'
                            AllTimings['treceviedPLA-PLA']='No Mismatch'
                        AllTimings['treceviedPLA-PLA_remark'] = '.'.join(remarks)  

        except Exception as e:
            er = traceback.print_exc()
            AllTimings['treceviedPLA-PLA_remark'] = '' if er is None else er
            AllTimings['treceviedPLA-PLA_res'] ='Fail'
        # print(AllTimings)
        return(AllTimings)
    def Measures(self,idx):
        if str(idx) in self.Json_TC['App_Measures']:
            self.GetInitailVoltage(idx)
            Plotstarttime = (self.AllChannelData['starttime']/100000)
            AllMeasures={}
            self.XCEref=None
            if len(self.Json_TC['App_Measures'][str(idx)])>0:
                for apmes in self.Json_TC['App_Measures'][str(idx)]:
                    # print('Xce',self.XCEref,apmes,AllMeasures)
                    if apmes in ['Vrect']:
                        if self.stability is not None:
                            res = self.CalculateVoltTwindow(self.stability,self.AllChannelData)
                            AllMeasures['Vrect'] =  res[0]
                    if apmes in ['Prect']: 
                        if self.stability is not None:
                            res = self.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                            AllMeasures['Prect'] =  round(res[0]*AllMeasures['Vrect'],3)
                    if apmes in ['Vrect_delta']:
                        #Get 1st v after 1st load
                        if self.stability is not None:
                            res = self.CalculateVoltTwindow(self.stability,self.AllChannelData)
                            AllMeasures['VrectMes'] =  res[0]
                            #Get 2nd v after 2nd load
                            limit = [self.timing_map[2]['Loads'][self.Json_TC['load_names'][1]],len(self.file_list)]
                            res = self.GetStableBtwLimits(limit)
                            if res is not None:
                                stable2=res[0]
                                #based on the req. get vrect max or min,by adding 2 sec
                                maxtime = (float(self.file_list[stable2].get('stopTime'))*1000)+2000
                                # VMaxlist = []
                                # VMinlist =[]
                                VRlist=[]
                                tid =stable2+1
                                print(tid,maxtime)
                                while tid < len(self.file_list):
                                    if any(rs in self.file_list[tid].get('pktType') for rs in ['Extended Control Error','Control Error']):
                                        if float(self.file_list[tid].get('startTime')*1000)<=maxtime:
                                            #calculate vrect min /max for all XCE twin time
                                            xceEtime = self.file_list[tid].get('startTime')*1000
                                            xceSindex = int((xceEtime-11)/self.AllChannelData['Interval'])
                                            xceEindex = int((xceEtime-8)/self.AllChannelData['Interval'])
                                            id = xceSindex
                                            Vrectlist =[]
                                            cnt =0
                                            # Vrectmax = 0
                                            # Vrectmin = 0
                                            while id < xceEindex:
                                                Vrectlist.append(round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4))
                                                # if round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4) > Vrectmax or Vrectmax==0: 
                                                #     Vrectmax = round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4)
                                                # if round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4) < Vrectmin or Vrectmin==0 : 
                                                #     Vrectmin = round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4)
                                                id+=1
                                            # VMaxlist.append(Vrectmax)
                                            # VMinlist.append(Vrectmin)
                                            VRlist.append(sum(Vrectlist)/len(Vrectlist))
                                        else:break
                                    tid+=1
                                # print(VMaxlist,VMinlist)
                                AllMeasures['Vrect'] = max(VRlist) if self.Json_TC['App_Measures'][str(idx)]['Vrect_delta']['VrectType']=='MAX' else min(VRlist)
                                AllMeasures['Vrect_delta'] = round(abs(AllMeasures['Vrect']-AllMeasures['VrectMes']),2)
                                AllMeasures['XCEcount'] = res[1]
                                if 'TxceStable' in self.Json_TC['App_Measures'][str(idx)]:
                                    AllMeasures['TxceStable'] = round((self.file_list[stable2].get('startTime') - self.file_list[limit[0]].get('startTime'))*1000,2)
                    if apmes in ['Vrect_ping1','Vrect_ping360']:
                        AllMeasures[apmes]=None
                        if 'General' in self.timing_map[idx]:
                            lmttmp = [self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]]
                            id = lmttmp[0]
                            while id < lmttmp[1]:
                                if 'Signal strength' in self.file_list[id].get('pktType'):
                                    sigtime = (self.file_list[id].get('startTime')*1000)-10
                                    index = int((sigtime)/self.AllChannelData['Interval'])
                                    AllMeasures[apmes] = round(abs(self.AllChannelData['RV']['displayDataChunk'][index]),2)
                                    break
                                id+=1
                    if apmes in ['Vrect_pingx']:
                        AllMeasures['Vrect_pingx']=None
                        if all(rs in self.timing_map[idx] for rs in ['General','Ping']):
                            lmttmp = [self.timing_map[idx]['General']['PD'][0],0]
                            ssindex = self.timing_map[idx]['Ping']['SS'][0][0][0]
                            id=lmttmp[0]
                            while id > lmttmp[1]:
                                if self.file_list[ssindex].get('pktType') in self.file_list[id].get('pktType') and  self.file_list[ssindex].get('value') in self.file_list[id].get('value'):
                                    sigtime = (self.file_list[id].get('startTime')*1000)-10
                                    index = int((sigtime)/self.AllChannelData['Interval'])
                                    AllMeasures['Vrect_pingx'] = round(abs(self.AllChannelData['RV']['displayDataChunk'][index]),2)
                                    break
                                id-=1
                    if apmes in ['Vrect_max']:
                        AllMeasures['Vrect_max']=None
                        vlot = 0
                        loadindex = self.timing_map[idx]['Loads'][self.Json_TC['load_names'][1]]
                        sindex = int((((self.file_list[loadindex].get('startTime')-1)*1000))/self.AllChannelData['Interval'])
                        eindex = int((((self.file_list[loadindex].get('startTime')+1)*1000))/self.AllChannelData['Interval'])
                        id = sindex
                        while id <= eindex:
                            if round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4) > vlot : vlot = round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),4)
                            id+=1
                        AllMeasures['Vrect_max']=vlot
                    if apmes in ['Vrectfinal0']:
                        AllMeasures['Vrectfinal0']=None
                        if self.stability is not None:
                            res = self.CalculateVoltTwindow(self.stability,self.AllChannelData)
                            AllMeasures['Vrectfinal0'] =  res[0]
                    if apmes in ['Vrectfinal1']:
                        AllMeasures['Vrectfinal1']=None
                        # print(self.stability)
                        if self.stability is not None:
                            lmt = [self.stability+4,len(self.file_list)-1]
                            ideal = self.GetPacketDetails(packet='MPP_XCE_Stabilized',limit=lmt)
                            if len(ideal)>1:
                                #find XCE packet before ideal
                                XCE =  self.GetPacketDetails(packet='Extended Control Error',limit=[ideal[2],lmt[0]])
                                self.XCEref=XCE
                                if len(XCE)>1:
                                    res = self.CalculateVoltTwindow(XCE[2],self.AllChannelData)
                                    AllMeasures['Vrectfinal1'] =  res[0]
                    if apmes in ['Vrectfinal2']:
                        AllMeasures['Vrectfinal2']=None 
                        if self.XCEref is not None:
                            lmt = [self.XCEref[2]+4,len(self.file_list)-1]
                            ideal = self.GetPacketDetails(packet='MPP_XCE_Stabilized',limit=lmt)
                            if len(ideal)>1:
                                #find XCE packet before ideal
                                XCE =  self.GetPacketDetails(packet='Extended Control Error',limit=[ideal[2],lmt[0]])
                                if len(XCE)>1:
                                    res = self.CalculateVoltTwindow(XCE[2],self.AllChannelData)
                                    AllMeasures['Vrectfinal2'] =  res[0]
                    if apmes in ['VrecrfinalComp']:
                        AllMeasures['VrecrfinalComp']=str(AllMeasures['Vrectfinal0'])+':'+str(AllMeasures['Vrectfinal1'])+':'+str(AllMeasures['Vrectfinal2'])
                    if apmes in['G1']:
                        AllMeasures['G1']=None
                        AllMeasures['Vrect1'] = None
                        AllMeasures['inverterV1']=None
                        if self.initialVoltage is not None:
                            #Get inverterV1
                            inverterV1 = None
                            id = self.stability
                            while id < len(self.file_list):
                                if 'Inverter_Voltage' in self.file_list[id].get('pktType'):
                                    inverterV1 = float(self.file_list[id]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'].split(' ')[1].split('V')[0])
                                    break
                                id+=1
                            #cal G1
                            if inverterV1 is not None: 
                                G1 = self.initialVoltage/inverterV1
                                AllMeasures['Vrect1'] = self.initialVoltage
                                AllMeasures['inverterV1'] = inverterV1
                                AllMeasures['G1'] = round(G1,2)
                    if apmes in['G2']:
                        AllMeasures['G2']=None
                        AllMeasures['Vrect2'] = None
                        AllMeasures['inverterV2']=None
                        if self.Json_TC['load_names'][0] in self.timing_map[2]['Loads']:
                            if self.timing_map[2]['Loads'][self.Json_TC['load_names'][0]] is not None:
                                #get the time of load applied + 5 sec
                                load2time = self.file_list[self.timing_map[2]['Loads'][self.Json_TC['load_names'][0]]].get('startTime')+(self.Json_TC['App_Measures'][str(idx)]['G2']['mdelay']/1000)
                                #after the above time check for the XCE packet and meaure Vrect2
                                id = self.timing_map[2]['Loads'][self.Json_TC['load_names'][0]]
                                index = None
                                while id < len(self.file_list):
                                    #filter only XCE packets
                                    if self.file_list[id].get('pktType') == 'Extended Control Error' and self.file_list[id].get('value') in ['-1','0','+1']:
                                        #check that the time meaured is grater than the XCE pacekt revd time
                                        if self.file_list[id].get('startTime') > load2time:
                                            index = id
                                            break
                                    id+=1
                                if index is not None:
                                    #calculate Vrect2 time 
                                    res = self.CalculateVoltTwindow(index,self.AllChannelData)
                                    Vrect2 = res[0]
                                #Get inverterV2
                                inverterV2 = None
                                id = index
                                while id < len(self.file_list):
                                    if 'Inverter_Voltage' in self.file_list[id].get('pktType'):
                                        inverterV2 = float(self.file_list[id]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'].split(' ')[1].split('V')[0])
                                        break
                                    id+=1
                                #cal G2
                                if Vrect2 is not None and inverterV2 is not None: 
                                    G2 = Vrect2/inverterV2
                                    AllMeasures['Vrect2'] = Vrect2
                                    AllMeasures['inverterV2'] = inverterV2
                                    AllMeasures['G2'] = round(G2,2)
                    if apmes in['VinverterDelta']:
                        AllMeasures['VinverterDelta']=None
                        if AllMeasures['inverterV1'] is not None and AllMeasures['inverterV2'] is not None:
                            AllMeasures['VinverterDelta'] = round(abs(AllMeasures['inverterV2']-AllMeasures['inverterV1']),2)
                    if apmes in ['PreceivedMin']:
                        AllMeasures['PreceivedMin']=None
                        AllMeasures['PreceivedMax'] =None
                        #get value from RP
                        loadindex = None
                        RPvalues = []
                        if self.Json_TC['load_names'][1] in self.timing_map[2]['Loads']:
                            startload = self.timing_map[2]['Loads'][self.Json_TC['load_names'][1]] if self.timing_map[2]['Loads'][self.Json_TC['load_names'][1]]!='Fail' else None
                        if len(self.timing_map[2]['Loads'])>0:
                            for Loads in self.timing_map[2]['Loads']:
                                if self.timing_map[2]['Loads'][Loads] =='Fail':
                                    break
                                else: loadindex = self.timing_map[2]['Loads'][Loads]
                        if loadindex is not None and startload is not None:
                            maxtime = self.file_list[loadindex].get('stopTime')+120
                            id = startload
                            # print(len(file_list))
                            while id < len(self.file_list):
                                if self.Json_TC['RP'] in self.file_list[id].get('pktType') :
                                    if (self.file_list[id].get('startTime')) >= maxtime:
                                        break
                                    else: 
                                        RPvalues.append(float(self.file_list[id].get('value').split('{')[1].split('w')[0]))
                                id+=1
                            if len(RPvalues)>0:
                                AllMeasures['PreceivedMin'] =min(RPvalues)
                                AllMeasures['PreceivedMax'] =max(RPvalues)
                    if apmes in ['Prect_target']:
                        AllMeasures['Prect_target']=None
                        AllMeasures['Vrect_target'] =None
                        AllMeasures['Irect_target'] =None
                        if 'RP_avgPower' in self.Json_TC['App_Measures'][str(idx)]:  AllMeasures['RP_avgPower'] = None
                        stable2 = None
                        loadindex = self.timing_map[2]['Loads'][self.Json_TC['load_names'][1]] if self.timing_map[2]['Loads'][self.Json_TC['load_names'][1]]!='Fail' else None
                        id = loadindex
                        if id is not None:
                            while id < len(self.file_list):
                                if 'MPP_XCE_Stabilized' in self.file_list[id].get('pktType'):
                                    revid = id
                                    while revid > loadindex:
                                        if  self.file_list[revid].get('pktType') in ['Extended Control Error','Control Error']:
                                            stable2=revid
                                            break
                                        revid-=1
                                    break
                                id+=1
                        if stable2 is not None:
                            res = self.CalculateVoltTwindow(stable2,self.AllChannelData)
                            AllMeasures['Vrect_target'] = res[0]
                            #Get I rect 
                            Pplot = self.AllChannelData3
                            AllMeasures['Irect_target'] = round(abs(Pplot['RV']['displayDataChunk'][res[1]]),2)
                            Prect =  AllMeasures['Irect_target'] * AllMeasures['Vrect_target']
                            AllMeasures['Prect_target'] = round(Prect,2)
                            if 'RP_avgPower' in self.Json_TC['App_Measures'][str(idx)]:
                                maxtime = float(self.file_list[stable2].get('startTime')) + 2
                                id = stable2
                                power = 0
                                cnt = 0
                                while id < len(self.file_list):
                                    if float(self.file_list[id].get('startTime')) > maxtime: break
                                    if 'Received Power' in self.file_list[id].get('pktType'):
                                        cnt+=1
                                        power = power+float(self.file_list[id]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'].split('w')[0].replace('{',''))
                                    id+=1
                                AllMeasures['RP_avgPower']  = power/cnt if 0 not in [cnt,power] else None
                    if apmes in ['Vrect_target1']:
                        #calculate based on the loads len
                        if len(self.Json_TC['load_names']) > 0:
                            lid = 0
                            while lid < len(self.Json_TC['load_names'])-1:
                                if lid == 0:
                                    #Calculate Vrect_target1,Irect_target1,Prect_target1
                                    if self.stability:
                                        res = self.CalculateVoltTwindow(self.stability,self.AllChannelData)
                                        AllMeasures['Vrect_target1'] =  res[0]
                                        Pplot = self.AllChannelData3
                                        AllMeasures['Irect_target1']= round(abs(Pplot['RV']['displayDataChunk'][res[1]]),2)
                                        AllMeasures['Prect_target1'] = round(AllMeasures['Irect_target1'] * AllMeasures['Vrect_target1'],2)
                                else:
                                    loadindex = self.timing_map[2]['Loads'][self.Json_TC['load_names'][lid]] if self.Json_TC['load_names'][lid] in self.timing_map[2]['Loads'] else None
                                    if loadindex is not None:
                                            stable =None
                                            id = loadindex
                                            while id < len(self.file_list):
                                                if 'MPP_XCE_Stabilized' in self.file_list[id].get('pktType'):
                                                    revid = id
                                                    while revid > loadindex:
                                                        if  self.file_list[revid].get('pktType') in ['Extended Control Error','Control Error']:
                                                            stable=revid
                                                            break
                                                        revid-=1
                                                    break
                                                id+=1
                                            if stable is not None:
                                                res = self.CalculateVoltTwindow(stable,self.AllChannelData)
                                                AllMeasures['Vrect_target'+str(lid+1)] = res[0]
                                                #Get I rect 
                                                Pplot = self.AllChannelData3
                                                AllMeasures['Irect_target'+str(lid+1)] = round(abs(Pplot['RV']['displayDataChunk'][res[1]]),2)
                                                AllMeasures['Prect_target'+str(lid+1)] = round(AllMeasures['Irect_target'+str(lid+1)] * AllMeasures['Vrect_target'+str(lid+1)],2)
                                    else:
                                        AllMeasures['Vrect_target'+str(lid+1)]=None
                                        AllMeasures['Irect_target'+str(lid+1)] =None
                                        AllMeasures['Prect_target'+str(lid+1)] =None
                                AllMeasures['Vrect_final'] = AllMeasures['Vrect_target'+str(lid+1)]
                                AllMeasures['Irect_final']= AllMeasures['Irect_target'+str(lid+1)]
                                AllMeasures['Prect_final'] = AllMeasures['Prect_target'+str(lid+1)]
                                lid+=1
                    if apmes in ['Ttimeout']:
                        AllMeasures['Ttimeout']=None
                        id =0
                        starttime = None
                        endtime = None
                        while id < len(self.file_list):
                            if self.Json_TC['App_Measures'][str(idx)]['Ttimeout']['packet'] in self.file_list[id].get('pktType'):
                                revid = id
                                while revid > 0:
                                    if 'Extended Control Error' in self.file_list[revid].get('pktType'):
                                        starttime = self.file_list[id].get('stopTime')
                                        #get shutdown starttime
                                        shid = revid
                                        while shid < len(self.file_list):
                                            if  self.file_list[shid].get('pktType') in ['Shutdown','Test_Stop']:
                                                endtime =  self.file_list[shid].get('startTime')
                                                break
                                            shid+=1
                                        break
                                    revid -=1
                                break
                            id+=1
                        # print(starttime,endtime)
                        AllMeasures['Ttimeout'] = round((endtime*1000)-(starttime*1000),2) if endtime is not None or starttime is not None else None
                    if apmes in ['tterminate']:
                        # print(self.Json_TC['other_checks_details'][str(idx)],idx)
                        if 'ILPKT' not in self.Json_TC['other_checks_details'][str(idx)]:
                            # print(self.Json_TC['App_Measures'][str(idx)]['tterminate'])
                            if self.Json_TC['App_Measures'][str(idx)]['tterminate']['packet'] =='IP':
                                if len(self.timing_map['Illegal'])>0:
                                    #Get EPT end value
                                    Pkttime = (self.timing_map['Illegal'][len(self.timing_map['Illegal'])]['end']*1000)-Plotstarttime
                                else:
                                    return {'tterminate':0}
                                if Pkttime != 0:
                                    index = int((Pkttime)/self.AllChannelData['Interval'])
                                    id = index
                                    #measure after eg. 19ms, if mentioned
                                    if self.Json_TC['App_Measures'][str(idx)]['tterminate']['mdelay'] != 0:
                                        addindex = round(19/self.AllChannelData['Interval'])+1
                                        id = index+addindex
                                    while id<self.AllChannelData['records']:
                                        if abs(self.AllChannelData['RV']['displayDataChunk'][id]*1000) < self.Json_TC['App_Measures'][str(idx)]['tterminate']['volt']:
                                            break
                                        id+=1
                                    tterminate = ((id-index)) * self.AllChannelData['Interval']
                                    return {'tterminate':round(tterminate,2)}
                            if self.Json_TC['App_Measures'][str(idx)]['tterminate']['packet'] =='EPT':
                                if 'EPT' in self.timing_map[idx]['PT']:
                                    #Get EPT end value
                                    Pkttime = (self.timing_map[idx]['PT']['EPT'][0][0][2]*1000)-Plotstarttime
                                else:
                                    AllMeasures['tterminate'] = 0
                                if Pkttime != 0:
                                    index = int((Pkttime)/self.AllChannelData['Interval'])
                                    id = index
                                    #measure after eg. 19ms, if mentioned
                                    if self.Json_TC['App_Measures'][str(idx)]['tterminate']['mdelay'] != 0:
                                        addindex = round(19/self.AllChannelData['Interval'])+1
                                        id = index+addindex
                                    while id<self.AllChannelData['records']:
                                        if abs(self.AllChannelData['RV']['displayDataChunk'][id]*1000) < self.Json_TC['App_Measures'][str(idx)]['tterminate']['volt']:
                                            break
                                        id+=1
                                    tterminate = ((id-index)) * self.AllChannelData['Interval']
                                    AllMeasures['tterminate'] = round(tterminate,2)
                            if self.Json_TC['App_Measures'][str(idx)]['tterminate']['packet'] =='Report':
                                Reppkt = self.GetPacketDetails(packet='Report',limit=[len(self.file_list)-1,0])
                                if len(Reppkt)>1:
                                    sindex =None
                                    sd= self.GetPacketDetails(packet='Shutdown',limit=[Reppkt[2],len(self.file_list)-1])
                                    if len(sd)>1:
                                        sindex = sd[2]
                                    else:
                                        TS = self.GetPacketDetails(packet='Test_Stop',limit=[Reppkt[2],len(self.file_list)-1])
                                        if len(TS)>1:
                                            sindex = TS[2]
                                        else:
                                            sindex =len(self.file_list)-1
                                    if sindex is not None:
                                        AllMeasures['tterminate'] = round(((self.file_list[sindex]['stopTime']-self.file_list[Reppkt[2]]['stopTime'])*1000),2)
                        else:
                            AllMeasures['tterminate'] = None
                            packets = self.Json_TC['other_checks_details'][str(idx)]['ILPKT'][0]
                            etime=stime = 0
                            if len(self.timing_map[idx]['Illegal'])>0:
                                for pk in self.timing_map[idx]['Illegal']:
                                    # ippkt = self.timing_map[idx]['Illegal'][pk]
                                    if packets['packet'][0] in pk[0][1] if packets['packet'][1] is None else packets['packet'][0] in pk[0][1] and packets['packet'][1] in pk[0][2]:
                                        etime = pk[0][4]
                                        if len(self.timing_map[idx]['General'])> 0:
                                            if self.timing_map[idx]['General']['SD'][2] > pk[0][0]:
                                                stime = self.timing_map[idx]['General']['SD'][2]
                                            else:
                                                # find SD
                                                sd= self.GetPacketDetails(packet='Shutdown',limit=[pk[0][0],len(self.file_list)-1])
                                                if len(sd)>1:
                                                    stime = self.file_list[sd[2]]['stopTime']
                                                else:
                                                    TS = self.GetPacketDetails(packet='Test_Stop',limit=[pk[0][0],len(self.file_list)-1])
                                                    if len(TS)>1:
                                                        stime = self.file_list[TS[2]]['stopTime']
                                                    else:
                                                        stime = self.file_list[len(self.file_list)-1]['stopTime']

                                            # print('stime',stime)
                                        break
                            if etime != 0 and stime != 0: AllMeasures['tterminate']=round((stime-etime)*1000,3)
                    if apmes in ['treping']:
                        #calculate time interval btween f1 and f2
                        endtime = starttime = None
                        if 'General' in self.timing_map[1]:
                            if 'SD' in self.timing_map[1]['General']: endtime = self.timing_map[1]['General']['SD'][2]*1000
                        if 'General' in self.timing_map[2]:
                            if 'PD' in self.timing_map[2]['General'] : starttime = self.timing_map[2]['General']['PD'][1]*1000
                        AllMeasures['treping'] =round((starttime-endtime),2) if None not in [endtime,starttime] else None
                    if apmes in ['tnopower']:
                        tnopower = None
                        if 'General' in self.timing_map[1]:
                            if 'PD' in self.timing_map[1]['General']:
                                id = self.timing_map[1]['General']['PD'][0]
                                while id > 0:
                                    if self.file_list[id].get('pktType') == 'Shutdown':
                                        tnopower = round((self.timing_map[1]['General']['PD'][1]*1000) - (self.file_list[id].get('stopTime')*1000),2)
                                        break
                                    id-=1
                        AllMeasures['tnopower'] = tnopower if tnopower is not None else None
                    if apmes in ['UroXCE']:
                        packet = self.Json_TC['App_Measures'][str(idx)]['UroXCE']['packet']
                        limit = [self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]]
                        Uro = []
                        #loop and get all matching packets get the timimgs
                        id = limit[0]
                        while id < limit[1]:
                            if packet[0] in self.file_list[id].get('pktType') and packet[1] in self.file_list[id].get('value') if packet[1]!=None else packet[0] in self.file_list[id].get('pktType'):
                                if self.Json_TC['App_Measures'][str(idx)]['UroXCE']['Uro1pos'] !=0:
                                    #consider upcoming packet
                                    tid = id+1
                                    while tid < limit[1]:
                                        if self.file_list[tid]['isTesterPkt'] == True and self.file_list[tid]['isFWTestermessage'] ==False:
                                            break
                                        tid+=1
                                else:
                                    tid=id
                                Uro1Time = ((self.file_list[tid].get('startTime')*1000) - self.Json_TC['App_Measures'][str(idx)]['UroXCE']['Uro1'])-Plotstarttime
                                Uro1TIndex = int(Uro1Time/self.AllChannelData['Interval'])
                                Uro1 = round(abs(self.AllChannelData['RV']['displayDataChunk'][Uro1TIndex]),4)
                                Uro2Time = (self.file_list[id].get('stopTime')*1000) + self.Json_TC['App_Measures'][str(idx)]['UroXCE']['Uro2']-Plotstarttime
                                Uro2TIndex = int(Uro2Time/self.AllChannelData['Interval'])
                                Uro2 = round(abs(self.AllChannelData['RV']['displayDataChunk'][Uro2TIndex]),4)
                                Uro.append(abs(round((Uro1-Uro2),3)))
                            id+=1
                        AllMeasures['UroXCE']=Uro    
                    if apmes in ['UroPLA']:
                        packet = self.Json_TC['App_Measures'][str(idx)]['UroPLA']['packet']
                        limit = [self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]]
                        Uro = []
                        #loop and get all matching packets get the timimgs
                        id = limit[0]
                        while id < limit[1]:
                            if packet[0] in self.file_list[id].get('pktType') and packet[1] in self.file_list[id].get('value') if packet[1]!=None else packet[0] in self.file_list[id].get('pktType'):
                                Uro1Time = ((self.file_list[id+(self.Json_TC['App_Measures'][str(idx)]['UroPLA']['Uro1pos'])].get('startTime')*1000) + self.Json_TC['App_Measures'][str(idx)]['UroPLA']['Uro1'])-Plotstarttime
                                Uro1TIndex = int(Uro1Time/self.AllChannelData['Interval'])
                                Uro1 = round(abs(self.AllChannelData['RV']['displayDataChunk'][Uro1TIndex]),4)
                                Uro2Time = ((self.file_list[id+1].get('stopTime')*1000) + self.Json_TC['App_Measures'][str(idx)]['UroPLA']['Uro2'])-Plotstarttime
                                Uro2TIndex = int(Uro2Time/self.AllChannelData['Interval'])
                                Uro2 = round(abs(self.AllChannelData['RV']['displayDataChunk'][Uro2TIndex]),4)
                                Uro.append(abs(round((Uro1-Uro2),3)))
                            id+=1
                        AllMeasures['UroPLA']=Uro    
                    if apmes in ['Txce_timeout']:
                        AllMeasures['Txce_timeout']=None
                        limit=[self.timing_map[idx]['General']['SD'][0],self.timing_map[idx]['General']['PD'][0]]
                        id =  limit[0]
                        while id > limit[1]:
                            if self.file_list[id].get('pktType') == 'Extended Control Error':
                                AllMeasures['Txce_timeout']= round((self.file_list[limit[0]].get('stopTime') - self.file_list[id].get('startTime'))*1000,2)
                                break
                            id-=1
                    if apmes in ['Txce_timeoutClk','Tpla_timeoutClk']:
                        AllMeasures[apmes]=None
                        if len(self.timing_map[idx]['Cloak'])>0:
                            sindex =None
                            lmt=[self.timing_map[idx]['Cloak'][len(self.timing_map[idx]['Cloak'])][0][0],len(self.file_list)-1]
                            xid = self.GetPacketDetails(packet='Get Request',value='Extended Identification',limit=lmt)
                            if len(xid)>1:
                                # find SD
                                sd= self.GetPacketDetails(packet='Shutdown',limit=[xid[2],len(self.file_list)-1])
                                if len(sd)>1:
                                    sindex = sd[2]
                                else:
                                    TS = self.GetPacketDetails(packet='Test_Stop',limit=[xid[2],len(self.file_list)-1])
                                    if len(TS)>1:
                                        sindex = TS[2]
                                    else:
                                        sindex =len(self.file_list)-1
                                if sindex is not None:
                                    AllMeasures[apmes]= round((self.file_list[sindex].get('stopTime') - self.file_list[xid[2]].get('startTime'))*1000,2)
                    if apmes in ['Tpla_timeout']:
                        AllMeasures['Tpla_timeout']=None
                        limit=[self.timing_map[idx]['General']['SD'][0],self.timing_map[idx]['General']['PD'][0]]
                        id =  limit[0]
                        while id > limit[1]:
                            if self.file_list[id].get('pktType') == 'Power Loss Accounting':
                                AllMeasures['Tpla_timeout']= round((self.file_list[limit[0]].get('stopTime') - self.file_list[id].get('startTime'))*1000,2)
                                break
                            id-=1
                    if apmes in ['CPLCheck']:
                        self.CPLmeasure(str(idx),AllMeasures)
                    if apmes in ['TcloakTimeout']:
                        AllMeasures['TcloakTimeout']=None
                        #find last cloak pkts SF pD to SD
                        lastclkpkt = self.timing_map[idx]['Cloak'][len(self.timing_map[idx]['Cloak'])][0][0]
                        if len(self.timing_map[idx]['Cloak'])>0:
                            PD = self.GetPacketDetails(packet='Ping Initiated',limit=[lastclkpkt,len(self.file_list)-1])
                            if len(PD)>1:
                                stopindex = None
                                # find SD
                                sd= self.GetPacketDetails(packet='Shutdown',limit=[PD[2],len(self.file_list)-1])
                                if len(sd)>1:
                                    stopindex = sd[2]
                                else:
                                    TS = self.GetPacketDetails(packet='Test_Stop',limit=[PD[2],len(self.file_list)-1])
                                    if len(TS)>1:
                                        stopindex = TS[2]
                                    else:
                                        stopindex =len(self.file_list)-1
                                AllMeasures['TcloakTimeout'] = round(((self.file_list[stopindex]['stopTime']-self.file_list[PD[2]]['stopTime'])*1000),2)
                    if apmes in ['Tcloak'] and 'CPLCheck' not in self.Json_TC['App_Measures'][str(idx)]:
                        #check for Tclock for all clk seq, Clk ack end to end clk PD start
                        AllMeasures['Tcloak'] =None
                        clkpkts = []
                        if len(self.timing_map[idx]['Cloak'])>0:
                            for clkpkt in self.timing_map[idx]['Cloak']:
                                clkpkts.append([self.timing_map[idx]['Cloak'][clkpkt][0][0],self.timing_map[idx]['Cloak'][clkpkt][1][0]])
                        if len(clkpkts)>0:
                            AllMeasures['Tcloak']=[]
                            id = 0
                            while id < len(clkpkts)-2:
                                #find PD before next clk
                                PD = self.GetPacketDetails(packet='Ping Initiated',limit=[clkpkts[id+1][0],clkpkts[id][0]])
                                if len(PD)>1:
                                    AllMeasures['Tcloak'].append(round((self.file_list[PD[2]]['startTime'] - self.file_list[clkpkts[id][1]]['stopTime'])*1000,2))
                                id+=1
                    if apmes in ['Tcloakdetect']:
                        #find PD-PD for all clk seq inbtwn 
                        AllMeasures['Tcloakdetect'] =None
                        if len(self.timing_map[idx]['Cloak'])>0:
                            for clkpkt in self.timing_map[idx]['Cloak']:
                                clkpkts.append([self.timing_map[idx]['Cloak'][clkpkt][0][0],self.timing_map[idx]['Cloak'][clkpkt][1][0]])
                        if len(clkpkts)>0:
                            AllMeasures['Tcloakdetect']=[]
                            id = 0
                            while id < len(clkpkts)-1:
                                #find PD-PD btween 2 clk
                                clklimit = [clkpkts[id][0],clkpkts[id+1][0]]
                                clkid = clklimit[0]
                                while clkid < clklimit[1]:
                                    PD1 = self.GetPacketDetails(packet='Ping Initiated',limit=[clkid,clklimit[1]])
                                    if len(PD1)>1:
                                        PD2 = self.GetPacketDetails(packet='Ping Initiated',limit=[PD1[2]+1,clklimit[1]])
                                        if len(PD2)>1:
                                            AllMeasures['Tcloakdetect'].append(round((self.file_list[PD2[2]]['startTime'] - self.file_list[PD1[2]]['stopTime'])*1000,2))
                                            clkid=PD2[2]+1
                                        else:clkid=PD1[2]+1
                                    else:break
                                id+=1
                    if apmes in ['Tdactive']:
                        AllMeasures['Tdactive'] =None
                        #find PD-PD for all clk seq inbtwn 
                        AllMeasures['Tdactive'] =None
                        if len(self.timing_map[idx]['Cloak'])>0:
                            for clkpkt in self.timing_map[idx]['Cloak']:
                                clkpkts.append([self.timing_map[idx]['Cloak'][clkpkt][0][0],self.timing_map[idx]['Cloak'][clkpkt][1][0]])
                        if len(clkpkts)>0:
                            AllMeasures['Tdactive']=[]
                            id = 0
                            while id < len(clkpkts)-1:
                                PDbfClk = self.GetPacketDetails(packet='Ping Initiated',limit=[clkpkts[id+1][0],clkpkts[id][0]])
                                if len(PDbfClk)>1:
                                    clklimit = [clkpkts[id][0],PDbfClk[2]-1]
                                    clkid = clklimit[0]
                                    while clkid < clklimit[1]:
                                        stopindex=None
                                        PD = self.GetPacketDetails(packet='Ping Initiated',limit=[clkid,clklimit[1]])
                                        if len(PD)>1:
                                            # find SD
                                            sd= self.GetPacketDetails(packet='Shutdown',limit=[PD[2],clklimit[1]])
                                            if len(sd)>1:
                                                stopindex = sd[2]
                                            else:
                                                TS = self.GetPacketDetails(packet='Test_Stop',limit=[PD[2],clklimit[1]])
                                                if len(TS)>1:
                                                    stopindex = TS[2]
                                                else:
                                                    stopindex =clklimit[1]
                                            if stopindex is not None:
                                                AllMeasures['Tdactive'].append(round((self.file_list[stopindex]['startTime'] - self.file_list[PD[2]]['stopTime'])*1000,2))
                                                clkid=stopindex
                                            else:PD[2]+1
                                        else:break
                                else:break
                                id+=1
                    if apmes in ['Clk_Detach']:
                        #SD to next coil remove pkt
                        AllMeasures['Clk_Detach'] =None
                        if 'Clk_Reattach' in self.Json_TC['App_Measures'][str(idx)]: AllMeasures['Clk_Reattach'] =None
                        if 'Tdetect' in self.Json_TC['App_Measures'][str(idx)]: AllMeasures['Tdetect'] =None
                        CoilRM = self.GetPacketDetails(packet='Coil_Remove_From_Base_Station',limit=[self.timing_map[idx]['General']['SD'][0],len(self.file_list)-1])
                        if len(CoilRM)>1:
                            AllMeasures['Clk_Detach']=(round((self.file_list[CoilRM[2]]['startTime'] - self.file_list[self.timing_map[idx]['General']['SD'][0]]['stopTime'])*1000,2))
                            if 'Clk_Reattach' in self.Json_TC['App_Measures'][str(idx)]:
                                CoilPL = self.GetPacketDetails(packet='Coil_Place_On_Base_Station',limit=[CoilRM[2],len(self.file_list)-1])
                                if len(CoilPL)>1:
                                   AllMeasures['Clk_Reattach']=(round((self.file_list[CoilPL[2]]['startTime'] - self.file_list[CoilRM[2]]['stopTime'])*1000,2))
                                   if 'Tdetect' in self.Json_TC['App_Measures'][str(idx)]:
                                        TmpPD = self.GetPacketDetails(packet='Ping Initiated',limit=[CoilPL[2],len(self.file_list)-1])
                                        if len(TmpPD)>1:
                                            AllMeasures['Tdetect']=(round((self.file_list[TmpPD[2]]['startTime'] - self.file_list[CoilPL[2]]['stopTime'])*1000,2))
                    if apmes in ['T_atn']:
                        AllMeasures['T_atn'] =None
                        limit = [self.timing_map[idx]['General']['SD'][0],len(self.file_list)-1]
                        Exid = self.GetPacketDetails(packet='Get Request',value='Extended Identification',limit=limit)
                        if len(Exid)>1:
                            DSR = self.GetPacketDetails(packet='DSR',limit=[Exid[2],limit[1]])
                            if len(DSR)>1:
                                print(Exid,DSR)
                                AllMeasures['T_atn'] = round((DSR[0]-Exid[1])*1000,2)
                    #TPT
                    if apmes in ['P1']:
                        AllMeasures['P1'] =None
                        #Get PLA after stable 
                        if self.stability is not None:
                            PLApkt = self.GetPacketDetails("Power Loss Accounting",limit=[self.stability,len(self.file_list)-1])
                            if len(PLApkt)>1:
                               #Calculate Power from plot - Since the Rectified channels are not available in the plot have to find the alternative options.
                            #    res = self.CalculateVoltTwindow(PLApkt[2],self.AllChannelData,winsize=[19,21])
                            #    Volt=res[0]
                            #    Curnt = round(abs(self.AllChannelData3['RV']['displayDataChunk'][res[1]]),2)
                            #    AllMeasures['P1'] = round((Volt*Curnt),2)
                               #Get Power from pkt
                               res= GeneralMethods.GetFloatFromStr(self.file_list[PLApkt[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])
                               AllMeasures['P1'] = res[0]
                    if apmes in ['P2']:
                        #calculate P2 on PLA, after 200ms from P1.
                        AllMeasures['P2'] =None
                        if self.stability is not None:
                            PLApkt1 = self.GetPacketDetails("Power Loss Accounting",limit=[self.stability,len(self.file_list)-1])
                            if len(PLApkt1)>1:
                                PLApkt2 = self.GetPacketDetails("Power Loss Accounting",limit=[PLApkt1[2],len(self.file_list)-1],timelimit=PLApkt1[1]+2)
                                print('PLA2',PLApkt2)
                                if len(PLApkt2)>1:
                                    res= GeneralMethods.GetFloatFromStr(self.file_list[PLApkt2[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])
                                    AllMeasures['P2'] = res[0]
                    if apmes in ['Prect2']:
                        AllMeasures['Prect2'] =None
                        if  self.stability is not None:
                            stable2 = self.GetPacketDetails("MPP_XCE_Stabilized Range",limit=[self.stability+20,len(self.file_list)-1])
                            if len(stable2)>1:
                                #get PLA pkt
                                PLApkt2 = self.GetPacketDetails("Power Loss Accounting",limit=[stable2[2],len(self.file_list)-1])
                                if len(PLApkt2)>1:
                                    res= GeneralMethods.GetFloatFromStr(self.file_list[PLApkt2[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])
                                    print(res)
                                    AllMeasures['Prect2'] = res[0]
                    if apmes in ['V1']:
                        AllMeasures['V1'] =None
                        #Get PLA after stable 
                        if self.stability is not None:
                            PLApkt = self.GetPacketDetails("Power Loss Accounting",limit=[self.stability,len(self.file_list)-1])
                            if len(PLApkt)>1:
                                res = self.CalculateVoltTwindow(PLApkt[2],self.AllChannelData,winsize=[19,21])
                                AllMeasures['V1']=res[0]
                    if apmes in ['V2']:
                        AllMeasures['V2'] =None
                        PLApkt1 = self.GetPacketDetails("Power Loss Accounting",limit=[self.stability,len(self.file_list)-1])
                        if len(PLApkt1)>1:
                            PLApkt2 = self.GetPacketDetails("Power Loss Accounting",limit=[self.stability,len(self.file_list)-1],timelimit=PLApkt1[1]+2)
                            if len(PLApkt2)>1:
                                res = self.CalculateVoltTwindow(PLApkt2[2],self.AllChannelData,winsize=[19,21])
                                AllMeasures['V2']=res[0]
                    if apmes in ['181Check']:
                        AllMeasures['181Check'] =None
                        if all(rs in AllMeasures for rs in ['P1','P2','V1','V2']):
                            AllMeasures['181Check'] = round((AllMeasures['P1']*AllMeasures['V2'])/AllMeasures['V1'],2)
                    if apmes in ['183Check']:
                        AllMeasures[apmes] =None
                        print(AllMeasures)
                        if all(rs in AllMeasures for rs in ['P1','Prect2']):
                            AllMeasures['183Check'] = round((AllMeasures['P1']*1.1),2)
                    if apmes in ['ITPT_MAX']:
                        AllMeasures[apmes] =None
                        #Find a max current from start of nego to stable
                        if self.stability is not None:
                            res = self.CalculateVoltTimePeriod(self.AllChannelData3,self.file_list[self.timing_map[idx]['Nego']['GRQexid'][0][0][0]]['startTime'],self.file_list[self.stability]['startTime'])
                            AllMeasures[apmes] =res[0]
                    if apmes in ['PDelta']:
                        AllMeasures[apmes] =None
                        #Get Pla pkt value after stabilize
                        if self.stability is not None:
                            PLApkt = self.GetPacketDetails("Power Loss Accounting",limit=[self.stability,len(self.file_list)-1])
                            if len(PLApkt)>1:
                                res= GeneralMethods.GetFloatFromStr(self.file_list[PLApkt[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])
                                PLAval = res[0]
                                #Get Nego power value from cap
                                Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]])
                                if len(Excap)>1:
                                    powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                                    AllMeasures[apmes] = round(abs(PLAval-powval[0]),2)

                    #apply Validations
                    exp = self.Json_TC['App_Measures'][str(idx)][apmes]['expected']
                    if type(exp) != str:
                        if type(AllMeasures[apmes]) !=list:
                            # AllMeasures[str(apmes)+'_exp'] = self.Json_TC['App_Measures'][str(idx)][apmes]['expected']
                            AllMeasures[str(apmes)+'_res'] = 'Fail'
                            if AllMeasures[apmes] is not None:
                                reslt = self.check_measure(exp, AllMeasures[apmes],self.Json_TC['App_Measures'][str(idx)][apmes]['comp'])
                                AllMeasures[str(apmes)+'_exp']=reslt[2]+str(reslt[0][0]) if reslt[2] != 0 else str(reslt[0][0])+'-'+str(reslt[0][1])
                                AllMeasures[str(apmes)+'_res'] = reslt[1]
                            else:
                                AllMeasures[str(apmes)+'_exp'] = str(exp[0])+'-'+str(exp[1]) if len(exp)>1 else exp[0]
                        else:
                            resultli = []
                            for res in AllMeasures[apmes]:
                                reslt = self.check_measure(exp, res,self.Json_TC['App_Measures'][str(idx)][apmes]['comp'])
                                resultli.append(reslt[1])
                            AllMeasures[str(apmes)+'_exp']=reslt[2]+str(reslt[0][0]) if reslt[2] != 0 else str(reslt[0][0])+'-'+str(reslt[0][1])
                            AllMeasures[apmes] = ','.join(map(str,AllMeasures[apmes]))
                            AllMeasures[str(apmes)+'_res'] = 'Fail' if 'Fail' in resultli else 'Pass'
                    else:
                        if apmes in ['VrecrfinalComp'] and exp=='TC1':
                            AllMeasures['VrecrfinalComp_exp'] ="VrectF0<VrectF1<VrectF2"
                            AllMeasures['VrecrfinalComp_res']='Fail'
                            if None not in [AllMeasures['Vrectfinal0'],AllMeasures['Vrectfinal1'],AllMeasures['Vrectfinal2']]:
                                if AllMeasures['Vrectfinal0'] < AllMeasures['Vrectfinal1'] and AllMeasures['Vrectfinal1'] < AllMeasures['Vrectfinal2']:
                                    AllMeasures['VrecrfinalComp_res'] = 'Pass'
                        elif apmes in ['VrecrfinalComp'] and exp=='TC2':
                            AllMeasures['VrecrfinalComp_exp'] ="VrectF0>VrectF1>VrectF2"
                            AllMeasures['VrecrfinalComp_res']='Fail'
                            if None not in [AllMeasures['Vrectfinal0'],AllMeasures['Vrectfinal1'],AllMeasures['Vrectfinal2']]:
                                if AllMeasures['Vrectfinal0'] > AllMeasures['Vrectfinal1'] and AllMeasures['Vrectfinal1'] > AllMeasures['Vrectfinal2']:
                                    AllMeasures['VrecrfinalComp_res'] = 'Pass'
                        elif apmes in ['CPLCheck'] and exp =='DPL+/-5%':
                            expval = [((AllMeasures['DPL']*95)/100),((AllMeasures['DPL']*105)/100)]
                            values = AllMeasures['CPLCheck']
                            AllMeasures['CPLCheck_exp'] = f"DPL:{AllMeasures['DPL']} Limit:{expval[0]}-{expval[1]}"
                            AllMeasures['CPLCheck_res']='Fail'
                            AllMeasures['CPLCheck']=','.join(map(str,values))
                            if all(rs >= expval[0] and rs <= expval[1] for rs in values): AllMeasures['CPLCheck_res']='Pass'
                        elif apmes in ['Prect'] and exp in ['Nego%','Potential%']:
                            AllMeasures[apmes+'_res'] ='Fail'
                            #Get Nego power value from cap
                            Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]])
                            if len(Excap)>1:
                                if exp == 'Nego%':
                                    powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                                elif exp == 'Potential%':
                                    powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])
                                expper = self.Json_TC['App_Measures'][str(idx)][apmes]['percentage']
                                if len(powval)>0:
                                    expval = ((powval[0])/100)*expper
                                    PowerValue_exp = [expval-((expval*5)/100),expval+((expval*5)/100)]
                                    AllMeasures[apmes+'_exp'] = '-'.join(map(str,PowerValue_exp))
                                    if AllMeasures[apmes] >= PowerValue_exp[0] and AllMeasures[apmes] <= PowerValue_exp[1]:AllMeasures[apmes+'_res'] ='Pass'
                        elif apmes in ['Vrect'] and exp in ['Nego%','Potential%']:
                            AllMeasures[apmes+'_res'] ='Fail'
                            #Get Nego power value from cap
                            Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]])
                            if len(Excap)>1:
                                if exp == 'Nego%':
                                    powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                                elif exp == 'Potential%':
                                    powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])
                                expper = self.Json_TC['App_Measures'][str(idx)]['Prect']['percentage']
                                if len(powval)>0:
                                    expval = ((powval[0])/100)*expper
                                    PowerValue_exp = [11.859,12.140] if expval <= 5 else [13.835,14.164]
                                    AllMeasures[apmes+'_exp'] = '-'.join(map(str,PowerValue_exp))
                                    if AllMeasures[apmes] >= PowerValue_exp[0] and AllMeasures[apmes] <= PowerValue_exp[1]:AllMeasures[apmes+'_res'] ='Pass'
                        #TPT
                        elif apmes in ['P1','P2'] and exp in ['NegoLimit']:
                            #Get Nego power value from cap
                            Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]])
                            if len(Excap)>1:
                                powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                                expper = self.Json_TC['App_Measures'][str(idx)][apmes]['percentage']
                                if len(powval)>0:
                                    expval = ((powval[0])/100)*expper
                                    PowerValue_exp = [powval[0]-expval,powval[0]+expval]
                                    AllMeasures[apmes+'_exp'] = '-'.join(map(str,PowerValue_exp))
                                    AllMeasures[apmes+'_res'] ='Pass' if AllMeasures[apmes] >= PowerValue_exp[0] and AllMeasures[apmes] <= PowerValue_exp[1] else 'Fail'
                        elif apmes in ['181Check']:
                            AllMeasures[apmes+'_exp'] = self.Json_TC['App_Measures'][str(idx)][apmes]['expected']
                            AllMeasures[apmes+'_res'] = 'Pass' if AllMeasures['P2'] <= AllMeasures[apmes] else 'Fail'
                        elif apmes in ['183Check']:
                            print(AllMeasures)
                            AllMeasures[apmes+'_exp'] = self.Json_TC['App_Measures'][str(idx)][apmes]['expected']
                            if AllMeasures['Prect2'] is not None:
                                AllMeasures[apmes+'_res'] = 'Pass' if AllMeasures['Prect2'] <= AllMeasures[apmes] else 'Fail'
                            else: AllMeasures[apmes+'_res'] = 'Fail'
                        elif apmes in ['PDelta'] and exp in ['Nego*']:
                            AllMeasures[apmes+'_res'] = 'Fail'
                            AllMeasures[apmes+'_exp'] = None
                            #Get Nego power value from cap
                            Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[idx]['General']['PD'][0],self.timing_map[idx]['General']['SD'][0]])
                            if len(Excap)>1:
                                powval = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                                value = self.Json_TC['App_Measures'][str(idx)][apmes]['Value']
                                if len(powval)>0:
                                    AllMeasures[apmes+'_exp'] = round(float(value)*powval[0],2)
                                    if AllMeasures[apmes] < AllMeasures[apmes+'_exp'] : AllMeasures[apmes+'_res'] = 'Pass'
        return AllMeasures
    def CPLmeasure(self,index,AllMeasures):
        #Get DPL
        DPL=None
        if 'SS' in self.timing_map[2]['Ping']:
            res = self.CalculateVoltTwindow(self.timing_map[2]['Ping']['SS'][0][0][0],self.AllChannelData,winsize=[9,11])
            DPL = res[0]
        #Get CPLs
        limit = [self.timing_map[2]['General']['PD'][0],len(self.file_list)-1]
        #find all Cloak 360 flows
        prevclk = 0
        cnt=0
        CLKtterminate = []
        Tcloak =[]
        CPL=[]
        id = limit[0]
        while id < limit[1]:
            if self.file_list[id].get('isFWTestermessage') ==False and self.file_list[id].get('isTesterPkt') ==True:
                if 'Cloak' in self.file_list[id].get('pktType'):
                    # print('clk',id,cnt)
                    cnt+=1
                    #Get SD
                    SDid = id+1
                    while SDid < limit[1]:
                        if any(rs in self.file_list[SDid].get('pktType') for rs in ['Shutdown','Test_Stop']):
                            break
                        SDid+=1
                    # print('SD',SDid)
                    if 'CLK_tterminate' in self.Json_TC['App_Measures'][index]:
                        if id != SDid:
                            CLKtterminate.append(round((self.file_list[SDid]['stopTime']*1000)-(self.file_list[id+1]['stopTime']*1000),2))
                        else:CLKtterminate.append(0)
                    if 'Tcloak' in self.Json_TC['App_Measures'][index]:
                        if cnt >1 and prevclk != 0:
                            #find PD 
                            PDid = id
                            while PDid > limit[0]:
                                if  'Ping Initiated' in self.file_list[PDid].get('pktType'):
                                    break
                                PDid-=1
                            Tcloak.append(round((self.file_list[PDid]['startTime']*1000)-(self.file_list[prevclk+1]['stopTime']*1000),2))
                    if cnt >1:
                        #cal CPLs
                        res = self.CalculateVoltTwindow(id,self.AllChannelData,winsize=[9,11])
                        CPL.append(res[0])
                    prevclk = id
                    id=SDid
                else:id+=1
            else:id+=1
        AllMeasures['DPL'] = DPL
        AllMeasures['CPLCheck'] = CPL
        AllMeasures['CLK_tterminate'] = CLKtterminate
        AllMeasures['Tcloak'] = Tcloak
        AllMeasures['CloakSeqCount'] = cnt-1
    def OtherChecks(self,index):
        # print(self.timing_map)
        AllOtherChecks = {}
        if str(index) in self.Json_TC['other_checks_details']:
            if len(self.Json_TC['other_checks_details'][str(index)])>0:
                for apchk in self.Json_TC['other_checks_details'][str(index)]:
                    if apchk in ['ReserveBitChek']:
                        self.ReserveBitChek(AllOtherChecks,index)
                    if apchk in ['BitsCheck']:
                        self.BitsCheck(index,AllOtherChecks)
                    if apchk in ['PacketCheck']:
                        self.PacketCheck(index,AllOtherChecks)
                    if apchk in ['OffsetValue']:
                        self.OffsetValueCheck(AllOtherChecks,index)
                    if apchk in ['PLA_PLOTvsPKT']:
                        self.PLA_PrectCheck(AllOtherChecks,index)
                    if apchk in ['EyeDigramCheck']:
                        print(self.timing_map)
                        self.EyeDigramCheck(AllOtherChecks,index)
                    if apchk in ['ILPKT']:
                        reslt = []
                        resvalue =[]
                        expvalue = []
                        ILPKT_index = 0
                        for packets in self.Json_TC['other_checks_details'][str(index)]['ILPKT']:
                            if packets['packet'][1] is None:
                                expvalue.append(str(packets['packet'][0]))
                            else:
                                expvalue.append(str(packets['packet'][0])+'-'+str(packets['packet'][1]))
                            # expvalue.append(str(packets['packet'][0])) if packets['packet'][1] is None else str(packets['packet'][0])+'-'+str(packets['packet'][1])
                            # print(expvalue,index)
                            if len(self.timing_map[index]['Illegal'])>0:
                                status =0
                                for ip in self.timing_map[index]['Illegal']:
                                    # ippkt = self.timing_map[index]['Illegal'][ip]
                                    if packets['packet'][1] is None:
                                        if packets['packet'][0] in ip[0][1]:
                                            resvalue.append(ip[0][1])
                                            status=1
                                            ILPKT_index = ip[0][0]
                                            break
                                    else:
                                        if packets['packet'][0] in ip[0][1] and packets['packet'][1] in ip[0][2]:
                                            resvalue.append(ip[0][1]+''+ip[0][2])
                                            status=1
                                            ILPKT_index = ip[0][0]
                                            break
                                    # if packets['packet'][0] in ippkt['PK'] if packets['packet'][1] is None else packets['packet'][0] in ippkt['PK'] and packets['packet'][1] in ippkt['value']:
                                    #     resvalue.append(ippkt['PK']) if packets['packet'][1] is None else ippkt['PK']+''+ippkt['value']
                                    #     status=1
                                if status == 0: reslt.append('Fail')
                            else:reslt.append('Fail')
                            # #check if any otherpackets present in the IP 
                            # for ip in timingmap[index]['Illegal']
                            AllOtherChecks['ILPKT'] =  ','.join(resvalue) if len(resvalue)>0 else 'NA'
                            AllOtherChecks['ILPKT_exp'] = ','.join(expvalue) if len(expvalue)>0 else 'NA'
                            AllOtherChecks['ILPKT_res'] ='Fail' if len(reslt)>0 else 'Pass'
                        if 'F1-Fq_AF_ILPKT' in self.Json_TC['other_checks_details'][str(index)]:
                            AllOtherChecks['F1-Fq_AF_ILPKT'] = None
                            exp = self.Json_TC['other_checks_details'][str(index)]['F1-Fq_AF_ILPKT']['expected']
                            AllOtherChecks['F1-Fq_AF_ILPKT_exp'] = str(exp[0])+'-'+str(exp[1])+' kHz'
                            AllOtherChecks['F1-Fq_AF_ILPKT_res'] = 'Fail'
                            if ILPKT_index != 0 :
                                fqpkt = self.GetPacketDetails(packet='',value='FOP:',limit=[ILPKT_index,len(self.file_list)-1])
                                if len(fqpkt)>1:
                                    AllOtherChecks['F1-Fq_AF_ILPKT'] = float(self.file_list[fqpkt[2]].get('value').split(':')[1].split(' ')[0])
                                    AllOtherChecks['F1-Fq_AF_ILPKT_res'] ='Pass' if AllOtherChecks['F1-Fq_AF_ILPKT'] >= exp[0] and AllOtherChecks['F1-Fq_AF_ILPKT'] <= exp[1] else 'Fail'
                    if apchk in ['F1-Fq_AF_Cloak']:
                        AllOtherChecks['F1-Fq_AF_Cloak'] = None
                        exp = self.Json_TC['other_checks_details'][str(index)]['F1-Fq_AF_Cloak']['expected']
                        AllOtherChecks['F1-Fq_AF_Cloak_exp'] = str(exp[0])+'-'+str(exp[1])+' kHz'
                        AllOtherChecks['F1-Fq_AF_Cloak_res'] = 'Fail'
                        if 'Cloak' in self.timing_map[index]:
                            lastclkpkt = self.timing_map[index]['Cloak'][len(self.timing_map[index]['Cloak'])][0][0]
                            if len(self.timing_map[index]['Cloak'])>0:
                                fqpkt = self.GetPacketDetails(packet='',value='FOP:',limit=[len(self.file_list)-1,lastclkpkt])
                                if len(fqpkt)>1:
                                    AllOtherChecks['F1-Fq_AF_Cloak'] = float(self.file_list[fqpkt[2]].get('value').split(':')[1].split(' ')[0])
                                    AllOtherChecks['F1-Fq_AF_Cloak_res'] ='Pass' if AllOtherChecks['F1-Fq_AF_Cloak'] >= exp[0] and AllOtherChecks['F1-Fq_AF_Cloak'] <= exp[1] else 'Fail'
                    if apchk in ['F1-Fq']:
                        exp = self.Json_TC['other_checks_details'][str(index)]['F1-Fq']['expected']
                        AllOtherChecks['F1-Fq_exp'] = str(exp[0])+'-'+str(exp[1])+' kHz'
                        AllOtherChecks['F1-Fq_res'] ='Fail'
                        if 'FOP' in self.timing_map[index]['General']:
                            AllOtherChecks['F1-Fq'] = self.timing_map[index]['General']['FOP'][3]
                            AllOtherChecks['F1-Fq_res'] ='Pass' if AllOtherChecks['F1-Fq'] >= exp[0] and AllOtherChecks['F1-Fq'] <= exp[1] else 'Fail'
                    if apchk in ['F2-Fq']:
                        exp = self.Json_TC['other_checks_details'][str(index)]['F2-Fq']['expected']
                        AllOtherChecks['F2-Fq_exp'] = str(exp[0])+'-'+str(exp[1])+' kHz'
                        AllOtherChecks['F2-Fq_res'] ='Fail'
                        if 'FOP' in self.timing_map[index]['General']:
                            AllOtherChecks['F2-Fq'] = self.timing_map[index]['General']['FOP'][3]
                            AllOtherChecks['F2-Fq_res'] ='Pass' if AllOtherChecks['F2-Fq'] >= exp[0] and AllOtherChecks['F2-Fq'] <= exp[1] else 'Fail'
                    if apchk in ['CEStability']:
                        AllOtherChecks['CEStability_exp']='Pass'
                        AllOtherChecks['CEStability']=None
                        AllOtherChecks['CEStability_res']='Fail'
                        if self.stability is not None:
                            AllOtherChecks['CEStability']=self.stability
                            AllOtherChecks['CEStability_res']='Pass'
                    if apchk in ['InitialVoltage']:
                        AllOtherChecks['InitialVoltage'] = self.initialVoltage
                        exp = self.Json_TC['other_checks_details'][str(index)]['InitialVoltage']['expected']
                        AllOtherChecks['InitialVoltage_exp'] = str(exp[0])+'-'+str(exp[1])
                        if AllOtherChecks['InitialVoltage'] is not None:
                            res = self.check_measure(exp,AllOtherChecks['InitialVoltage'])
                            AllOtherChecks['InitialVoltage_res'] = res[1]
                        else : AllOtherChecks['InitialVoltage_res'] ='Fail'
                    if apchk in ['LoadXCEcount']:
                        AllOtherChecks['LoadXCEcount']=[]
                        AllOtherChecks['LoadXCEcount_exp']=self.Json_TC['other_checks_details'][str(index)]['LoadXCEcount']['expected']
                        AllOtherChecks['LoadXCEcount_res'] ='Fail'
                        #check Xce packets count for all applied loads
                        if len(self.Json_TC['load_names'])>0:
                            for ld in self.timing_map[2]['Loads']:
                                if self.timing_map[2]['Loads'][ld] != 'Fail':
                                    id = (self.timing_map[2]['Loads'][ld])+1
                                    count = 0
                                    while id < len(self.file_list):
                                        # print(id)
                                        if self.file_list[id].get('isTesterPkt') == True and self.file_list[id].get('isFWTestermessage')==False:
                                            if any(rs in self.file_list[id].get('pktType') for rs in ['Control Error','Extended Control Error']):
                                                if any(rs in self.file_list[id].get('value') for rs in self.Json_TC['other_checks_details'][str(index)]['LoadXCEcount']['Values']):
                                                    count+=1
                                                else: count = 0
                                        if any(rs in self.file_list[id].get('pktType') for rs in ['MPP_XCE_Stabilized','Set_Load']): break
                                        id+=1
                                    AllOtherChecks['LoadXCEcount'].append(count)
                                    break
                        if len(AllOtherChecks['LoadXCEcount'])>0:
                            if all(rs >= AllOtherChecks['LoadXCEcount_exp'] or rs == 0 for rs in AllOtherChecks['LoadXCEcount']): AllOtherChecks['LoadXCEcount_res'] ='Pass'
                        AllOtherChecks['LoadXCEcount']=','.join(map(str,AllOtherChecks['LoadXCEcount'])) if len(AllOtherChecks['LoadXCEcount'])>0 else None
                    if apchk in ['360flow']:
                        AllOtherChecks['360flow_exp'] = 'Pass'
                        AllOtherChecks['360flow'] ='NA'
                        AllOtherChecks['360flow_res'] ='Fail'
                        if 'Ping' in self.timing_map[2]:
                            if 'SS' in self.timing_map[2]['Ping']:
                                AllOtherChecks['360flow'] = AllOtherChecks['360flow_res'] ='Pass'
                    if apchk in ['Force_SD']:
                        AllOtherChecks['Force_SD_exp'] = 'Pass'
                        AllOtherChecks['Force_SD'] ='NA'
                        AllOtherChecks['Force_SD_res'] ='Fail'
                        pkt = self.Json_TC['other_checks_details'][str(index)]['Force_SD']['packet'][0]
                        value = self.Json_TC['other_checks_details'][str(index)]['Force_SD']['packet'][1]
                        if self.Json_TC['other_checks_details'][str(index)]['Force_SD']['refPrevious'] == True:
                            #find previous flow limit
                            tmplimit = [0,self.timing_map[index]['General']['PD'][0]]
                            id = 0
                            # while id 
                            limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
                        else:
                            limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
                        id = limit[0]
                        pktstatus = 0
                        while id < limit[1]:
                            if value is None:
                                if pkt in self.file_list[id].get('pktType'):
                                    pktstatus=1
                                    break
                            else:
                                if pkt in self.file_list[id].get('pktType') and value in self.file_list[id].get('value'):
                                    pktstatus=1
                                    break
                            id+=1
                        if pktstatus !=0:
                            #check for SD
                            diff = abs(pktstatus - limit[1])
                            if diff == 1:
                                AllOtherChecks['Force_SD_res']='Pass'
                            else:
                                id = pktstatus+1
                                while id < limit[1]:
                                    if self.file_list[id].get('isTesterPkt') == True and self.file_list[id].get('isFWTestermessage'):
                                        AllOtherChecks['Force_SD_res']='Pass'
                                        AllOtherChecks['Force_SD'] ='Pass'
                                        break
                                    else:
                                        AllOtherChecks['Force_SD_res']='Fail'
                                        AllOtherChecks['Force_SD'] ='Fail'
                                    id+=1
                    if apchk in ['PowerMatch']:
                        #Get Maxpower declared in SDF
                        GetQIConfiguration = APIOperations(url=self.JapiData[self.mode]['GetQIConfiguration'],retype='json')
                        data = GetQIConfiguration.GetRequest()
                        maxpow=data['maxPower_MPTPT']
                        AllOtherChecks['PowerMatch_exp'] = f'MaxPow:{maxpow},NegPow:{maxpow},PotPow:{maxpow}'
                        AllOtherChecks['PowerMatch'] ='NA'
                        AllOtherChecks['PowerMatch_res'] ='Fail'
                        if 'GRQexcap' in self.timing_map[index]['Nego']:
                            if self.timing_map[index]['Nego']['GRQexcap'][0][1] is not None:
                                pktindex =  self.timing_map[index]['Nego']['GRQexcap'][0][0][0]+1
                                potpow = literal_eval(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1].get('sRawData'))/10
                                negpow = literal_eval(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][1].get('sRawData'))/10
                                AllOtherChecks['PowerMatch'] =f'MaxPow:{maxpow},NegPow:{negpow},PotPow:{potpow}'
                                if maxpow == potpow and maxpow == negpow: AllOtherChecks['PowerMatch_res'] ='Pass'
                    if apchk in['SRQcountMatch']:
                        lastsdtime = None
                        AllOtherChecks['SRQcountMatch_exp'] = 'Pass'
                        AllOtherChecks['SRQcountMatch'] ='NA'
                        AllOtherChecks['SRQcountMatch_res'] ='Fail'
                        AllOtherChecks['CoilPlaceInterval']='NA'
                        AllOtherChecks['CoilPlaceInterval_exp']='NA'
                        AllOtherChecks['CoilPlaceInterval_res']='Fail'
                        if 'Nego' in self.timing_map[index]:
                            if 'SRQen' in self.timing_map[index]['Nego']:
                                #get the value of last flow
                                endvalue = int(self.file_list[self.timing_map[index]['Nego']['SRQen'][0][0][0]].get('value').split(':')[1].replace(' ','').replace('}',''))
                                #get the value of first flow
                                id = self.timing_map[index]['General']['PD'][0]
                                while id > 0:
                                    if 'Specific Request' in self.file_list[id].get('pktType') and 'End Negotiation' in self.file_list[id].get('value'):
                                        firstvalue = int(self.file_list[id].get('value').split(':')[1].replace(' ','').replace('}',''))
                                        AllOtherChecks['SRQcountMatch'] = str(firstvalue)+','+str(endvalue)
                                        if endvalue == firstvalue:
                                            AllOtherChecks['SRQcountMatch_res']='Pass'
                                        #get sd of the flow to calculate coil place interval
                                        sid = id
                                        while sid < len(self.file_list):
                                            if self.file_list[sid].get('pktType') in ['Shutdown','Test_Stop']:
                                                lastsdtime=round(self.file_list[sid].get('stopTime')*1000,2)
                                                break
                                            sid+=1
                                        break
                                    id-=1
                        if lastsdtime is not None and 'CoilPlaceInterval' in self.Json_TC['other_checks_details']:
                            AllOtherChecks['CoilPlaceInterval_exp'] = self.Json_TC['other_checks_details']['CoilPlaceInterval']
                            AllOtherChecks['CoilPlaceInterval'] ='NA'
                            AllOtherChecks['CoilPlaceInterval_res'] ='Fail'
                            if 'General' in self.timing_map[index]:
                                if 'PD' in self.timing_map[index]['General']:
                                    AllOtherChecks['CoilPlaceInterval'] = round(self.file_list[self.timing_map[index]['General']['PD']-1].get('startTime')*1000,2) - lastsdtime
                                    reslt = self.check_measure(AllOtherChecks['CoilPlaceInterval_exp'],AllOtherChecks['CoilPlaceInterval'],0)
                                    AllOtherChecks['CoilPlaceInterval_exp'] = str(reslt[0][0])+'-'+str(reslt[0][1])
                                    AllOtherChecks['CoilPlaceInterval_res'] = reslt[1]
                    if apchk in ['FlowInterval']:
                        exp = self.Json_TC['other_checks_details'][str(index)]['FlowInterval']['expected']
                        AllOtherChecks['FlowInterval_exp'] = '.'.join(map(str,self.Json_TC['other_checks_details'][str(index)]['FlowInterval']['expected']))
                        AllOtherChecks['FlowInterval'] ='NA'
                        AllOtherChecks['FlowInterval_res'] ='Fail'
                        limit=[0,self.timing_map[1]['General']['PD'][0]] if self.Json_TC['other_checks_details'][str(index)]['FlowInterval']['flow'] ==-1 else [0,self.timing_map[2]['General']['PD'][0]]
                        #Get SD 
                        id = limit[1]
                        while id > limit[0]:
                            if self.file_list[id].get('pktType') =='Configuration':
                                SID = id
                                while SID < limit[1]:
                                    if self.file_list[SID].get('pktType') =='Shutdown':
                                        AllOtherChecks['FlowInterval'] = round((self.file_list[limit[1]-1].get('startTime')*1000) - (self.file_list[id].get('stopTime')*1000),2)
                                        reslt = self.check_measure(exp,AllOtherChecks['FlowInterval'],comp=self.Json_TC['other_checks_details'][str(index)]['FlowInterval']['comp']) 
                                        AllOtherChecks['FlowInterval_exp'] = reslt[2]+str(reslt[0][0]) if reslt[2] != 0 else reslt[0][0]
                                        AllOtherChecks['FlowInterval_res'] = reslt[1]
                                        break
                                    SID+=1
                                break
                            id-=1
                    if apchk in ['StableToRunTime']:
                        AllOtherChecks['StableToRunTime'] = None
                        exp = self.Json_TC['other_checks_details'][str(index)]['StableToRunTime']['expected']
                        AllOtherChecks['StableToRunTime_exp'] = '-'.join(map(str,exp))
                        AllOtherChecks['StableToRunTime_res'] ='Fail'
                        # print('stable',self.stability)
                        if self.stability is not None:
                            runtime = round( (self.file_list[self.timing_map[index]['General']['SD'][0]].get('startTime') - self.file_list[self.stability].get('stopTime'))*1000,2)
                            AllOtherChecks['StableToRunTime'] = runtime
                            reslt = self.check_measure(exp, runtime,self.Json_TC['other_checks_details'][str(index)][apchk]['comp'])
                            AllOtherChecks[str(apchk)+'_exp']=reslt[2]+str(reslt[0][0]) if reslt[2] != 0 else str(reslt[0][0])+'-'+str(reslt[0][1])
                            AllOtherChecks[str(apchk)+'_res'] = reslt[1]
                    if apchk in ['LoadCheck']:
                        AllOtherChecks['LoadCheck'] = None
                        AllOtherChecks['LoadCheck_exp'] =None
                        exploads=[]
                        if len(self.Json_TC['load_names'])>0:
                            exploads = self.Json_TC['load_names']
                            AllOtherChecks['LoadCheck_exp'] = ','.join(map(str,exploads))
                        else:
                            if self.Json_TC['App_Measures'][str(index)]['Prect']['expected'] == 'Nego%':
                                #Get Nego power value from cap
                                Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]])
                                if len(Excap)>1:
                                    negopow = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                                    expper = self.Json_TC['App_Measures'][str(index)]['Prect']['percentage']
                                    if len(negopow)>0:
                                        exploads.append(str(int((((negopow[0])/100)*expper)*1000))+'mW')
                                        AllOtherChecks['LoadCheck_exp'] = ','.join(map(str,exploads))
                            elif self.Json_TC['App_Measures'][str(index)]['Prect']['expected'] == 'Potential%':
                                # Get Potential power value from cap
                                Excap = self.GetPacketDetails('Extended_Power_Transmitter_Extended_Capabilities',limit=[self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]])
                                if len(Excap)>1:
                                    potnpow = GeneralMethods.GetFloatFromStr(self.file_list[Excap[2]]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])
                                    expper = self.Json_TC['App_Measures'][str(index)]['Prect']['percentage']
                                    if len(potnpow)>0:
                                        exploads.append(str(int((((potnpow[0])/100)*expper)*1000))+'mW')
                                        AllOtherChecks['LoadCheck_exp'] = ','.join(map(str,exploads))
                        AllOtherChecks['LoadCheck_res'] = 'Fail'
                        if len(self.timing_map[index]['Loads'])>0 and len(exploads)>0:
                            apploads = []
                            for appload in self.timing_map[index]['Loads']:
                                apploads.append(str(appload)+'@'+str(self.timing_map[index]['Loads'][appload]))
                            AllOtherChecks['LoadCheck'] = ','.join(map(str,apploads))
                            if all(rs in self.timing_map[index]['Loads'] for rs in exploads): AllOtherChecks['LoadCheck_res'] = 'Pass'
        return AllOtherChecks
    def GetInitailVoltage(self,index):
        if str(index) in self.Json_TC['other_checks_details']:
            if 'CEStability' in self.Json_TC['other_checks_details'][str(index)]:
                try:
                    limit=[self.timing_map[2]['General']['PD'][0],self.timing_map[2]['General']['SD'][0]]
                    id = limit[0]
                    while id < limit[1]:
                        if 'MPP_XCE_Stabilized' in self.file_list[id].get('pktType'):
                            revid = id
                            while revid > limit[0]:
                                if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                                    self.stability=revid
                                    # print('stability',self.stability)
                                    #GetIntital Voltage
                                    # print(self.Json_TC['other_checks_details'])
                                    if 'InitialVoltage' in self.Json_TC['other_checks_details'][str(index)]:
                                        res = self.CalculateVoltTwindow(revid,self.AllChannelData)
                                        self.initialVoltage =  res[0]
                                    break
                                revid-=1
                            break
                        id+=1
                except Exception as e:
                    traceback.print_exc()
    def GetStableBtwLimits(self,limit):
        id = limit[0]
        XCEcount = 0
        while id < limit[1]:
            if any(rs in self.file_list[id].get('pktType') for rs in ['Extended Control Error','Control Error']): XCEcount +=1
            if 'MPP_XCE_Stabilized' in self.file_list[id].get('pktType'):
                revid = id
                while revid > limit[0]:
                    
                    if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                        # res = self.CalculateVoltTwindow(revid,self.AllChannelData)
                        return [revid,XCEcount]
                    revid-=1
            id+=1
        return None
    def CalculateVoltBtwStEd(self,indx,AllChannelData):
        starttime = (AllChannelData['starttime']/100000)
        vlot =0
        index = 0
        # print('chks',self.file_list[indx].get('startTime')*1000,((self.file_list[indx].get('startTime')*1000)-starttime-8))
        sindex = int(((((self.file_list[indx].get('startTime'))*1000)-starttime)-8)/AllChannelData['Interval'])
        eindex = int((((self.file_list[indx].get('stopTime'))*1000)-starttime)/AllChannelData['Interval'])
        id = sindex
        while id < eindex:
            if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) > vlot : 
                index=id
                vlot = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
            id+=1
        # print('vlt',vlot)
        return [round(vlot,2), index]  
    def CalculateVoltTwindow(self,indx,AllChannelData,winsize=[8,11]):
        #calculate vrect min /max for all XCE twin time
        xceEtime = self.file_list[indx].get('startTime')*1000
        xceSindex = int((xceEtime-(winsize[1]))/AllChannelData['Interval'])
        xceEindex = int((xceEtime-winsize[0])/AllChannelData['Interval'])
        id = xceSindex
        VRlist=[]
        # Vrectmax = 0
        while id < xceEindex:
            VRlist.append(round(abs(AllChannelData['RV']['displayDataChunk'][id]),4))
            # if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) > Vrectmax or Vrectmax==0: 
            #     Vrectmax = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
            id+=1
        return [round((sum(VRlist)/len(VRlist)),3), id-1]
    def CalculateVoltTimePeriod(self,AllChannelData,stime,etime):
        #calculate vrect min /max for all XCE twin time
        xceEtime = etime*1000
        xceSindex = int((stime*1000)/AllChannelData['Interval'])
        xceEindex = int((etime*1000)/AllChannelData['Interval'])
        id = xceSindex
        Vrectmax = 0
        while id < xceEindex:
            if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) > Vrectmax or Vrectmax==0: 
                Vrectmax = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
            id+=1
        return [round(Vrectmax,3), id-1]
    def CalculateVoltPlotIndex(self,index,AllChannelData):
        return round(abs(AllChannelData['RV']['displayDataChunk'][index]),4)
    def check_measure(self,exp_val,obsr_val,comp=0):
        res = None
        compval=0
        exp_vals=[]
        if obsr_val != None:
            if len(exp_val)==1:
                exp_vals.append(exp_val[0])
                if comp =='GTEQL':
                    if  obsr_val >= exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval='>='
                elif comp =='LTEQL':
                    if  obsr_val <= exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval='<='
                elif comp =='EQL':
                    if  obsr_val == exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval='=='
                #add for rql,lseql
            else:
                exp_vals=exp_val
                if obsr_val >= exp_vals[0] and obsr_val <= exp_vals[1]:
                    res =  'Pass'
                else:  
                    res = 'Fail'
        else:
            res = 'Fail'
        return [exp_vals,res,compval]
    def ReserveBitChek(self,Allchecks,index):
        #check Reserve bit value for all DUT packets exp Mfg reserve both flow
        res =[]
        val = []
        expected = self.Json_TC['other_checks_details'][str(index)]['ReserveBitChek']['expected']
        if len(self.timing_map[index]['General'])>0:
            limit1 = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            id = limit1[0]
            while id < limit1[1]:
                if self.file_list[id].get('isTesterPkt') == False and self.file_list[id].get('isFWTestermessage')==False:
                    #find and check all reserve bits
                    for d1 in self.file_list[id]['header_Payload']['childelement']:
                        for d2 in d1['childelement']:
                            if 'Reserved' in d2['sDecodedValue']:
                                if d2['sRawData'] != expected:
                                    val.append(d2['sRawData'])
                                    res.append(str(self.file_list[id]['pktType'])+'@index='+str(id)+':'+str(d2['sDecodedValue'])+str(d2['sRawData']))
                id+=1
            Allchecks['ReserveBitChek']=','.join(val) if len(val)>0 else 'No Mismatch'
            Allchecks['ReserveBitChek_exp']='Reserved='+str(expected)
            Allchecks['ReserveBitChek_res']='Pass' if len(res)==0 else 'Fail'
            Allchecks['ReserveBitChek_remark']=','.join(res)
    def OffsetValueCheck(self,Allchecks,index):
        res =[]
        val = []
        expected = self.Json_TC['other_checks_details'][str(index)]['OffsetValue']['expected']
        if len(self.timing_map[index]['General'])>0:
            limit1 = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            id = limit1[0]
            while id < limit1[1]:
                if 'MPP_FOD' in self.file_list[id].get('pktType') and 'Offset applied:' in self.file_list[id].get('value'):
                    offsetlist = GeneralMethods.GetFloatFromStr(self.file_list[id].get('value'))
                    print(offsetlist)
                    if len(offsetlist)>0:
                        if offsetlist[1] != expected: 
                            val.append(offsetlist[1])
                            res.append(f"Found offset value {offsetlist[1]}, but the Expected value is {expected} ")
                id+=1
        Allchecks['OffsetValue']=','.join(map(str,val)) if len(val)>0 else 'No Mismatch'
        Allchecks['OffsetValue_exp']=str(expected)
        Allchecks['OffsetValue_res']='Pass' if len(res)==0 else 'Fail'
        Allchecks['OffsetValue_remark']=','.join(res)
    def CheckFinalResult(self):
        res=[]
        checklist = self.Json_TC['Result_checks']
        if len(checklist)==0 or type(checklist)==list:
            return 'NA'
        else:
            for index in checklist:
                if len(checklist[index])>0:
                    for check in checklist[index]:
                        if check in self.timing_map[int(index)]['Measures']:
                            if self.timing_map[int(index)]['Measures'][check+'_res']=='Fail':res.append('Fail')
                        if check in self.timing_map[int(index)]['OtherChecks']:
                            if self.timing_map[int(index)]['OtherChecks'][check+'_res']=='Fail':res.append('Fail')
        return 'Fail' if len(res)>0 else 'Pass'
    #to ensure the PLA pck Rect. Power is in limit of +/- 100mW of measured W from plot
    def PLA_PrectCheck(self,Allchecks,index):
        val=[]
        if 'PT' in self.timing_map[index]:
            if 'PLA' in self.timing_map[index]['PT']:
                if len(self.timing_map[index]['PT']['PLA'])>0:
                    for PLA in self.timing_map[index]['PT']['PLA']:
                        res = self.CalculateVoltTwindow(PLA[0][0],self.AllChannelData,winsize=[19,21])
                        Volt=res[0]
                        Curnt = round(abs(self.AllChannelData3['RV']['displayDataChunk'][res[1]]),2)
                        Plot_P = round((Volt*Curnt),2)
                        #Get Power from pkt
                        res= GeneralMethods.GetFloatFromStr(self.file_list[PLA[0][0]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])
                        Pkt_P = res[0]
                        if abs(Pkt_P-Plot_P) >= 0.100:
                            val.append(f"Diff:{round(abs(Pkt_P-Plot_P),3)}@{PLA[0][0]}")
        Allchecks['PLA_PLOTvsPKT']=','.join(map(str,val)) if len(val)>0 else 'No Mismatch'
        Allchecks['PLA_PLOTvsPKT_exp']="+/-100mW"
        Allchecks['PLA_PLOTvsPKT_res']='Pass' if len(val)==0 else 'Fail'
    def UpdateToJsonReport(self):
        self.FinalRepData.append({'Header':self.Header,'SeqResults':self.timing_map})
        #Sorting TBD -- Not req
        self.FinalRep.update_file(self.FinalRepData)
        #update extracts to consolidated JSON file
        #Avoid already validate data TBD
        if self.Header['SWVersion'] not in self.conRepData: self.conRepData[self.Header['SWVersion']]={}
        if self.Header['FWVersion'] not in self.conRepData[self.Header['SWVersion']]: self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']]={}
        if self.Header['HWVersion'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']]: self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']]={}
        if self.Header['BoardNo'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']]: 
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']]={}
        if str(self.Header['DUTName'])+'_'+str(self.Header['DUTID']) not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']]: 
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])]={}
        if self.Header['DUTSL'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])]: 
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']]={}
        # if self.Header['DUTID'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][self.Header['DUTName']]: 
        #     self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][self.Header['DUTName']][self.Header['DUTID']]={}
        if self.Header['ChapterName'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']]: 
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']]={}
        if self.Header['Position'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']]: 
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']]={} 
        if self.Header['TestcaseID'] not in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']]: 
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']][self.Header['TestcaseID']]=[] 
        ConTCdata={"Header" : {
            "UID":self.Header['UID'],
            "TestcaseID":self.Header['TestcaseID'],
            "TestcaseName":self.Header['TestcaseName'],
            "ChapterID":self.Header['ChapterID'],
            "CapturePath":self.Header['CapturePath'],
            "ProjectName":self.Header['ProjectName'],
            "Run":self.Header['Run'],
            "TestLab":self.Header['TestLab'],
            "Engineer":self.Header['Engineer'],
            "TCresult":self.Header['TCresult']
        },
        'Timings':{1:{},2:{}},'Measures':{1:{},2:{}},'OtherChecks':{1:{},2:{}}
        }
        if 1 in self.timing_map:
            ConTCdata['Timings'][1]=self.timing_map[1]['Timings']
            ConTCdata['Measures'][1]=self.timing_map[1]['Measures']
            ConTCdata['OtherChecks'][1]=self.timing_map[1]['OtherChecks']
        if 2 in self.timing_map:
            ConTCdata['Timings'][2]=self.timing_map[2]['Timings']
            ConTCdata['Measures'][2]=self.timing_map[2]['Measures']
            ConTCdata['OtherChecks'][2]=self.timing_map[2]['OtherChecks']
        #check that smae tests already available in the report, if so update with new results.
        testPresent = False
        indexid = 0
        if len(self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']][self.Header['TestcaseID']])>0:
            #already same tests avaialble , check same project name and run name avaiable in json
            for avatests in self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']][self.Header['TestcaseID']]:
                if avatests['Header']['ProjectName'] == ConTCdata['Header']['ProjectName'] and avatests['Header']['Run'] == ConTCdata['Header']['Run']: 
                    testPresent = True
                    break
                indexid+=1
        if testPresent==False:
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']][self.Header['TestcaseID']].append(ConTCdata)
            self.conRep.update_file(self.conRepData)
        else:
            #replace with new Testresults
            self.conRepData[self.Header['SWVersion']][self.Header['FWVersion']][self.Header['HWVersion']][self.Header['BoardNo']][str(self.Header['DUTName'])+'_'+str(self.Header['DUTID'])][self.Header['DUTSL']][self.Header['ChapterName']][self.Header['Position']][self.Header['TestcaseID']][indexid]=ConTCdata
            self.conRep.update_file(self.conRepData)
    def BitsCheck(self,index,AllOtherChecks):
        reslt = []
        resvalue =[]
        expvalue = []
        for BITSck in self.Json_TC['other_checks_details'][str(index)]['BitsCheck']:
            # print(BITSck)
            if  BITSck['refPrevious'] ==True:
                limit = [0,self.timing_map[index]['General']['PD'][0]-1]
            else:
                if 'refNextAll' in BITSck:
                    limit = [self.timing_map[index]['General']['SD'][0],len(self.file_list)-1]
                else:
                    limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            # if BITSck['refPrevious']  == True:
            #     limit = [0,self.timing_map[index]['General']['PD'][0]-1]
            # else:
            #     limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            print("bits",limit)
            #find the packet to check bits
            id = limit[0]
            pktindex = 0
            while id < limit[1]:
                # if self.file_list[id]['isFWTestermessage'] != True and self.file_list[id]['isTesterPkt'] != True:
                if BITSck['packet'][1] is None:
                    if BITSck['packet'][0] in self.file_list[id].get('pktType'):
                        pktindex = id
                        break
                else:
                    if BITSck['packet'][0] in self.file_list[id].get('pktType') and BITSck['packet'][1] in self.file_list[id].get('value'):
                        pktindex = id
                        break
                id+=1
            #once get pkt index performe bits checks
            if pktindex != 0:
                for ck in BITSck['Checks']:
                    if ck =='NEG':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NEG='+str(BITSck['Checks'][ck]['expected']))
                        # print('neg',self.file_list[pktindex]['header_Payload']['childelement'][4]['childelement'][0]['sRawData'],BITSck['Checks'][ck]['expected'])
                        if self.file_list[pktindex]['header_Payload']['childelement'][4]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NEG='+str(self.file_list[pktindex]['header_Payload']['childelement'][4]['childelement'][0]['sRawData']))
                    if ck == 'Mjrver':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mjrver='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mjrver='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']))
                    if ck == 'Mnrver':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mnrver='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mnrver='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sRawData']))
                    
                    if ck=='Restricted':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Restricted='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Restricted='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData']))
                    
                    if ck=='PCHtime':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PCHtime='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PCHtime='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']))
                    if ck=='CLkpingValue':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkpingValue='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkpingValue='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData']))
                    if ck=='CLkdelay':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdelay='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdelay='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData']))
                    if ck=='CLkdetctPing':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdetctPing='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdetctPing='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData']))
                    if ck=='CLkReason':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkReason='+str(BITSck['Checks'][ck]['expected']))
                        if BITSck['Checks'][ck]['expected'] not in self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sDescription']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkReason='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sDescription']))
                    if ck=='NegoPwr':
                        exp = float(BITSck['Checks'][ck]['expected'][0])
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NegoPwr='+str(exp))
                        negolist = GeneralMethods.GetFloatFromStr(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
                        res = self.check_measure(BITSck['Checks'][ck]['expected'],negolist[0],BITSck['Checks'][ck]['comp'])
                        if res[1] == 'Fail':
                            reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NegoPwr='+str(negolist[0]))
                    if ck=='PotentialPow':
                        exp = '-'.join(map(str,BITSck['Checks'][ck]['expected']))
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PotentialPow='+str(exp))
                        potnlist = GeneralMethods.GetFloatFromStr(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])
                        res = self.check_measure(BITSck['Checks'][ck]['expected'],potnlist[0],BITSck['Checks'][ck]['comp'])
                        if res[1] == 'Fail':
                            reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PotentialPow='+str(potnlist[0]))
                    #TPT
                    if ck=='SSvalue':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':SSvalue='+str(BITSck['Checks'][ck]['expected']))
                        if int(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']) < BITSck['Checks'][ck]['expected'][0]:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':SSvalue='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']))
                    if ck=='Ext':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Ext='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Ext='+str(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][0]['sRawData']))
                    if ck=='XIDvalue':
                        expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':XIDvalue='+str(BITSck['Checks'][ck]['expected']))
                        if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
                             reslt.append('Fail')
                        resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':XIDvalue='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']))
            
            AllOtherChecks['BitsCheck'] =  ','.join(resvalue) if len(resvalue)>0 else 'NA'
            AllOtherChecks['BitsCheck_exp'] = ','.join(expvalue) if len(expvalue)>0 else 'NA'
            AllOtherChecks['BitsCheck_res'] ='Fail' if len(reslt)>0 else 'Pass'
    def PacketCheck(self,index,AllOtherChecks):
        reslt = []
        resvalue =[]
        expvalue = []
        for pkt in self.Json_TC['other_checks_details'][str(index)]['PacketCheck']:
            AllOtherChecks['PacketCheck_res']='Fail'
            # print('pkt',pkt)
            evalue = str(pkt['packet'][0])+'_'+str(pkt['packet'][1])+';Phase: '+str(pkt['phase']) if pkt['packet'][1]!= None else str(pkt['packet'][0])+';Phase: '+str(pkt['phase'])
            pres = 'None'
            #check for packets through the PD-SD limit
            if 'refCustom' in pkt:
                limit = self.RefCustomeLimitforPkt(pkt,index)
            else:
                if  pkt['refPrevious'] ==True:
                    limit = [0,self.timing_map[index]['General']['PD'][0]]
                else:
                    if 'refNextAll' in pkt:
                        limit = [self.timing_map[index]['General']['SD'][0],len(self.file_list)-1]
                    else:
                        limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            print('limit',limit)
            if limit != None:
                id = limit[0]
                pkcount = 0
                pkvcount = 0
                pkTresp = []
                Pkttimes = []
                PktInter = []
                PkRes =[]
                PktVal = []
                expPkt = [pkt['packet'][0],pkt['packet'][1]]
                preEndTime = 0
                while id < limit[1]:
                    #check if its packet
                    if self.file_list[id].get('isFWTestermessage') ==False and self.file_list[id].get('isTesterPkt') ==False:
                        if expPkt[0] in self.file_list[id].get('pktType') and expPkt[1] in self.file_list[id].get('value') if expPkt[1] is not None else expPkt[0] in self.file_list[id].get('pktType'):
                            # print(pkt['phase'],id,'-',self.file_list[id].get('description'))
                            if pkt['phase'] != None:
                                if pkt['phase'] == self.file_list[id].get('description'):
                                    pres = self.file_list[id].get('pktType')+'_'+self.file_list[id].get('value') if expPkt[1] is not None else self.file_list[id].get('pktType')
                                    pres=pres+'@'+str(id)+';Phase: '+str(pkt['phase'])
                                    if 'Pkt_count' in pkt: pkcount +=1
                                    if 'Pkt_Value' in pkt: PktVal.append(self.file_list[id].get('value').split('-')[0])
                                    if preEndTime!=0 : PktInter.append([round((self.file_list[id].get('startTime')*1000)-preEndTime,2),id])
                                    preEndTime=self.file_list[id].get('stopTime')*1000
                                    #to check proper resp for pkt
                                    rid = id+1
                                    resstatus = False
                                    #    print('resps',rid)
                                    while rid < limit[1]:
                                        # print(file_list[rid].get('pktType'))
                                        if self.file_list[rid].get('isTesterPkt') == False and self.file_list[rid].get('isFWTestermessage')== True:
                                            PkRes.append([self.file_list[rid].get('pktType'),rid])
                                            pkTresp.append([round((self.file_list[rid]['startTime']-self.file_list[id]['stopTime'])*1000,2),id])
                                            resstatus=True
                                            break
                                        elif self.file_list[rid].get('isTesterPkt') == False and self.file_list[rid].get('isFWTestermessage')== False:
                                            break
                                        rid+=1
                                    if resstatus==False: 
                                        PkRes.append(['NoResponse',rid-1])
                                    id=rid
                                else:id+=1
                        else:id+=1
                    else: 
                        id+=1
                if 'Pkt_response' in pkt:
                    evalue = evalue+';Response:'+'|'.join(pkt['Pkt_response'])
                    if len(PkRes)>0:
                        TPkRes=[]
                        for rs in PkRes:
                            if rs[0] not in pkt['Pkt_response']:
                                TPkRes.append('@'.join(map(str,rs)))
                        if len(TPkRes)>0:
                            reslt.append('Fail')
                            pres=pres+';Response:'+','.join(TPkRes)
                        else:pres=pres+';Response:'+'No mismatch'
                        # if any(rs not in pkt['Pkt_response'] for rs in PkRes): reslt.append('Fail')
                    else:
                        if 'NOResp' not in pkt['Pkt_response']:
                            reslt.append('Fail')
                        pres=pres+';Response:None'
                if 'Pkt_count' in pkt:
                    evalue = evalue+';Count:'+str(pkt['Pkt_count'])
                    pres=pres+';Count:'+str(pkcount)
                    if pkcount < pkt['Pkt_count']:reslt.append('Fail')
                if 'Pkt_Value' in pkt:
                    evalue = evalue+';Value:'+','.join(map(str,pkt['Pkt_Value']))
                    pres=pres+';Value:'+','.join(map(str,PktVal))
                    if any(rs not in pkt['Pkt_Value'] for rs in PktVal):
                        reslt.append('Fail')
                if 'Pkt_Tresponse' in pkt:
                    evalue = evalue+';Tresponse:'+'-'.join(str(a) for a in pkt['Pkt_Tresponse'])+'ms'
                    if len(pkTresp)>0:
                        TpkTresp=[]
                        for rs in pkTresp:
                            if rs[0] < pkt['Pkt_Tresponse'][0] or rs[0] > pkt['Pkt_Tresponse'][1]:
                                TpkTresp.append(str(rs[0])+'@'+str(rs[1]))
                        if len(TpkTresp)>0:
                            reslt.append('Fail')
                            pres=pres+';Tresponse:'+','.join(TpkTresp)
                        else:pres=pres+';Tresponse:'+'No mismatch'
                        # pres=pres+';Tresponse:'+'|'.join(str(a) for a in pkTresp)
                        # if any(rs < pkt['Pkt_Tresponse'][0] or rs > pkt['Pkt_Tresponse'][1] for rs in pkTresp): reslt.append('Fail')
                    else:
                        pres=pres+';Tresponse:None'
                        reslt.append('Fail')
                if 'Pkt_Interval' in pkt:
                    TPktInter=[]
                    evalue = evalue+';Interval:'+'-'.join(str(a) for a in pkt['Pkt_Interval'])+'ms'
                    if len(PktInter)>0:
                        for rs in PktInter:
                            if rs[0] < pkt['Pkt_Interval'][0] or rs[0] > pkt['Pkt_Interval'][1]:
                                TPktInter.append(str(rs[0])+'@'+str(rs[1]))
                        if len(TPktInter)>0:
                            reslt.append('Fail')
                            pres=pres+';Interval:'+','.join(TPktInter)
                        else:pres=pres+';Interval:'+'No mismatch'
                        # pres=pres+';Interval:'+'|'.join(str(a) for a in PktInter)
                        # if any(rs != pkt['Pkt_Interval'] for rs in PktInter): reslt.append('Fail')
                    else:
                        pres=pres+';Interval:None'
                        reslt.append('Fail')
                expvalue.append(evalue)
                resvalue.append(pres)
            AllOtherChecks['PacketCheck_exp'] = ','.join(expvalue)
            AllOtherChecks['PacketCheck'] = ','.join(resvalue)
            AllOtherChecks['PacketCheck_res'] = 'Pass' if len(reslt) == 0 else 'Fail'
    def GetCloakPkts(self,index,id,packets):
        # print('clk',id,len(self.file_list))
        clkseq =0
        self.timing_map[index]['Cloak']={}
        while id < len(self.file_list)-1:
            print(id)
            # self.timing_map[index]['Cloak'][clkseq]={}
            if 'Cloak' in self.file_list[id].get('pktType') and self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                print('clkpkt',id)
                clkseq+=1
                tid = id+1
                while tid < len(self.file_list)-1:
                    if self.file_list[tid].get('isFWTestermessage') == False and self.file_list[tid].get('isTesterPkt') == True:
                            if all(rs not in self.file_list[tid].get('pktType') for rs in packets['CLK']['Response']):
                                self.timing_map[index]['Cloak'][clkseq]=[[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]]
                            else:
                                self.timing_map[index]['Cloak'][clkseq] = [[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[tid,self.file_list[tid].get('pktType'),self.file_list[tid].get('startTime'),self.file_list[tid].get('stopTime')]]
                            break
                    elif self.file_list[tid].get('isFWTestermessage') == False and self.file_list[tid].get('isTesterPkt') == False:
                        self.timing_map[index]['Cloak'][clkseq] =[[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]]
                        # print('Received Pkt instead of response')
                        break
                    tid+=1
                id=tid
                #find next clk flow
                #1.Find next PD
                PD = self.GetPacketDetails(packet='Ping Initiated',limit=[id,len(self.file_list)])
                if len(PD)>1:
                    #2.Get Cloak Packet
                    CLK = self.GetPacketDetails(packet='Cloak',limit=[PD[2],PD[2]+1])
                    if len(CLK)> 1:
                        id = CLK[2]
                    else:
                        print('CLK ILL')
                        #clk not received hence move all packets to the Illigal
                        id=PD[2]+1
                        while True:
                            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == True:
                                pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                                resp =None
                                tmpid = id+1
                                #check for response
                                while tmpid < len(self.file_list)-1:
                                    if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                        break
                                    elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                        resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                                    tmpid+=1
                                self.timing_map[index]['Illegal'].append([pkt,resp])
                            if any(rs in self.file_list[id].get('pktType') for rs in ['Test_Stop','Shutdown']): break
                            id+=1
                else:
                    id+=1
                    break
            else:id+=1
        print(self.timing_map[index])
    def RefCustomeLimitforPkt(self,pkt,index):
        sindex = None
        eindex = None
        reslimit = []
        if pkt['refCustom']['Type'] =='PktAFPeriod':
            #find packet
            expPkt = pkt['refCustom']['values']['Packet']
            phase = pkt['refCustom']['values']['phase']
            phstatus = 0
            limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            id = limit[0]
            while id < limit[1]:
                if phase == None:
                    phstatus =1
                else:
                    if phase == self.file_list[id].get('description'):phstatus=1
                if phstatus==1:
                    if expPkt[0] in self.file_list[id].get('pktType') and expPkt[1] in self.file_list[id].get('value') if expPkt[1] is not None else expPkt[0] in self.file_list[id].get('pktType'):
                        sindex = id
                        #find duration
                        maxtime = (self.file_list[id].get('stopTime')*1000)+pkt['refCustom']['values']['duration']
                        tid = id+1
                        while tid< limit[1]:
                            if (self.file_list[tid]['startTime']*1000) >= maxtime:
                                eindex = tid
                                break
                            tid+=1
                        break
                id+=1
        elif pkt['refCustom']['Type'] == 'PktWithCnt':
            expPkt = pkt['refCustom']['values']['Packet']
            Pktcnt = pkt['refCustom']['values']['Count']
            limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            id = limit[0]
            eindex=limit[1]
            strtpkt_status = 0
            while id < limit[1]:
                if expPkt[1] is not None:
                    if expPkt[0] in self.file_list[id].get('pktType') and expPkt[1] in self.file_list[id].get('value'): 
                        strtpkt_status=1
                        break
                else:
                    if expPkt[0] in self.file_list[id].get('pktType'):
                        strtpkt_status=1
                        break
                id+=1
            if strtpkt_status==1:
                pkt = pkt['packet']
                id2 = id
                cnt = 0
                while id2 < limit[1]:
                    if pkt[1] is not None:
                        if pkt[0] in self.file_list[id2].get('pktType') and pkt[1] in self.file_list[id2].get('value'): 
                            cnt+=1
                            if cnt == Pktcnt: break
                    else:
                        if pkt[0] in self.file_list[id2].get('pktType'):
                            cnt+=1
                            if cnt == Pktcnt: break
                    id2+=1
                eindex = id2+1
            sindex = id
        elif pkt['refCustom']['Type'] == "SoonAFPkt":
            expPkt = pkt['refCustom']['values']['Packet']
            limit = [self.timing_map[index]['General']['PD'][0],self.timing_map[index]['General']['SD'][0]]
            epkt = self.GetPacketDetails(packet=expPkt[0],limit=limit)
            if len(epkt)>1:
                sindex = epkt[2]
                #check that next is a packet
                id = sindex+1
                while id < limit[1]:
                    if self.file_list[id]['isTesterPkt'] == False and self.file_list[id]['isFWTestermessage'] == False:
                        eindex = id+1
                        break
                    id+=1
        if sindex != None:
            if eindex != None:
                return [sindex,eindex]
            else:
                return [sindex,limit[1]]
        else: return None  
    def EyeDigramCheck(self,AllOtherChecks,index):
        AllOtherChecks['Npass'] = None
        AllOtherChecks['Npass_exp'] = int(self.Json_TC['other_checks_details'][str(index)]['Npass']['expected'])
        AllOtherChecks['Npass_res'] = "Fail"

        AllOtherChecks['EyeDigramCheck']=[]
        AllOtherChecks['EyeDigramCheck_res']='Fail'
        Npass_Phase = 0
        Npass_magnitude = 0
        res = []
        check_res =[]
        EyEdigpath = None
        EyeResult={"Phase":{},"Magnitude":{}}
        Expvalue = self.Json_TC['other_checks_details'][str(index)]['EyeDigramCheck']
        AllOtherChecks['EyeDigramCheck_exp']=str(Expvalue)
        TCfolderList = self.TracePath.split("\\")
        path = "\\".join(TCfolderList[0:len(TCfolderList)-1])
        #Unzip Eyedig file
        for subdir, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.GrlEyeInfo'):
                    if os.path.exists(os.path.join(subdir,'EyeDebugInfo')):
                        EyEdigpath = os.path.join(subdir,'EyeDebugInfo')
                    else:
                        #Perform unzip
                        with zipfile.ZipFile(os.path.join(subdir,file), 'r') as zip_ref:
                            zip_ref.extractall(os.path.join(subdir,'EyeDebugInfo'))
                        EyEdigpath = os.path.join(subdir,'EyeDebugInfo')
        if EyEdigpath is not None:
            MagnitudeResultCSV = []
            PhaseResultCSV = []
            Temresult = {"Phase":{},"Magnitude":{}}
            for subdir, dirs, files in os.walk(path):
                for file in files:
                    if 'Eye_Magnitude_' in file and file.endswith("Results_EYE.csv"):
                        MagnitudeResultCSV.append(os.path.join(subdir,file))
                    if 'Eye_Phase' in file and file.endswith("Results_EYE.csv"):
                        PhaseResultCSV.append(os.path.join(subdir,file))
            if len(MagnitudeResultCSV) >0:
                for MagPath in MagnitudeResultCSV:
                    PktName = (MagPath.split("\\")[len(MagPath.split("\\"))-2]).split("_TS")[0]
                    Temresult["Magnitude"][PktName]={}
                    # reading the CSV file
                    data = open(MagPath)
                    csvFile = csv.reader(data)
                    #update csvdata to res
                    for lines in csvFile:
                        if len(lines)>0:
                            if 'AmplitudeHigh' in lines: Temresult["Magnitude"][PktName]['AmplitudeHigh'] = float(lines[1])
                            if 'AmplitudeLow' in lines: Temresult["Magnitude"][PktName]['AmplitudeLow'] = float(lines[1])
                            if 'SNR' in lines: Temresult["Magnitude"][PktName]['SNR'] = float(lines[1])
                            if 'Fclk' in lines: Temresult["Magnitude"][PktName]['Fclk'] = float(lines[1])
                            if 'HalfBitPeriod' in lines: Temresult["Magnitude"][PktName]['HalfBitPeriod'] = float(lines[1])
                            if 'EyeWidth' in lines: Temresult["Magnitude"][PktName]['EyeWidth'] = float(lines[1])
            if len(PhaseResultCSV) >0:
                for MagPath in PhaseResultCSV:
                    PktName = (MagPath.split("\\")[len(MagPath.split("\\"))-2]).split("_TS")[0]
                    Temresult['Phase'][PktName]={}
                    # reading the CSV file
                    data = open(MagPath)
                    csvFile = csv.reader(data)
                    #update csvdata to res
                    for lines in csvFile:
                        if len(lines)>0:
                            if 'AmplitudeHigh' in lines: Temresult['Phase'][PktName]['AmplitudeHigh'] = float(lines[1])
                            if 'AmplitudeLow' in lines: Temresult['Phase'][PktName]['AmplitudeLow'] = float(lines[1])
                            if 'SNR' in lines: Temresult['Phase'][PktName]['SNR'] = float(lines[1])
                            if 'Fclk' in lines: Temresult['Phase'][PktName]['Fclk'] = float(lines[1])
                            if 'HalfBitPeriod' in lines: Temresult['Phase'][PktName]['HalfBitPeriod'] = float(lines[1])
                            if 'EyeWidth' in lines: Temresult['Phase'][PktName]['EyeWidth'] = float(lines[1])
            if len(Temresult['Magnitude'])>0:
                try:
                    for pkts in Temresult['Magnitude']:
                        Ampdiff = round((Temresult['Magnitude'][pkts]['AmplitudeHigh']-Temresult['Magnitude'][pkts]['AmplitudeLow'])*1000,2)
                        EyeResult['Magnitude'][pkts]={}
                        EyeResult['Magnitude'][pkts]['Amplitude Diff'] = f"{Ampdiff}|>={Expvalue['Magnitude']['AmplitudeDiff'][0]}|Pass" if Ampdiff >= Expvalue['Magnitude']['AmplitudeDiff'][0] else f"{Ampdiff}|>={Expvalue['Magnitude']['AmplitudeDiff'][0]}|Fail"
                        EyeResult['Magnitude'][pkts]['SNR'] = f"{Temresult['Magnitude'][pkts]['SNR']}|>={Expvalue['Magnitude']['SNR'][0]}|Pass" if Temresult['Magnitude'][pkts]['SNR'] >= Expvalue['Magnitude']['SNR'][0] else f"{Temresult['Magnitude'][pkts]['SNR']}|>={Expvalue['Magnitude']['SNR'][0]}|Fail"
                        EyeResult['Magnitude'][pkts]['Fclk'] = f"{Temresult['Magnitude'][pkts]['Fclk']}|{Expvalue['Magnitude']['Fclk'][0]}-{Expvalue['Magnitude']['Fclk'][1]}|Pass" if Temresult['Magnitude'][pkts]['Fclk'] >= Expvalue['Magnitude']['Fclk'][0] and Temresult['Magnitude'][pkts]['Fclk'] <= Expvalue['Magnitude']['Fclk'][1] else f"{Temresult['Magnitude'][pkts]['Fclk']}|{Expvalue['Magnitude']['Fclk'][0]}-{Expvalue['Magnitude']['Fclk'][1]}|Fail"
                        EyeResult['Magnitude'][pkts]['HalfBitPeriod'] = f"{Temresult['Magnitude'][pkts]['HalfBitPeriod']}|{Expvalue['Magnitude']['HalfBitPeriod'][0]}-{Expvalue['Magnitude']['HalfBitPeriod'][1]}|Pass" if Temresult['Magnitude'][pkts]['HalfBitPeriod'] >= Expvalue['Magnitude']['HalfBitPeriod'][0] and Temresult['Magnitude'][pkts]['HalfBitPeriod'] <= Expvalue['Magnitude']['HalfBitPeriod'][1] else f"{Temresult['Magnitude'][pkts]['HalfBitPeriod']}|{Expvalue['Magnitude']['HalfBitPeriod'][0]}-{Expvalue['Magnitude']['HalfBitPeriod'][1]}|Fail"
                        EyeResult['Magnitude'][pkts]['EyeWidth'] = f"{Temresult['Magnitude'][pkts]['EyeWidth']}|>={Expvalue['Magnitude']['EyeWidth'][0]}|Pass" if Temresult['Magnitude'][pkts]['EyeWidth'] >= Expvalue['Magnitude']['EyeWidth'][0] else f"{Temresult['Magnitude'][pkts]['EyeWidth']}|>={Expvalue['Magnitude']['EyeWidth'][0]}|Fail"
                except Exception as e:
                    pass 
            if len(Temresult['Phase'])>0:
                try:
                    for pkts in Temresult['Phase']:
                        Ampdiff = round((Temresult['Phase'][pkts]['AmplitudeHigh']-Temresult['Phase'][pkts]['AmplitudeLow'])*1000,2)
                        EyeResult['Phase'][pkts]={}
                        EyeResult['Phase'][pkts]['Amplitude Diff'] = f"{Ampdiff}|>={Expvalue['Phase']['AmplitudeDiff'][0]}|Pass" if Ampdiff >= Expvalue['Phase']['AmplitudeDiff'][0] else f"{Ampdiff}|>={Expvalue['Phase']['AmplitudeDiff'][0]}|Fail"
                        EyeResult['Phase'][pkts]['SNR'] = f"{Temresult['Phase'][pkts]['SNR']}|>={Expvalue['Phase']['SNR'][0]}|Pass" if Temresult['Phase'][pkts]['SNR'] >= Expvalue['Phase']['SNR'][0] else f"{Temresult['Phase'][pkts]['SNR']}|>={Expvalue['Phase']['SNR'][0]}|Fail"
                        EyeResult['Phase'][pkts]['Fclk'] = f"{Temresult['Phase'][pkts]['Fclk']}|{Expvalue['Phase']['Fclk'][0]}-{Expvalue['Phase']['Fclk'][1]}|Pass" if Temresult['Phase'][pkts]['Fclk'] >= Expvalue['Phase']['Fclk'][0] and Temresult['Phase'][pkts]['Fclk'] <= Expvalue['Phase']['Fclk'][1] else f"{Temresult['Phase'][pkts]['Fclk']}|{Expvalue['Phase']['Fclk'][0]}-{Expvalue['Phase']['Fclk'][1]}|Fail"
                        EyeResult['Phase'][pkts]['HalfBitPeriod'] = f"{Temresult['Phase'][pkts]['HalfBitPeriod']}|{Expvalue['Phase']['HalfBitPeriod'][0]}-{Expvalue['Phase']['HalfBitPeriod'][1]}|Pass" if Temresult['Phase'][pkts]['HalfBitPeriod'] >= Expvalue['Phase']['HalfBitPeriod'][0] and Temresult['Phase'][pkts]['HalfBitPeriod'] <= Expvalue['Phase']['HalfBitPeriod'][1] else f"{Temresult['Phase'][pkts]['HalfBitPeriod']}|{Expvalue['Phase']['HalfBitPeriod'][0]}-{Expvalue['Phase']['HalfBitPeriod'][1]}|Fail"
                        EyeResult['Phase'][pkts]['EyeWidth'] = f"{Temresult['Phase'][pkts]['EyeWidth']}|>={Expvalue['Phase']['EyeWidth'][0]}|Pass" if Temresult['Phase'][pkts]['EyeWidth'] >= Expvalue['Phase']['EyeWidth'][0] else f"{Temresult['Phase'][pkts]['EyeWidth']}|>={Expvalue['Phase']['EyeWidth'][0]}|Fail"
                except Exception as e:
                    pass 
        resindx = -1
        for root in EyeResult:
            for Pkt in EyeResult[root]:
                resindx+=1
                res.append(Pkt+'_'+root+':'+EyeResult[root][Pkt]['Amplitude Diff']+','+EyeResult[root][Pkt]['SNR']+','+EyeResult[root][Pkt]['Fclk']+','+EyeResult[root][Pkt]['HalfBitPeriod']+','+EyeResult[root][Pkt]['EyeWidth'])
                if 'Fail' in res[resindx]: check_res.append("Fail")
                if root == 'Phase':
                    if 'Fail' not in res[resindx]: Npass_Phase+=1
                if root == 'Magnitude':
                    if 'Fail' not in res[resindx]: Npass_magnitude+=1 
        AllOtherChecks['EyeDigramCheck'] = ';'.join(res)
        AllOtherChecks['EyeDigramCheck_res'] = 'Fail' if len(check_res)>0 and len(res)>0 else 'Pass'
        AllOtherChecks['Npass'] = f"Npass_Phase: {Npass_Phase}, Npass_magnitude: {Npass_magnitude}"
        if (Npass_Phase+Npass_magnitude) >= AllOtherChecks['Npass_exp']:AllOtherChecks['Npass_res'] ='Pass'






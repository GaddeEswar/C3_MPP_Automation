# Add 'return res' manually at end of each function if missing
#get first initial voltage after the stabilization
def GetInitailVoltage(self,index,limit):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    self.initialVoltage = None
    self.stability = None
    
    limit = limit
    # print("limit:",limit)
    # limit = flows[index]['Limit']
    id = limit[0]
    while id < limit[1]:
        if 'MPP_XCEV_Ideal' in self.file_list[id]['pktType']:
            # print(id)
            revid = id
            while revid > limit[0]:
                if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                    self.stability=revid
                    # print('stability:',self.stability)
                    #GetIntital Voltage
                    # # print(self.Json_TC['other_checks_details'])
                    # if 'InitialVoltage' in self.Json_TC['other_checks_details'][str(index)]:
                    res = self.PktMethod.CalculateVoltTwindow(revid,self.AllChannelData)
                    self.initialVoltage =  res[0]
                    return [self.initialVoltage,revid]
                    # # print('stability',self.stability,self.initialVoltage)
                    
                revid-=1
            break
        id+=1
    return None
    
def PacketCheck_New(self,Flow_limit,Check):
    SubChecks = []
    expvalues=[]
    # print("PKTSck")
    for pkt in Check['ChecksList']:
        expval = ""
        Pktcount = 0
        limit=Flow_limit
        if 'PktLimit' in pkt:
            limit = self.PktMethod.GetLimits(pkt['PktLimit'],pkt,Flow_limit)
        # # print("limit:",limit)
        ExpPacket = pkt['packet'] if pkt['packet'][1] is not None else [pkt['packet'][0]]
        expval=expval+f"{'_'.join(ExpPacket)}:"
        if 'Pkt_response' in pkt : 
            if 'Pkt_response_Reverse' in pkt:
                if pkt['Pkt_response_Reverse'] == True:
                    expval=expval+f"Response not in {','.join(pkt['Pkt_response'])}"
                else:expval=expval+f"Response in {','.join(pkt['Pkt_response'])}"
            else:expval=expval+f"Response in {','.join(pkt['Pkt_response'])}"
        if 'Pkt_count' in pkt : expval=expval+f"Pacekt Count= {pkt['Pkt_count']}"
        if limit != None:
            SubChecks.append([f"Packet check for {'_'.join(ExpPacket)} initiated on limit {round(self.file_list[limit[0]]['startTime'],2)}Sec to {round(self.file_list[limit[1]]['startTime'],2)}Sec","Pass"])
            #Iterate on limit and get the matching packets
            id = limit[0]
            while id<=limit[1]:
                # if self.PktMethod.GetPacketType(id) =="Packet":
                #check for the phase
                if pkt['phase'] in self.file_list[id]['description']:
                    if ExpPacket[0].lower() in self.file_list[id]['pktType'].lower() and  ExpPacket[1].lower() in self.file_list[id]['value'].lower() if len(ExpPacket)==2 else ExpPacket[0].lower() in self.file_list[id]['pktType'].lower():
                        #check for the packet type
                        if self.PktMethod.GetPacketType(id) == pkt['PktType'] if 'PktType' in pkt else "Packet":
                            Pktcount+=1
                            # SubChecks.append([f"{ExpPacket[0]} Packet found at {round(self.file_list[id]['startTime'],2)}Sec","Pass"])
                            SubChecks.append([f"{self.file_list[id]['pktType']} {self.file_list[id]['value']} Packet found at {round(self.file_list[id]['startTime'],2)}Sec","Pass"])
                            #Apply additional checks for the packet
                            #############################################################
                            if 'Pkt_response' in pkt:
                                Pktresp = self.PktMethod.GetPacketResponse2(id,[id+1,limit[1]])
                                if Pktresp is not None:
                                    if 'Pkt_response_Reverse' in pkt:
                                        if pkt['Pkt_response_Reverse']==True:
                                            if any(res in self.file_list[Pktresp]['pktType'] for res in pkt['Pkt_response']):
                                                SubChecks.append([f"found response {self.file_list[Pktresp]['pktType']}_{self.file_list[Pktresp]['value']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which is not expected amoung {','.join(pkt['Pkt_response'])}","Fail"])
                                            else:SubChecks.append([f"found response {self.file_list[Pktresp]['pktType']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which is not expected amoung {','.join(pkt['Pkt_response'])}","Pass"])
                                    else:
                                        if any(res in self.file_list[Pktresp]['pktType'] for res in pkt['Pkt_response']):
                                            SubChecks.append([f"found response {self.file_list[Pktresp]['pktType']}_{self.file_list[Pktresp]['value']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which is expected amoung {','.join(pkt['Pkt_response'])}","Pass"])
                                        else:SubChecks.append([f"found response {self.file_list[Pktresp]['pktType']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which not is expected amoung {','.join(pkt['Pkt_response'])}","Fail"])
                                else:SubChecks.append([f"Response not found for received packet.","Fail"])
                                if not pkt.get('Pkt_count'):
                                    break
                                # tmpid = id+1
                                # RespFlag = False
                                # while tmpid < limit[1]:
                                #     if self.PktMethod.GetPacketType(tmpid) =="Response":
                                #         if any(res in self.file_list[tmpid]['pktType'] for res in pkt['Pkt_response']):
                                #             RespFlag=True
                                #             SubChecks.append([f"found response {self.file_list[tmpid]['pktType']} at {round(self.file_list[tmpid]['startTime'],2)}sec, Which is expected amoung {','.join(pkt['Pkt_response'])}","Pass"])
                                #         else: SubChecks.append([f"found response {self.file_list[tmpid]['pktType']} at {round(self.file_list[tmpid]['startTime'],2)}sec, Which is not expected amoung {','.join(pkt['Pkt_response'])}","Fail"])
                                #     elif self.PktMethod.GetPacketType(tmpid) =="Packet":break
                                #     tmpid+=1
                                # if RespFlag == False:SubChecks.append([f"Response not found for received for the packet.","Fail"])
                                ############################################################
                            elif not pkt.get('Pkt_count'):break
                id+=1
        else:SubChecks.append([f"Packet check for {'_'.join(ExpPacket)} not initiated, limit not found","Fail"])
        if Pktcount !=0:
            #check for pacekt count
            if 'Pkt_count' in pkt:
                if Pktcount >= pkt['Pkt_count']:
                    SubChecks.append([f"The received pacekt count is {Pktcount},Which is >= of expected count of {pkt['Pkt_count']}","Pass"])
                else:SubChecks.append([f"The received pacekt count is {Pktcount},Which is not expected count of {pkt['Pkt_count']}","Fail"])
        else:SubChecks.append([f"{ExpPacket[0]} Packet not found","Fail"])
        expvalues.append(expval)
    AllMeasures['PacketCheck_exp'] = ';'.join(expvalues)
    AllMeasures['PacketCheck'] = 'Found Issues' if any(res[1]=="Fail" for res in SubChecks) else 'No Issues'
    AllMeasures['PacketCheck_res'] = 'Fail' if any(res[1]=="Fail" for res in SubChecks) else 'Pass'
    AllMeasures['PacketCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
    AllMeasures['PacketCheck_Details']=SubChecks

def BitsCheck_New(self,Flow_limit,Check):
    # print("BITSck")
    # # print(Flow_limit)
    SubChecks=[]
    expvalues=[]
    
    for BITSck in Check['ChecksList']:
        PktCount = 0
        # # print(BITSck)
        limit = Flow_limit
        if 'PktLimit' in  BITSck:
            limit=self.PktMethod.GetLimits(BITSck['PktLimit'],BITSck,Flow_limit)
        ExpPacket = BITSck['packet'] if BITSck['packet'][1] is not None else [BITSck['packet'][0]]
        expvalue=f"{'_'.join(ExpPacket)}"
        comp = None
        for ck in BITSck['Checks']:
            if BITSck['Checks'][ck]['comp']=="str":
                expvalue=expvalue+f":{ck}={BITSck['Checks'][ck]['expected']}"
            elif BITSck['Checks'][ck]['comp']=="str_Reverse":
                expvalue=expvalue+f":{ck} Not {BITSck['Checks'][ck]['expected']}"
            elif BITSck['Checks'][ck]['comp']=="btw":
                expvalue=expvalue+f":{ck} between {'-'.join(map(str,BITSck['Checks'][ck]['expected']))}"
            elif BITSck['Checks'][ck]['comp']=="Present":
                expvalue=expvalue+f":{ck} should available"
            else:
                if BITSck['Checks'][ck]['comp'] == "GTEQL": comp = ">="
                if BITSck['Checks'][ck]['comp'] == "LTEQL": comp = "<="
                if BITSck['Checks'][ck]['comp'] == "EQL": comp = "=="
                expvalue=expvalue+f":{ck} {comp} {BITSck['Checks'][ck]['expected']}"
        PktType = BITSck['PacketType'] if 'PacketType' in BITSck else 'Packet'
        #check for multiple packet or signle packet based on the requirement
        # print('bitsLimit',limit)
        tmpID = limit[0]
        while tmpID < limit[1]:
            PktFlag = False
            pktres = self.PktMethod.GetPacketDetails(packet=BITSck['packet'][0],value=BITSck['packet'][1],limit=[tmpID,limit[1]],Type=PktType)
            # print("pktres:",pktres)
            if len(pktres)>2:
                #check for packet phase
                if 'phase' in BITSck:
                    if BITSck['phase'] in self.file_list[pktres[2]]['description']:PktFlag=True
                else:PktFlag=True
                if PktFlag==True:
                    PktCount+=1
                    #count check    
                    SubChecks.append([f"The expected packet {self.file_list[pktres[2]]['pktType']}_{self.file_list[pktres[2]]['value']} found at {round(pktres[0],3)}sec","Pass"]) # SubChecks.append([f"The expected packet {'_'.join(ExpPacket)} found at {round(pktres[0],3)}sec","Pass"])
                    #Get the payload values results
                    for ck in BITSck['Checks']:
                        # # print(ck)
                        #get the payload details
                        payloadDetails = self.PktMethod.GetPayloadDetails(pktres[2],ck)
                        # # print(payloadDetails)
                        if len(payloadDetails)>0:
                            # print("payloadDetails:",payloadDetails)
                            for pyload in payloadDetails:
                                if BITSck['Checks'][ck]['comp']=="str":
                                    if BITSck['Checks'][ck]['expected'] in pyload[BITSck['Checks'][ck]['flag']]:
                                        SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as expected value of {BITSck['Checks'][ck]['expected']}","Pass"])
                                    elif 'random' in BITSck['Checks'][ck]['expected']:
                                        if BITSck['Checks'][ck].get('except'):
                                            if pyload[BITSck['Checks'][ck]['flag']] not in BITSck['Checks'][ck]['except']:
                                                SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}","Pass"])
                                            else: SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}","Fail"])
                                        else: SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random value","Pass"])
                                    else:SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} is not expected value of {BITSck['Checks'][ck]['expected']}","Fail"])
                                elif BITSck['Checks'][ck]['comp']=="str_Reverse":
                                    if BITSck['Checks'][ck]['expected'] in pyload[BITSck['Checks'][ck]['flag']]:
                                        SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as expected value of {BITSck['Checks'][ck]['expected']}","Fail"])
                                    else:SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} is not expected value of {BITSck['Checks'][ck]['expected']}","Pass"])
                                elif BITSck['Checks'][ck]['comp']=="btw":
                                    # # print(int(pyload[BITSck['Checks'][ck]['flag']]),BITSck['Checks'][ck]['expected'])
                                    if int(pyload[BITSck['Checks'][ck]['flag']]) >= BITSck['Checks'][ck]['expected'][0] and int(pyload[BITSck['Checks'][ck]['flag']]) <= BITSck['Checks'][ck]['expected'][1]:
                                        SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as expected value in limit of  {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}","Pass"])
                                    else:SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as not expected value in limit of  {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}","Fail"])
                                elif BITSck['Checks'][ck]['comp'] == "NEQL":
                                    if BITSck['Checks'][ck]['expected'] not in pyload[BITSck['Checks'][ck]['flag']]:
                                        SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} not equal to {BITSck['Checks'][ck]['expected']}, Expected: !={BITSck['Checks'][ck]['expected']}","Pass"])
                                    else: SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} equal to {BITSck['Checks'][ck]['expected']}, Expected: !={BITSck['Checks'][ck]['expected']}","Fail"])

                                elif BITSck['Checks'][ck]['comp']=="Present":
                                    SubChecks.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}","Pass"])
                                else:
                                    if ':' in pyload[BITSck['Checks'][ck]['flag']]:
                                        pyaloadli = pyload[BITSck['Checks'][ck]['flag']].split(':')
                                        # print("pyaloadli:",pyaloadli)
                                        payloadActual = '_'.join(pyaloadli[1:])
                                    else:payloadActual=pyload[BITSck['Checks'][ck]['flag']]
                                    revdval = GeneralMethods.GetFloatFromStr(payloadActual)
                                    # print("revdval:",revdval)
                                    if BITSck['Checks'][ck]['comp'] == 'GTEQL':
                                        if  revdval[0] >= float(BITSck['Checks'][ck]['expected']):
                                            SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is >={BITSck['Checks'][ck]['expected']}","Pass"])
                                        else:SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is not >={BITSck['Checks'][ck]['expected']}","Fail"])
                                    elif BITSck['Checks'][ck]['comp'] == 'LTEQL':
                                        if  revdval[0] <= float(BITSck['Checks'][ck]['expected']):
                                            SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is <={BITSck['Checks'][ck]['expected']}","Pass"])
                                        else:SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is not <={BITSck['Checks'][ck]['expected']}","Fail"])
                                    elif BITSck['Checks'][ck]['comp'] == 'EQL':
                                        if  revdval[0] == float(BITSck['Checks'][ck]['expected']):
                                            SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is =={BITSck['Checks'][ck]['expected']}","Pass"])
                                        else:SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is not =={BITSck['Checks'][ck]['expected']}","Fail"])
                        else:SubChecks.append([f"The payload {ck} for packet {'_'.join(ExpPacket)} not found for the packet {'_'.join(ExpPacket)}","Fail"])
                if 'PacketCount' not in BITSck:
                    break
                if 'PacketCount' in BITSck:
                    if BITSck['PacketCount']==PktCount:break
                tmpID = pktres[2]+1
            else:
                if 'PacketCount' in BITSck:
                    if PktCount < BITSck['PacketCount']:
                        SubChecks.append([f"Out of {BITSck['PacketCount']} Received only {PktCount} {'_'.join(ExpPacket)} packets","Fail"])
                else:
                    if PktCount==0:
                        SubChecks.append([f"The expected packet {'_'.join(ExpPacket)} not found between {round(self.file_list[limit[0]]['startTime'],3)}sec to {round(self.file_list[limit[1]]['stopTime'],3)}sec ","Fail"])
                break
        expvalues.append(expvalue)
    # AllMeasures['BitsCheck_exp'] = ';'.join(expvalues)
    # AllMeasures['BitsCheck'] = 'Found Issues' if any(res[1]=="Fail" for res in SubChecks) else 'No Issues'
    # AllMeasures['BitsCheck_res'] = 'Fail' if any(res[1]=="Fail" for res in SubChecks) else 'Pass'
    # AllMeasures['BitsCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
    # AllMeasures['BitsCheck_Details']=SubChecks
    # print("SubChecks:",SubChecks)
    return SubChecks
def EyeTestFetchDataFromCSV(self,check):
    res = []
    try:
        Ntotal = 0
        Npass = 0
        # Npass_meg = 0
        # Npass_pha = 0
        ExtractedFiles=None
        #After Stabilization find the XCE and PLA packets, fetch the corresponding values from the CSV files extracted from the EyeDebugInfo.GrlEyeInfo
        #1. Extract EyeDebugInfo.GrlEyeInfo file 
        PathList = self.Header['CapturePath'].split('\\')
        EyeInfoPath = CommonMethods.find_file('/'.join(PathList[0:len(PathList)-1]),'EyeDebugInfo.GrlEyeInfo')
        if EyeInfoPath is not None:
            if any (res in ["Extended Control Error"] for res in check['Packets']):
                RangeLimit = [1,check['Range']] if 'Range' in check else [1,1]
                rid = RangeLimit[0]
                TempLimit = Flow_limit
                while rid <= RangeLimit[1]:
                    # ExtractedFiles = CommonMethods.extract_zip_in_memory(EyeInfoPath)
                    #2.Get XCE and PLA packets after Stabilization find for 2 range
                    # print(TempLimit)
                    Stb_Pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCE_Stabilized",limit=TempLimit,Type="TesterMsg")
                    # # print(Stb_Pkt)
                    if len(Stb_Pkt)>2:
                        res.append([f"Stabilization {rid} found at:{round(Stb_Pkt[0],3)}sec","Pass"])
                        #Get XCE packets___________________________________________________________________________________________________________________
                        id = Stb_Pkt[2]
                        while id < Flow_limit[1]:
                            CEPkt = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[id,TempLimit[1]],Type="Response")
                            if len(CEPkt)>2:
                                #Get packets for 5sec
                                if CEPkt[0] - Stb_Pkt[1] >= 5: break
                                Ntotal+=1
                                Npass_meg = 0
                                Npass_pha = 0
                                for PktType in ['Magnitude','Phase']:
                                    df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'XCE',str(CEPkt[2]),'Results'])
                                    # # print(df)
                                    if df is not None:
                                        ckres = []
                                        #Find each checks
                                        for chk in check['Checks'][PktType]:
                                            if 'EyeAmplitude' in chk:
                                                AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                                AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                            elif 'SNR' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                            elif 'Fclk' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                            elif 'HalfBitPeriod' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                            elif 'EyeWidth' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                        #Update result for Packet
                                        subcheckres = 'Fail' if any(res[1]=='Fail' for res in ckres) else 'Pass'
                                        if PktType == "Magnitude" and subcheckres=="Pass": Npass_meg+=1
                                        if PktType == "Phase" and subcheckres=="Pass": Npass_pha+=1
                                        res.append([f"{PktType} Extended_Control_Error at index:{CEPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                                    else: res.append([f"CSV file not found for the {PktType} packet Extended_Control_Error at {CEPkt[2]}","Fail"])
                                if Npass_meg == 1 or Npass_pha == 1: Npass+=1
                            else:break
                            id = CEPkt[2]+1
                        #Get PLA packets___________________________________________________________________________________________________________________
                        id = Stb_Pkt[2]
                        while id < Flow_limit[1]:
                            CEPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,TempLimit[1]],Type="Response")
                            if len(CEPkt)>2:
                                #Get packets for 5sec
                                if CEPkt[0] - Stb_Pkt[1] >= 5:break
                                Ntotal+=1
                                Npass_meg = 0
                                Npass_pha = 0
                                for PktType in ['Magnitude','Phase']:
                                    df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'PLA_2',str(CEPkt[2]),'Results'])
                                    # # print(df)
                                    if df is not None:
                                        ckres = []
                                        #Find each checks
                                        for chk in check['Checks'][PktType]:
                                            if 'EyeAmplitude' in chk:
                                                AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                                AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                            elif 'SNR' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                            elif 'Fclk' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                            elif 'HalfBitPeriod' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                            elif 'EyeWidth' in chk:
                                                result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                                ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                        #Update result for Packet
                                        # # print(ckres)
                                        subcheckres = 'Fail' if any(res[1]=='Fail' for res in ckres) else 'Pass'
                                        if PktType == "Magnitude" and subcheckres=="Pass": Npass_meg+=1
                                        if PktType == "Phase" and subcheckres=="Pass": Npass_pha+=1
                                        res.append([f"{PktType} PLA_2 at index:{CEPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                                    else: res.append([f"CSV file not found for the {PktType} packet PLA_2 at {CEPkt[2]}","Fail"])
                                if Npass_meg==1 or Npass_pha == 1: Npass+=1
                            else:break
                            id = CEPkt[2]+1
                        TempLimit = [Stb_Pkt[2]+1,Flow_limit[1]]
                    else:res.append([f"Stabilization {rid} not found","Fail"])
                    rid+=1
                # print(res)
                if Npass !=0 and Ntotal !=0:
                    if (Npass/(Ntotal/100))>=95:
                        res.append([f"Caluclated Npass {Npass} and Received Ntotal {Ntotal}: Pass Percentage:{round((Npass/(Ntotal/100)),3)}%","Pass"])
                    else:res.append([f"Caluclated Npass {Npass} and Received Ntotal {Ntotal}: Pass Percentage:{round((Npass/(Ntotal/100)),3)}%","Fail"])
                else:res.append([f"No packets received to calculate Npass","Fail"])
            else:
                if "MPP_Extended_Identification" in check["Packets"]:
                    Ntotal+=1
                    XIDPkt = self.PktMethod.GetPacketDetails(packet="MPP_Extended_Identification",limit=Flow_limit,Type="Response")
                    if len(XIDPkt)>2:
                        Npass_meg = 0
                        Npass_pha = 0
                        for PktType in ['Magnitude','Phase']:
                            df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'XID',str(XIDPkt[2]),'Results'])
                            if df is not None:
                                ckres = []
                                #Find each checks
                                for chk in check['Checks'][PktType]:
                                    if 'EyeAmplitude' in chk:
                                        AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                        AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                    elif 'SNR' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                    elif 'Fclk' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                    elif 'HalfBitPeriod' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                    elif 'EyeWidth' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                #Update result for Packet
                                subcheckres = 'Fail' if any(res[1]=='Fail' for res in ckres) else 'Pass'
                                if PktType == "Magnitude" and subcheckres=="Pass": Npass_meg+=1
                                if PktType == "Phase" and subcheckres=="Pass": Npass_pha+=1
                                res.append([f"{PktType} Extended Identification at index:{XIDPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                            else: res.append([f"CSV file not found for the {PktType} packet Extended Identification at {XIDPkt[2]}","Fail"])
                        if Npass_meg==1 or Npass_meg==1 :Npass+=1
                    else:res.append([f"Extended Identification not found","Fail"])
                if "Configuration" in check["Packets"]:
                    Ntotal+=1
                    CNFPkt = self.PktMethod.GetPacketDetails(packet="Configuration",limit=Flow_limit,Type="Response")
                    if len(CNFPkt)>2:
                        Npass_meg = 0
                        Npass_pha = 0
                        for PktType in ['Magnitude','Phase']:
                            df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'CFG',str(CNFPkt[2]),'Results'])
                            # df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'CFG',"_",'Results'])
                            if df is not None:
                                ckres = []
                                #Find each checks
                                for chk in check['Checks'][PktType]:
                                    if 'EyeAmplitude' in chk:
                                        AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                        AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                    elif 'SNR' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                    elif 'Fclk' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                    elif 'HalfBitPeriod' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                    elif 'EyeWidth' in chk:
                                        result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                        ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                #Update result for Packet
                                subcheckres = 'Fail' if any(res[1]=='Fail' for res in ckres) else 'Pass'
                                if PktType == "Magnitude" and subcheckres=="Pass": Npass_meg+=1
                                if PktType == "Phase" and subcheckres=="Pass": Npass_pha+=1
                                res.append([f"{PktType} Configuration at index:{CNFPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                            else: res.append([f"CSV file not found for the {PktType} packet Configuration at {CNFPkt[2]}","Fail"])
                        if Npass_meg==1 or Npass_meg==1 :Npass+=1
                    else:res.append([f"Configuration not found","Fail"])
                else:res.append([f"The File EyeDebugInfo.GrlEyeInfo file not found in Trace path :{'/'.join(PathList[0:len(PathList)-1])}","Fail"])
                if Npass == 2:
                    res.append([f"Caluclated Npass {Npass}","Pass"])
                else:res.append([f"Caluclated Npass {Npass}","Fail"])
        # # print(res)
        return res 
    except Exception as e:
        traceback.print_exc()
        res.append([f"Exception:{str(e)}","Fail"])
def PrectVrectRamp(self,Flow_limit,Check):
    res = []
    if 'NPM' in self.Header['TestcaseName']:
        TypeSD = "NPM"
        TyepDscr = "Nominal_Power_Mode"
    elif 'LPM' in self.Header['TestcaseName']:
        TypeSD = "LPM"
        TyepDscr = "Low_Power_Mode"
    elif 'HPM' in self.Header['TestcaseName']:
        TypeSD = "HPM"
        TyepDscr = "High_Power_Mode"
    elif 'CPM' in self.Header['TestcaseName']:
        TypeSD = "CPM"
        TyepDscr = "Continuous_Power_Mode"
    #1. Find the MODEXCAP packet
    TempPkt1 = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
    if len(TempPkt1)>2:
        # # print(TypeSD,TyepDscr)
        TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref0")[0]['sDescription']
        if ':' in TempVal:TempVal = TempVal.split(':')[1]
        Vrect_target = {'LPM':12.5,'NPM':12.5,'CPM':12.5,'HPM':18}
        # ref0 = GeneralMethods.GetFloatFromStr(TempVal)[0]
        ref2 = Vrect_target[TypeSD]
        if '_CAP_360.LPM' in self.Header['TestcaseName']: ref2 = 9.6
        
        TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref1")[0]['sDescription']
        if ':' in TempVal:TempVal = TempVal.split(':')[1]
        ref1 = GeneralMethods.GetFloatFromStr(TempVal)[0]
        
        TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],TyepDscr)[0]['sDescription']
        if ':' in TempVal:TempVal = TempVal.split(':')[1]
        Pwr = GeneralMethods.GetFloatFromStr(TempVal)[0]
        # if '_P3' in self.Header['TestcaseName']: MaxW=15 if MaxW>15 else MaxW
        # if '_P4' in self.Header['TestcaseName']: MaxW=5 if MaxW>5 else MaxW
        # print("Header['TestcaseName']:",self.Header['TestcaseName'])
        if '.P3' in self.Header['TestcaseName']: Pwr = min(Pwr,15)
        if '.P4' in self.Header['TestcaseName']: Pwr = min(Pwr,5)
        # print("MinW:",Pwr)
        res.append([f"Found MODEXCAP at {round(TempPkt1[0],3)}sec, with {TypeSD} Voltage Ref1: {ref1} V and {TypeSD} Potential load power: {Pwr} W","Pass"])
        #Condition 1
        #2. Set Prect and Vrect targets
        cnt = 0
        # Conditions = [{"TPrect":1,"TVrect":ref0},{"TPrect":MaxW,"TVrect":ref1}]
        Conditions = [{"TPrect":Pwr,"TVrect":ref1},{"TPrect":1,"TVrect":ref2}]
        # print("Conditions:",Conditions)
        for cond in Conditions:
            cnt+=1
            TPrect = cond['TPrect']
            TVrect = cond['TVrect']
            res.append([f"Condition {cnt}: Prect Target{cnt} set to {TPrect}W and Vrect Target{cnt} set to {TVrect}V","Pass"])
            #Find Load
            TempPkt2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(TPrect*1000)}mW",limit=[Flow_limit[1],TempPkt1[2]],Type="TesterMsg")
            if len(TempPkt2)>2:
                res.append([f"Set_Load {int(TPrect*1000)}mW packet found at {round(TempPkt2[0],3)}sec","Pass"])
                #3.Get Stablization
                TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Flow_limit[1]],Type="TesterMsg")
                if len(TempPkt3)>2:
                    res.append([f"Stablization found at {round(TempPkt3[0],3)}sec","Pass"])
                    #get for next set load or consider the end
                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="Set_Load",limit=[TempPkt3[2],Flow_limit[1]],Type="TesterMsg")
                    PLAlimit = TempPkt4[2] if len(TempPkt4)>2 else Flow_limit[1]
                    #Get PLA2 packets for 1 mins
                    id = TempPkt3[2]
                    PrectLi = []
                    VrectLi = []
                    while id < PLAlimit:
                        TempPkt5 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,PLAlimit])
                        if len(TempPkt5)>2:
                            if (TempPkt5[0] - TempPkt3[0]) >= 60: break
                            Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt5[2],"PRECT")[0]['sDescription'])[0]
                            Vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt5[2],"VRECT")[0]['sDescription'])[0]
                            res.append([f"Found PLA_2 packet at {round(TempPkt5[0],3)}sec with Prect: {Prect} W and Vrect: {Vrect} V","Pass"])
                            PrectLi.append(Prect)
                            VrectLi.append(Vrect)
                            id=TempPkt5[2]+1
                        else:break
                    if id == PLAlimit:res.append([f"No PLA_2 found between {round(TempPkt3[0],3)}sec - {round(TempPkt4[1],3)}sec"])
                    #Find the average Vrect and Prect
                    if len(VrectLi)>2:
                        results = CommonMethods.check_measure(obsr_val=sum(VrectLi)/len(VrectLi),exp_val=[round((TVrect-0.25),3),round((TVrect+0.25),3)],comp=0)
                        res.append([f"The calculated average Vrect{cnt} : {round(results[3],3)} V, Limit: {results[2]} V",results[1]])
                        # results = CommonMethods.check_measure(obsr_val=sum(VrectLi)/len(VrectLi),exp_val=[round((TVrect/100)*95,3),round((TVrect/100)*105,3)])
                        # res.append([f"The calculated average Vrect : {round(results[3],3)}V, Limit +/-5% of Target Vrect {TVrect}V i.e {results[2]}V",results[1]])

                    if len(PrectLi)>0:
                        if cnt == 2:
                            results = CommonMethods.check_measure(obsr_val=sum(PrectLi)/len(PrectLi),exp_val=[0.9],comp="GTEQL")
                            res.append([f"The calculated average Prect{cnt} : {round(results[3],3)} W, Limit: {results[2]} W",results[1]])
                        else:
                            # results = CommonMethods.check_measure(obsr_val=sum(PrectLi)/len(PrectLi),exp_val=[round((TPrect/100)*95,3),round((TPrect/100)*105,3)])
                            # res.append([f"The calculated average Prect : {round(results[3],3)}W, Limit +/-5% of Target Prect {TPrect}W i.e {results[2]}W",results[1]])
                            results = CommonMethods.check_measure(obsr_val=sum(PrectLi)/len(PrectLi),exp_val=[round((TPrect-0.1),3)],comp="GTEQL")
                            res.append([f"The calculated average Prect{cnt} : {round(results[3],3)} W, Limit: {results[2]} W",results[1]])

                else:res.append([f"Stablization not found for the Condition 1 between {round(self.file_list[TempPkt3[2]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
            else:res.append([f"Set_Load {int(TPrect*1000)}mA not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    else:res.append([f"The MODEXCAP packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res
def MPLA2_PARAM(self,Flow_limit,Check):
    res =[]
    # limit = Flow_limit
    #try for all flows
    AllLimits = []
    PrevFo = None
    Offsets = []
    id = 0
    while id < len(self.file_list):
        FOpkt = self.PktMethod.GetPacketDetails(packet="",value="FOP:360",limit=[id,len(self.file_list)],Type="TesterMsg")
        if len(FOpkt)>2:
            if PrevFo != None:
                AllLimits.append([PrevFo,FOpkt[2]-1])
            PrevFo=FOpkt[2]
            id = FOpkt[2]+1
        else:
            if PrevFo != None:AllLimits.append([PrevFo,len(self.file_list)-1])
            break
    if len(AllLimits)==3:
        res.append([f"Found 3 flows as expected","Pass"])
    else:res.append([f"Found {len(AllLimits)} out of 3 flows","Fail"])
    if len(AllLimits)>0:
        # # print(AllLimits)
        cond = 0
        for lim in AllLimits:
            cond+=1
            limit=lim
            res.append([f"Condition:{cond} started between {round(self.file_list[limit[0]]['startTime'],3)}sec to {round(self.file_list[limit[1]]['stopTime'],3)}sec","Pass"])
            #Check for the PLAP_2 [0x88] packet g_coil_Rx_pla2 value
            TempPkt6 = self.PktMethod.GetPacketDetails(packet="PLAP_2 [0x88]",limit=limit,Type="Response")
            if len(TempPkt6)>2:
                value = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt6[2],Check['PRx_coil_key'])[0]['sDescription'].split(':')[1])[0]
                if value ==1:
                    res.append([f"The PLAP_2 [0x88] packet found at {round(TempPkt6[0],3)}sec with {Check['PRx_coil_key']} value {value}, expected 1","Pass"])
                else:res.append([f"The PLAP_2 [0x88] packet found at {round(TempPkt6[0],3)}sec with {Check['PRx_coil_key']} value {value}, expected 1","Fail"])
            else:res.append([f"PLAP_2 [0x88] not found for condition {cond}","Fail"])
            TempPkt7 = self.PktMethod.GetPacketDetails(packet="PLAP_2 [0x90]",limit=limit)
            # # print("Check:",Check)
            if cond == 1:
                plap2_default_values = {"Alpha_FM_ITX_pla2": 0,"Alpha_FM_Vrect_Pla2": 0,"Alpha_FM_Irect_Pla2": 0,f"{Check['PTx_coil_key']}": 0}
            if len(TempPkt7)>2:
                try:
                    # value4 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"gb_coil_Tx_pla2")[0]['sDescription'].split(':')[1])[0]
                    value1 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"Alpha_FM_ITX_pla2")[0]['sDescription'].split(':')[1])[0]
                    value2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"Alpha_FM_Vrect_Pla2")[0]['sDescription'].split(':')[1])[0]
                    value3 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"Alpha_FM_Irect_Pla2")[0]['sDescription'].split(':')[1])[0]
                    value4 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],Check['PTx_coil_key'])[0]['sDescription'].split(':')[1])[0]

                    if cond == 1:
                        plap2_default_values['Alpha_FM_ITX_pla2'] = value1
                        plap2_default_values['Alpha_FM_Vrect_Pla2'] = value2
                        plap2_default_values['Alpha_FM_Irect_Pla2'] = value3
                        plap2_default_values[Check['PTx_coil_key']] = value4
                        res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}","Pass"])
                    elif cond == 2:
                        if value1 == plap2_default_values["Alpha_FM_ITX_pla2"] and value2 == plap2_default_values["Alpha_FM_Vrect_Pla2"] and value3 == plap2_default_values["Alpha_FM_Irect_Pla2"] and value4 == (1.2*plap2_default_values[Check['PTx_coil_key']]):
                            res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {plap2_default_values["Alpha_FM_ITX_pla2"]} (default value), Alpha_FM_Vrect_Pla2 == {plap2_default_values["Alpha_FM_Vrect_Pla2"]} (default value), Alpha_FM_Irect_Pla2 == {plap2_default_values["Alpha_FM_Irect_Pla2"]} (default value), {Check['PTx_coil_key']} == {1.2*plap2_default_values[Check['PTx_coil_key']]} (1.2 * default value)","Pass"])
                        else:
                            res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {plap2_default_values["Alpha_FM_ITX_pla2"]} (default value), Alpha_FM_Vrect_Pla2 == {plap2_default_values["Alpha_FM_Vrect_Pla2"]} (default value), Alpha_FM_Irect_Pla2 == {plap2_default_values["Alpha_FM_Irect_Pla2"]} (default value), {Check['PTx_coil_key']} == {1.2*plap2_default_values[Check['PTx_coil_key']]} (1.2 * default value)","Fail"])
                    elif cond == 3:
                        if value1 == (1.2*plap2_default_values["Alpha_FM_ITX_pla2"]) and value2 == round((1.2*plap2_default_values["Alpha_FM_Vrect_Pla2"]),7) and value3 == round((0.8*plap2_default_values["Alpha_FM_Irect_Pla2"]),5) and value4 == plap2_default_values[Check['PTx_coil_key']]:
                            res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {1.2*plap2_default_values["Alpha_FM_ITX_pla2"]} (1.2 * default value), Alpha_FM_Vrect_Pla2 == {round((1.2*plap2_default_values["Alpha_FM_Vrect_Pla2"]),7)} (1.2 * default value), Alpha_FM_Irect_Pla2 == {round((0.8*plap2_default_values["Alpha_FM_Irect_Pla2"]),5)} (0.8 * default value), {Check['PTx_coil_key']} == {plap2_default_values[Check['PTx_coil_key']]} (default value)","Pass"])
                        else:
                            res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {1.2*plap2_default_values["Alpha_FM_ITX_pla2"]} (1.2 * default value), Alpha_FM_Vrect_Pla2 == {round((1.2*plap2_default_values["Alpha_FM_Vrect_Pla2"]),7)} (1.2 * default value), Alpha_FM_Irect_Pla2 == {round((0.8*plap2_default_values["Alpha_FM_Irect_Pla2"]),5)} (0.8 * default value), {Check['PTx_coil_key']} == {plap2_default_values[Check['PTx_coil_key']]} (default value)","Fail"])
                
                except Exception as e:
                    res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec, Exception:{e}","Fail"])
            else:res.append([f"The PLAP_2 [0x90] packet not found for condition {cond}","Fail"])
            #1. find the Load 15000
            TempPkt1 = self.PktMethod.GetPacketDetails(packet="Set_Load 15000mW",limit=limit,Type="TesterMsg")
            if len(TempPkt1)>2:
                res.append([f"Set Load 15000mW found at {round(TempPkt1[0],3)}ms","Pass"])
                #2. find stabiliZATION
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt1[2]+1,limit[1]],Type="TesterMsg")
                if len(TempPkt2)>2:
                    #3. Get Vrect value
                    results = self.GetInitailVoltage(Check['flow'],[TempPkt1[2],TempPkt2[2]+1])
                    if results is not None:
                        resultsMes = CommonMethods.check_measure([13.3,14.7],results[0])
                        res.append([f"Stabilization found at {round(TempPkt2[0],3)}Sec,with caluclate Voltage {results[0]}V measured at {round(self.file_list[results[1]]['startTime'],3)}Sec, limit:{resultsMes[2]}",resultsMes[1]])
                    else:res.append([f"Stabilization found at {round(TempPkt2[0],3)}Sec, Voltage calculation not performed","Fail"])
                    #4.check PLA packet by increaring offset values until PLA gets NAk
                    PLAID = TempPkt2[2]
                    NAK_Flag = False
                    PrevRPoffset = None
                    PLAcount = 0
                    maxoffset = 0
                    while PLAID < limit[1]:
                        TempPkt3 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[PLAID,limit[1]])
                        if len(TempPkt3)>2:
                            PLAcount+=1
                            
                            #Get Prect & RP offset values
                            TempPkt4 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt3[2],TempPkt3[2]-4],Type="TesterMsg")
                            if len(TempPkt4)>2:
                                Prect_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['value'])[0]
                                maxoffset = RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['value'])[1]
                                if Prect_Offset != RP_Offset: res.append([f"The applied Prect_offset {Prect_Offset}W and RP_Offset{RP_Offset} are not same for PLA packet at {round(TempPkt3[0],3)}ms","Fail"])
                            else:res.append([f"Power offset not found for the PLA packet at {round(TempPkt3[0],3)}","Fail"])
                            
                            #get Acutal RP and Prect values
                            TempPkt5 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt3[2],TempPkt3[2]-4],Type="TesterMsg")
                            if len(TempPkt5)>2:
                                Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt5[2]]['pktType'])[0]
                                RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt5[2]]['pktType'])[1]
                            else: res.append([f"Rectified not found for the PLA packet at {round(TempPkt3[0],3)}","Fail"])
                            Prect_Final = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                            RP_Final = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                            
                            if len(TempPkt4)>2 and len(TempPkt5)>2:
                                # result = "Pass" if Prect_Final == round((Prect_Actual-Prect_Offset),3) and RP_Final == round((RP_Actual-RP_Offset),3) else "Fail"
                                # #add only if PLA_2 checks fails to reduce the report length 
                                # if result=="Fail": res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec with Perct={Prect_Final}W and RP={RP_Final}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",result])
                                if Prect_Final == round((Prect_Actual-Prect_Offset),3) and RP_Final == round((RP_Actual-RP_Offset),3):
                                    res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec with Prect={Prect_Final}W, RP={RP_Final}W | Prect_actual = {Prect_Actual}W, RP_actual={RP_Actual} | Prect_Offset={Prect_Offset}W, RP_offset={RP_Offset}W, Expected: Prect = Prect_actual - P_offset and RP = RP_Actual - RP_offset","Pass"])
                                else:
                                    res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec with Prect={Prect_Final}W, RP={RP_Final}W | Prect_actual = {Prect_Actual}W, RP_actual={RP_Actual} | Prect_Offset={Prect_Offset}W, RP_offset={RP_Offset}W, Expected: Prect = Prect_actual - P_offset and RP = RP_Actual - RP_offset","Fail"])


                                #ensure offset increment
                                if PrevRPoffset is not None:
                                    if round(abs(RP_Offset-PrevRPoffset),3)!=0.01:
                                        res.append([f"The RP_offset not increased by 0.01W from previous offset value","Fail"])
                                
                                #Check for PLA_with NAK response
                                PLAresp = self.PktMethod.GetPacketResponse(TempPkt3[2],[TempPkt3[2]+1,limit[1]])
                                # # print(cond,PLAresp,TempPkt3,[TempPkt3[2]+1,Flow_limit[1]])
                                if PLAresp is not None:
                                    if self.file_list[PLAresp]['pktType'] == "NAK":
                                        res.append([f"NAK response found to the PLA packet for P_offset: {Prect_Offset} W  at {round(TempPkt3[0],3)}sec","Pass"]) 
                                        NAK_Flag=True
                                        break
                                PrevRPoffset = RP_Offset
                            else:res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec, offset calculations not performed!","Fail"])
                            PLAID = TempPkt3[2]+1
                        else:break
                    if NAK_Flag==False:res.append([f"PLA packet with NAK not found for Condition {cond}","Fail"])
                    res.append([f"Found {PLAcount} PLA packets for the Condition {cond} and the applied last offset is {maxoffset}W","Pass"])
                    Offsets.append(maxoffset)
                else:res.append([f"The Stabilization not found","Fail"])
            else:res.append([f"Set load for 15000mW not found","Fail"])
            # break
    if len(Offsets)==3:
        if Offsets[1] > Offsets[0]:
            res.append([f"Max offset for condition B ({Offsets[1]}W) is grater than the Condition A max offset value({Offsets[0]}W)","Pass"])
        else:res.append([f"Max offset for condition B ({Offsets[1]}W) is not grater than the Condition A max offset value({Offsets[0]}W)","Fail"])
        if Offsets[2] > Offsets[0]:
            res.append([f"Max offset for condition C ({Offsets[2]}W) is grater than the Condition A max offset value({Offsets[0]}W)","Pass"])
        else:res.append([f"Max offset for condition C ({Offsets[2]}W) is not grater than the Condition A max offset value({Offsets[0]}W)","Fail"])
    else:res.append([f"Not all 3 conditions applied","Fail"])
    return res
def extract_and_read_csv_from_zip(self,zip_path, csv_match):
    # # print(csv_match)
    with open(zip_path, "rb") as file:
        zip_bytes = io.BytesIO(file.read())  # Load ZIP into memory
    with zipfile.ZipFile(zip_bytes, "r") as zip_file:
        # Find CSV file by matching name
        matched_csv = [name for name in zip_file.namelist() if all(res in name for res in csv_match)]
        # # print(matched_csv)
        if not matched_csv:
            # # print(f"No CSV file matching '{csv_match}' found.")
            return None
        # Read the first matched CSV file
        with zip_file.open(matched_csv[0]) as csv_file:
            reader = csv.reader(io.TextIOWrapper(csv_file, encoding="utf-8"))
            data_list = [row for row in reader]
            return data_list
def MatchCSVvalues(self,CSVlist,name):
    for row in CSVlist:
        # if name =="Fclk":# print(row)
        # # print(row)
        if len(row)>2:
            if name in row[0]:
                return row[1]
    return None
def OffsetReneg(self,Flow_limit,Check):
    # print("OffsetReneg started")
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)

    res = []
    Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
    # print("Excapres:",Excapres)
    if len(Excapres)> 2:
        EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
        for ck in EXCAP.keys():
            payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
            # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
            EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
        # print("EXCAP:",EXCAP)
        mode1 = sorted(EXCAP, key=EXCAP.get, reverse=True)[1]  # second highest potential load power
        mode2 = max(EXCAP, key=EXCAP.get)    # highest potential load power
        # print("mode1:",mode1, "mode2:",mode2)

        end = len(self.file_list)-1
        pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=Flow_limit)
        if len(pkt_exit)>2:
            MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=[pkt_exit[2],end],Type="Packet")
            if len(MSRreq2)> 2:
                PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                # print("PrefMode2:",PrefMode2)
                res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: Mode2: {mode2}", "Pass" if mode2 == PrefMode2 else "Fail"])
                MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],end],Type="Response")
                if len(MSS2)> 2:
                    res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", "Pass"])

                    ECAP = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=[MSS2[2],end],Type="Response")
                    if len(ECAP)>2:
                        renegpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                        res.append([f"Negotiable_Load_Power in ECAP is {renegpwr}W", "Pass"])

                        reqload = renegpwr*(Check['TargetLoadPercent'])/100
                        res.append([f"{Check['TargetLoadPercent']}% of Negotiable_Load_Power is {reqload}W", "Pass"])

                        renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(reqload*1000)}mW",limit=[ECAP[2],end],Type='TesterMsg')
                        # print("renegload:",renegload)
                        if len(renegload)>2:
                            res.append([f"Set_Load {int(reqload*1000)}mW found at {round(renegload[0],3)}sec","Pass"])
                            self.GetInitailVoltage(Check['flow'],[renegload[2],end])
                            
                            irect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                            vrect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData)
                            power = round(vrect[0]*irect[0],3)
                            # print("vrect:",vrect,"irect:",irect,"power:",power)
                            res.append([f"Prect after control stabilization is {power} W at {round(self.file_list[self.stability]['startTime'],3)} sec, Expected: >= {reqload}W", "Pass" if power>=reqload else "Fail"])
                        # else: res.append([f"Set_Load {int(reqload*1000)}mW not found", "Fail"])

                            duration_flag = False
                            removepwr = False
                            #2.Find PLA packts has power offset
                            id = self.stability#renegload[2]
                            while id < end:
                                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,end])
                                # # print("TempPkt2:",TempPkt2)
                                if len(TempPkt2)>2:
                                    Pktresp = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,end])
                                    if Pktresp is not None:
                                        
                                        res.append([f"{self.file_list[Pktresp]['pktType']} response received to PLA_2 packet at {round(TempPkt2[0],3)} sec", "Pass"])
                                        

                                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                                    if len(TempPkt3)>2 and len(TempPkt4)>2:
                                        RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[1]
                                        Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[0]

                                        RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                                        Prect_Offset =  GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                                        
                                        Prect_Rcv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"PRECT")[0]['sDescription'])[0]
                                        RP_Rcvd = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'])[0]
                                        # print("Prect_Actual:",Prect_Actual,"Prect_Offset:",Prect_Offset,"Prect_Rcv:",Prect_Rcv)
                                        # print("RP_Actual:",RP_Actual,"RP_Offset:",RP_Offset,"RP_Rcvd:",RP_Rcvd)

                                        #check for offset value are applied as like mentioned in the CTS
                                        if 'FixedOffsetValues' in Check:
                                            # # print(RP_Offset,Prect_Offset)
                                            if RP_Offset!=Check['FixedOffsetValues']['RP'] or Prect_Offset!=Check['FixedOffsetValues']['Prect']:
                                                res.append([f"PLA offset issue at {round(TempPkt2[0],3)}: RP Offset:{RP_Offset}W Expected :{Check['FixedOffsetValues']['RP']}, Prect Offset:{Prect_Offset}W Expected :{Check['FixedOffsetValues']['Prect']}W","Fail"])
                                        #Ensure that the offset calculations are correct
                                        PLARes = "Pass" if Prect_Rcv == round((Prect_Actual+(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual+(RP_Offset)),3) else "Fail"
                                        if PLARes=="Fail":res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect_Rcv}W and RP={RP_Rcvd}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
                                        else: res.append([f"Prect_Actual:{Prect_Actual}W is matching with Prect_Rcv:{Prect_Rcv}W after applying Prect_Offset:{Prect_Offset}W and RP_Actual:{RP_Actual}W is matching with RP_Rcvd:{RP_Rcvd}W after applying RP_Offset:{RP_Offset}W","Pass"])
                                        
                                        
                                        # PLA response
                                        x = TempPkt2[2]+1
                                        if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                                            x += 1
                                        
                                        # if 'Response' in self.PktMethod.GetPacketType(x):
                                        #     res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet", "Pass"])
                                            

                                        # Throttle check
                                        
                                        if 'NAK' in self.file_list[x]['pktType']:
                                            nak_chk = True
                                            vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                            irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                            Prect1 = vrect1*irect1

                                            vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                            irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                            Prect2 = vrect2*irect2

                                            pwr_diff = round((Prect2-Prect1)*1000,3)
                                            
                                            
                                            if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                                res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                            else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                            
                                        elif 'ACK' in self.file_list[x]['pktType']:
                                            res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", "Pass"])
                                        
                                        
                                        
                                        if Pktresp is not None:
                                            if self.file_list[Pktresp]['pktType'] in ['ATN']:
                                                id = Pktresp
                                                break
                                    id = TempPkt2[2]
                                id += 1

                            ECAP2 = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=[id,end],Type="Response")
                            
                            if len(ECAP2)>2:
                                negpwr2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP2[2],'Negotiable_Load_Power')[0]['sDescription'])[0]
                                # print("negpwr2:",negpwr2)
                                res.append([f"RENEG_POWER in Extended_Power_Transmitter_Extended_Capabilities is {negpwr2}W found at index@{ECAP2[2]}", "Pass"])
                                reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[ECAP2[2],end],Type="Packet")
                                
                                if len(reneg)>2:
                                    res.append([f"Renegotiate packet found at index@{reneg[2]}", "Pass"])
                                    respid = self.PktMethod.GetPacketResponse(reneg,[reneg[2]+1,end])
                                    if respid is not None:
                                        if self.file_list[respid]['pktType'] =="ACK":
                                            res.append([f"ACK response found at index@{respid}", "Pass"])
                                            srqepl = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=[respid,end],Type="Packet")
                                            if len(srqepl)>2:
                                                res.append([f"SRQ(Extended Power Level Selection) found at index@{srqepl[2]}", "Pass"])
                                                respid2 = self.PktMethod.GetPacketResponse(srqepl,[srqepl[2]+1,end])
                                                if respid2 is not None:
                                                    if self.file_list[respid2]['pktType'] =="ACK":
                                                        res.append([f"ACK response found at index@{respid2}", "Pass"])
                                                        srqen = self.PktMethod.GetPacketDetails(packet="SRQ",value="End Negotiation",limit=[respid2,end],Type="Packet")
                                                        if len(srqen)>2:
                                                            res.append([f"SRQ(End Negotiation) found at index@{srqen[2]}", "Pass"])
                                                            respid3 = self.PktMethod.GetPacketResponse(srqen,[srqen[2]+1,end])
                                                            if respid3 is not None:
                                                                if self.file_list[respid3]['pktType'] =="ACK":
                                                                    res.append([f"ACK response found at index@{respid3}", "Pass"])

                                                                    renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(negpwr2*1000)}mW",limit=[respid3,end],Type='TesterMsg')
                                                                    # print("renegload:",renegload)
                                                                    if len(renegload)>2:
                                                                        
                                                                        pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[renegload[2],end],Type="Response")
                                                                        if len(pkt_DPM)>2:
                                                                            alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                                                            beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                                                            invalid = float(self.PktMethod.GetPayloadDetails(pkt_DPM[2],"Invalid")[0]['sDescription'].split(":")[1].strip())
                                                                            res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0],2)} sec with Invalid: {invalid}, dPLoss-Alpha:{alpha}, dPLoss-Beta:{beta}","Pass" if invalid == 1 and alpha == 0 and beta == 0 else "Fail"])
                                                                        else:res.append([f"DPCAL_PARAM packet not recevied","Fail"])
                                                                    
                                                                    else: res.append([f"Set_Load {int(negpwr2*1000)}mW not found", "Fail"])
    return res


def OffsetReneg2(self,Flow_limit,Check):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)

    res = []

    end = Flow_limit[1]
    pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=Flow_limit)
    if len(pkt_exit)>2:

        ECAP = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=[pkt_exit[2],0],Type="Response")
        if len(ECAP)>2:
            renegpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
            res.append([f"Negotiable_Load_Power in ECAP is {renegpwr}W", "Pass"])

            reqload = renegpwr*(Check['TargetLoadPercent'])/100
            res.append([f"{Check['TargetLoadPercent']}% of Negotiable_Load_Power is {reqload}W", "Pass"])

            renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(reqload*1000)}mW",limit=[ECAP[2],end],Type='TesterMsg')
            # print("renegload:",renegload)
            if len(renegload)>2:
                res.append([f"Set_Load {int(reqload*1000)}mW found at {round(renegload[0],3)}sec","Pass"])
                self.GetInitailVoltage(Check['flow'],[renegload[2],end])
                
                irect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                vrect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData)
                power = round(vrect[0]*irect[0],3)
                # print("vrect:",vrect,"irect:",irect,"power:",power)
                res.append([f"Prect after control stabilization is {power} W at {round(self.file_list[self.stability]['startTime'],3)} sec, Expected: >= {reqload}W", "Pass" if power>=reqload else "Fail"])
            # else: res.append([f"Set_Load {int(reqload*1000)}mW not found", "Fail"])

                #2.Find PLA packts has power offset
                duration_flag = False
                removepwr = False
                id = self.stability#renegload[2]
                while id < end:
                    TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,end])
                    # # print("TempPkt2:",TempPkt2)
                    if len(TempPkt2)>2:
                        Pktresp = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,end])
                        if Pktresp is not None:
                            if 'exp_resp' in Check:
                                if 'Response' in self.GetPacketType(x):
                                    if self.file_list[x]['pktType'] in Check["exp_resp"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Pass"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Fail"])
                            else: res.append([f"{self.file_list[Pktresp]['pktType']} response received to PLA_2 packet at {round(TempPkt2[0],3)} sec", "Pass"])
                            

                        TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                        TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                        if len(TempPkt3)>2 and len(TempPkt4)>2:
                            RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[1]
                            Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[0]

                            RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                            Prect_Offset =  GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                            
                            Prect_Rcv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"PRECT")[0]['sDescription'])[0]
                            RP_Rcvd = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'])[0]
                            # print("Prect_Actual:",Prect_Actual,"Prect_Offset:",Prect_Offset,"Prect_Rcv:",Prect_Rcv)
                            # print("RP_Actual:",RP_Actual,"RP_Offset:",RP_Offset,"RP_Rcvd:",RP_Rcvd)
                            #check for offset value are applied as like mentioned in the CTS
                            if 'FixedOffsetValues' in Check:
                                # # print(RP_Offset,Prect_Offset)
                                if RP_Offset!=Check['FixedOffsetValues']['RP'] or Prect_Offset!=Check['FixedOffsetValues']['Prect']:
                                    res.append([f"PLA offset issue at {round(TempPkt2[0],3)}: RP Offset:{RP_Offset}W Expected :{Check['FixedOffsetValues']['RP']}, Prect Offset:{Prect_Offset}W Expected :{Check['FixedOffsetValues']['Prect']}W","Fail"])
                            #Ensure that the offset calculations are correct
                            PLARes = "Pass" if Prect_Rcv == round((Prect_Actual+(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual+(RP_Offset)),3) else "Fail"
                            if PLARes=="Fail":res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect_Rcv}W and RP={RP_Rcvd}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
                            else: res.append([f"Prect_Actual:{Prect_Actual}W is matching with Prect_Rcv:{Prect_Rcv}W after applying Prect_Offset:{Prect_Offset}W and RP_Actual:{RP_Actual}W is matching with RP_Rcvd:{RP_Rcvd}W after applying RP_Offset:{RP_Offset}W","Pass"])
                            
                            
                            # PLA response
                            x = TempPkt2[2]+1
                            if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                                x += 1
                            
                            # if 'Response' in self.PktMethod.GetPacketType(x):
                            #     res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet", "Pass"])
                                

                            # Throttle check
                            
                            if 'NAK' in self.file_list[x]['pktType']:
                                nak_chk = True
                                vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                Prect1 = vrect1*irect1

                                vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                Prect2 = vrect2*irect2

                                pwr_diff = round((Prect2-Prect1)*1000,3)
                                
                                
                                if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                
                            elif 'ACK' in self.file_list[x]['pktType']:
                                res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", "Pass"])
                            
                            
                            #check PLA until
                            if 'CheckDuration' in Check:
                                # # print('diff',TempPkt2[0] - TempPkt1[0])
                                duration = (TempPkt2[0] - self.file_list[self.stability]['startTime'])
                                if duration >= Check['CheckDuration']:
                                    duration_flag = True
                                    break
                            if Pktresp is not None:
                                if self.file_list[Pktresp]['pktType'] in ['ATN']:
                                    id = Pktresp
                                    break
                        id = TempPkt2[2]
                    id += 1
                
                # Power remove
                if 'Remove_Power' in Check:
                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[id,end],Type="TesterMsg")
                    if Check['Remove_Power']:
                        if len(sd)> 2:
                            removepwr = True
                            res.append([f"PTx removed power at {round(sd[0],3)} sec", "Pass"])
                        else: res.append([f"PTx does not removed power", "Fail"])
                    else:
                        if len(sd)> 2:
                            removepwr = True
                            res.append([f"PTx removed power at {round(sd[0],3)} sec", "Fail"])
                        else: res.append([f"PTx does not removed power", "Pass"])

                if 'CheckDuration' in Check:
                    if not removepwr:
                        if duration_flag:
                            res.append([f"TPR monitored PLA packets for at least 1 minute after stabilizing.", "Pass"])
                        else: res.append([f"TPR monitored PLA packets for only {round(duration,3)} sec after stabilizing.", "Fail"])
        
                ECAP2 = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=[id,end],Type="Response")
                
                if len(ECAP2)>2:
                    negpwr2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP2[2],'Negotiable_Load_Power')[0]['sDescription'])[0]
                    # print("negpwr2:",negpwr2)
                    res.append([f"RENEG_POWER in Extended_Power_Transmitter_Extended_Capabilities is {negpwr2}W found at index@{ECAP2[2]}", "Pass"])
                    reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[ECAP2[2],end],Type="Packet")
                    
                    if len(reneg)>2:
                        res.append([f"Renegotiate packet found at index@{reneg[2]}", "Pass"])
                        respid = self.PktMethod.GetPacketResponse(reneg,[reneg[2]+1,end])
                        if respid is not None:
                            if self.file_list[respid]['pktType'] =="ACK":
                                res.append([f"ACK response found at index@{respid}", "Pass"])
                                srqepl = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=[respid,end],Type="Packet")
                                if len(srqepl)>2:
                                    res.append([f"SRQ(Extended Power Level Selection) found at index@{srqepl[2]}", "Pass"])
                                    respid2 = self.PktMethod.GetPacketResponse(srqepl,[srqepl[2]+1,end])
                                    if respid2 is not None:
                                        if self.file_list[respid2]['pktType'] =="ACK":
                                            res.append([f"ACK response found at index@{respid2}", "Pass"])
                                            srqen = self.PktMethod.GetPacketDetails(packet="SRQ",value="End Negotiation",limit=[respid2,end],Type="Packet")
                                            if len(srqen)>2:
                                                res.append([f"SRQ(End Negotiation) found at index@{srqen[2]}", "Pass"])
                                                respid3 = self.PktMethod.GetPacketResponse(srqen,[srqen[2]+1,end])
                                                if respid3 is not None:
                                                    if self.file_list[respid3]['pktType'] =="ACK":
                                                        res.append([f"ACK response found at index@{respid3}", "Pass"])

                                                        renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(negpwr2*1000)}mW",limit=[respid3,end],Type='TesterMsg')
                                                        # print("renegload:",renegload)
                                                        if len(renegload)>2:
                                                            
                                                            pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[renegload[2],end],Type="Response")
                                                            if len(pkt_DPM)>2:
                                                                alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                                                beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                                                invalid = float(self.PktMethod.GetPayloadDetails(pkt_DPM[2],"Invalid")[0]['sDescription'].split(":")[1].strip())
                                                                res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0],2)} sec with Invalid: {invalid}, dPLoss-Alpha:{alpha}, dPLoss-Beta:{beta}","Pass" if invalid == 1 and alpha == 0 and beta == 0 else "Fail"])
                                                            else:res.append([f"DPCAL_PARAM packet not recevied","Fail"])
                                                        
                                                        else: res.append([f"Set_Load {int(negpwr2*1000)}mW not found", "Fail"])
    return res

def Thermal(self,Flow_limit,Check):
    res = []
    Flow_limit = Flow_limit
    for tests in self.BKjsonData['testBkpTestResultsandPath']:
        if self.Header['TestcaseID'] == tests['testcaseDetails']['m_TestId']:
            basepath = Path(os.path.dirname(self.ProjectJson))
            path1 = tests["actualIndividualTestcaseFolder"]
            # print(path1.split("\\")[-2])
            run_path = basepath/path1.split("\\")[-2]
            for file in os.listdir(run_path):
                if file.startswith("MPP_PTX_THERMAL") and file.endswith(".csv"):
                    csv_path = os.path.join(run_path, file)
                    # print("csv_path:",csv_path)

                    #csv read
                    df = pd1.read_csv(csv_path)

                    ECAP = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=Flow_limit,Type="Response")
                    # print('ECAP:',ECAP)
                    if len(ECAP)>2:
                        ECAPppwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Potential_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                        # print("ECAPppwr:",ECAPppwr)
                        res.append([f"Potential_Load_Power is {ECAPppwr} W in Extended_Power_Transmitter_Extended_Capabilities at {round(ECAP[0],3)} sec", "Pass"])
                        XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[ECAP[2],Flow_limit[1]],Type="Packet")
                        # print('XCE:',XCE)
                        pwr_mtrid = 0
                        if len(XCE)>2:
                            res.append([f"PT phase started at {round(XCE[0],3)} sec", "Pass"])

                            start = XCE[2]
                            # t0 = XCE[0]
                            self.AllChannelData11 = self.PlotMethod.GetAllChannelData('11',self.JapiData)
                            self.AllChannelData12= self.PlotMethod.GetAllChannelData('12',self.JapiData)
                            sindex = int((XCE[0]*1000)/self.AllChannelData12['Interval'])
                            fotemp0 = self.AllChannelData12['RV']['displayDataChunk'][sindex]
                            ambtemp0 = self.AllChannelData11['RV']['displayDataChunk'][sindex]
                            res.append([f"Measured Puck_temp_t0: {fotemp0}℃, Ambient_temp_t0: {ambtemp0}℃ at t0: {round(XCE[0],3)} sec", "Pass"])
                            # print("fotemp0:",fotemp0,"ambtemp0:",ambtemp0)

                            # Absolute Max puck temp
                            sindex3 = int((self.file_list[Flow_limit[0]]['startTime'])/self.AllChannelData12['Interval'])
                            alltempdata = self.AllChannelData12['RV']['displayDataChunk'][sindex3:]
                            
                            Maxtemp = max(alltempdata)
                            Temp_max_t = ((self.AllChannelData12['RV']['displayDataChunk'].index(Maxtemp))*self.AllChannelData12['Interval']) #millisec
                            # print("Maxtemp:", Maxtemp, "time:",self.PktMethod.ms_to_time(Temp_max_t))
                            if Maxtemp <= 48:
                                res.append([f"Absolute maximum puck_temp is {Maxtemp}℃ at {self.PktMethod.ms_to_time(Temp_max_t)}, Expected: <= 48℃", "Pass"])
                            else:
                                res.append([f"Absolute maximum puck_temp is {Maxtemp}℃ at {self.PktMethod.ms_to_time(Temp_max_t)}, Expected: <= 48℃", "Fail"])

                            if ECAPppwr > 15:
                                res.append([f"Potential_Load_Power is {ECAPppwr} W in Extended_Power_Transmitter_Extended_Capabilities i.e, > 15W", "Pass"])
                                tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,"Inconclusive": False,"CheckSEQ": 1}
                                dplosschks = self.DPlossCalibrationCheck(tempcheck)
                                # # print(chk for chk in dplosschks)
                                # res.append(chk for chk in dplosschks)
                                for chk in dplosschks:
                                    res.append(chk)
                                calexit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=[ECAP[2],Flow_limit[1]],Type="Packet")
                                # print('calexit:',calexit)
                                if len(calexit)>2:
                                    nxt_start = calexit[2]
                                    pwr_mtrid = calexit[2]
                            else: 
                                res.append([f"Potential_Load_Power is {ECAPppwr} W, so DPLOSS calibration won't perform, Expected: > 15 W", "Pass"])
                                setload2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(ECAPppwr*1000)}mW",limit=[ECAP[2],Flow_limit[1]],Type='TesterMsg')
                                # print('setload2:',setload2)
                                if len(setload2)>2:
                                    res.append([f"Set_Load {int(ECAPppwr*1000)}mW packet found at {round(setload2[0],3)}sec","Pass"])
                                else:
                                    res.append([f"Set_Load {int(ECAPppwr*1000)}mW packet not found","Fail"])
                                pwr_mtrid = XCE[2]
                            
                            pla_cnt1 = 1
                            pla_cnt2 = 0
                            t_start = 0
                            prect_min = []
                            prect_max = []
                            while start < Flow_limit[1]:
                                pla2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[start,Flow_limit[1]],Type="Packet")
                                if len(pla2)>2:
                                    prect = float(self.PktMethod.GetPayloadDetails(pla2[2],"PRECT")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                    if prect >= 14.5:
                                        if pla_cnt1 == 1:
                                            # print("First PLA_2 packet with prect >= 14.5 W:",pla2)
                                            res.append([f"First PLA_2 packet found at {round(pla2[0],3)} sec with Prect: {prect}, Expected: Prect >= 14.5 W", "Pass"])
                                            t1 = pla2[0]
                                            # print("t1:",t1)
                                            res.append([f"t1 is {round(t1,3)} sec", "Pass"])
                                            tempdata2 = self.Thermaldata(csv_path,t1,max_delT=True)
                                            if tempdata2:
                                                if tempdata2['Temp_Rise'] <= 25:
                                                    res.append([f"Max Δtemp: {tempdata2['Temp_Rise']}℃ found at {round(tempdata2['startTime'],3)} sec (t1+15min), Expected: <= 25℃", "Pass"])
                                                else:
                                                    res.append([f"Max Δtemp: {tempdata2['Temp_Rise']}℃ found at {round(tempdata2['startTime'],3)} sec (t1+15min), Expected: <= 25℃", "Fail"])
                                            else:
                                                res.append([f"Max Δtemp not found", "Fail"])
                                            nxt_start = pla2[2]
                                            # break
                                        pla_cnt1 += 1

                                    # TPRPLA_2[PRECT] >= PTx ECAP[Potential Load Power]- 2%
                                    if pla2[2] >= pwr_mtrid: 
                                        if prect >= (0.98*ECAPppwr):  
                                            pla_cnt2 += 1
                                            if pla_cnt2 == 1:
                                                t_start = pla2[0]
                                                prect_min = [prect,pla2[0]]
                                                prect_max = [prect,pla2[0]]
                                            else:
                                                if prect < prect_min[0]:
                                                    prect_min = [prect,pla2[0]]
                                                if prect > prect_max[0]:
                                                    prect_max = [prect,pla2[0]]
                                            
                                            # 150 sec
                                            if pla2[0] - t_start >= 150:
                                                res.append([f"TPR PLA_2 Prect >= PTx ECAP[Potential Load Power]- 2% for greatert than 150 sec","Pass"])
                                                res.append([f"Minimum Prect: {prect_min[0]} W at {round(prect_min[1],3)} sec","Pass"])
                                                res.append([f"Maximum Prect: {prect_max[0]} W at {round(prect_max[1],3)} sec","Pass"])
                                                break
                                        else:
                                            pla_cnt2 = 0
                                            t_start = 0
                                            prect_min = []
                                            prect_max = []
                                    start = pla2[2]+1
                                start += 1
                            
                            pwrs = [10,1]
                            temp_lmts = [15,10]
                            for pwr,temp_lmt in zip(pwrs,temp_lmts):
                                setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(pwr*1000)}mW",limit=[nxt_start,Flow_limit[1]],Type='TesterMsg')
                                # print('setload:',setload)
                                if len(setload)>2:
                                    res.append([f"Set_Load {int(pwr*1000)}mW packet found at {round(setload[0],3)}sec","Pass"])
                                    tempdata3 = self.Thermaldata(csv_path,setload[1]+900)  # after 15 min
                                    # print("tempdata3:",tempdata3)
                                    if tempdata3:
                                        if float(tempdata3['Temp_Rise']) <= temp_lmt:
                                            res.append([f"Max Δtemp: {tempdata3['Temp_Rise']}℃ found at {round(tempdata3['startTime'],3)} sec {"(t1+30)" if pwr == 10 else "(t1+45)"}, Expected: <= {temp_lmt}℃", "Pass"])
                                        else:
                                            res.append([f"Max Δtemp: {tempdata3['Temp_Rise']}℃ found at {round(tempdata3['startTime'],3)} sec {"(t1+30)" if pwr == 10 else "(t1+45)"}, Expected: <= {temp_lmt}℃", "Fail"])
                                    else:
                                        res.append([f"Max Δtemp not found", "Fail"])
                                    nxt_start = setload[2]
                                else:
                                    res.append([f"Set_Load {int(pwr*1000)}mW packet not found", "Fail"])
                            # cloak
                            #Cloak enter
                            clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[Flow_limit[1],len(self.file_list)-1],Type="Packet")
                            # print("clk_ping:",clk_ping)
                            if len(clk_ping) > 2:
                                reason =self.PktMethod.GetPayloadDetails(clk_ping[2],'Reason')[0]["sDescription"].split(":")[-1].strip()
                                rsn_chk =  CommonMethods.check_measure(["Generic"],reason,"EQL")
                                # print("reason:",rsn_chk)
                                clk_resp = self.file_list[clk_ping[2]+1].get('pktType')
                                res.append([f"Cloak enter found with reason:{reason} at {round(clk_ping[0],3)} sec and received {self.file_list[clk_ping[2]+1].get('pktType')}", rsn_chk[1]])
                                tempdata4 = self.Thermaldata(csv_path,clk_ping[1]+1800)  # after 30 min
                                # print("tempdata4:",tempdata4)
                                if tempdata4:
                                    if float(tempdata4['Temp_Rise']) <= 6:
                                        res.append([f"Max Δtemp: {tempdata4['Temp_Rise']}℃ found at {round(tempdata4['startTime'],3)} sec (t1+75min), Expected: <= 6℃", "Pass"])
                                    else:
                                        res.append([f"Max Δtemp: {tempdata4['Temp_Rise']}℃ found at {round(tempdata4['startTime'],3)} sec (t1+75min), Expected: <= 6℃", "Fail"])
                                else:
                                    res.append([f"Max Δtemp not found", "Fail"])
                            else: res.append([f"Cloak enter not found", "Fail"])

                                
                    break            
                                    

    return res

def Thermaldata(self,file_path,t,max_delT=False):
    df = pd1.read_csv(file_path, header=None)

    # Detect header row
    header_row = None
    for i, row in df.iterrows():
        row_str = " ".join(row.astype(str)).lower()
        if "starttime" in row_str and "ambient" in row_str:
            header_row = i
            break

    # Load actual table
    clean_df = pd1.read_csv(file_path, skiprows=header_row)

    # Remove empty columns (FIX)
    clean_df = clean_df.dropna(axis=1, how='all')
    clean_df.columns = ["startTime","Ambient_Temp","Puck_Temp","Temp_Rise"]

    # Clean all columns properly
    clean_df = clean_df.replace("℃", "", regex=True)
    for col in clean_df.columns:
        clean_df[col] = clean_df[col].astype(str).str.strip()
        clean_df[col] = pd1.to_numeric(clean_df[col], errors='coerce')

    # Drop invalid rows
    clean_df = clean_df.dropna(subset=["startTime", "Ambient_Temp", "Puck_Temp"])

    input_start_time = t
    filtered_df = clean_df[round(clean_df["startTime"],0) == round(input_start_time,0)]
    
    # Max_tisr in 15 min
    if max_delT:
        t0 = filtered_df.iloc[0]["startTime"]
        t_end = t0 + 900

        window_df = clean_df[(clean_df["startTime"] >= t0) &(clean_df["startTime"] <= t_end)]
        window_df = window_df.dropna(subset=["Temp_Rise"])
        if not window_df.empty:
            max_row = window_df.loc[window_df["Temp_Rise"].idxmax()]

            # print("Max Temp Rise:", max_row["Temp_Rise"])
            # print("At Time:", max_row["startTime"])
            return {"startTime":float(max_row["startTime"]),"Ambient_Temp":float(max_row["Ambient_Temp"]),"Puck_Temp":float(max_row["Puck_Temp"]),"Temp_Rise":float(max_row["Temp_Rise"])}
        else:
            # print("No valid data in window")
            return None

    else:
        if not filtered_df.empty:
            matched_index = filtered_df.index[0]
            if matched_index > 0:
                exact_match_df = clean_df[clean_df["startTime"] == input_start_time]
                if not exact_match_df.empty:
                    row = exact_match_df.iloc[0]
                    return {"startTime": float(row["startTime"]),"Ambient_Temp": float(row["Ambient_Temp"]),"Puck_Temp": float(row["Puck_Temp"]),"Temp_Rise": float(row["Temp_Rise"])}
                else:
                    matched_index = filtered_df.index[0]
                    if matched_index > 0:
                        prev_row = clean_df.loc[matched_index - 1]
                        return {"startTime": float(prev_row["startTime"]),"Ambient_Temp": float(prev_row["Ambient_Temp"]),"Puck_Temp": float(prev_row["Puck_Temp"]),"Temp_Rise": float(prev_row["Temp_Rise"])}
                    else:
                        return None
                
def Cal_Preserve(self,Flow_limit,Check):
    res = []
    Flow_limit = Flow_limit
    Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
    if len(Excapres)> 2:
        EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
        for ck in EXCAP.keys():
            payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
            # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
            EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
        # print("EXCAP:",EXCAP)
        mode1 = sorted(EXCAP, key=EXCAP.get, reverse=True)[1]  # second highest potential load power
        mode2 = max(EXCAP, key=EXCAP.get)    # highest potential load power
        # print("mode1:",mode1, "mode2:",mode2)

        ideal = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
        if len(ideal)>2:
            pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[ideal[2],Flow_limit[1]],Type="Response")
            if len(pkt_DPM)>2:
                alpha1 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                beta1 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                if any(res1 == 0 for res1 in [alpha1,beta1]):
                    res.append([f"The DPCAL_PARAM packet wit Alpha1: {alpha1}, Beta1: {beta1} received at {round(pkt_DPM[0],2)}sec","Fail"])
                else:res.append([f"The DPCAL_PARAM packet with Alpha1: {alpha1}, Beta1: {beta1} received at {round(pkt_DPM[0],2)}sec","Pass"])

                templmt = [pkt_DPM[2],len(self.file_list)-1]
                MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=templmt,Type="Packet")
                if len(MSRreq2)> 2:
                    PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                    # print("PrefMode2:",PrefMode2)
                    res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: Mode2: {mode2}", "Pass" if mode2 == PrefMode2 else "Fail"])
                    MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],templmt[1]],Type="Response")
                    if len(MSS2)> 2:
                        res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", "Pass"])
                        ECAP = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=[MSS2[2],templmt[1]],Type="Response")
                        if len(ECAP)>2:
                            renegpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                            res.append([f"Negotiable_Load_Power in ECAP is {renegpwr}W, Expected: 25W", "Pass" if renegpwr == 25 else 'Fail'])
                            pkt_DPM2 = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[ECAP[2],templmt[1]],Type="Response")
                            if len(pkt_DPM2)>2:
                                alpha2 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM2[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                beta2 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM2[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                if any(res2 == 0 for res2 in [alpha2,beta2]):
                                    res.append([f"The DPCAL_PARAM packet wit Alpha2: {alpha2}, Beta2: {beta2} received at {round(pkt_DPM2[0],2)}sec","Fail"])
                                else:res.append([f"The DPCAL_PARAM packet with Alpha2: {alpha2}, Beta2: {beta2} received at {round(pkt_DPM2[0],2)}sec","Pass"])
                                res.append([f"Alpha1:{alpha1} , Alpha2:{alpha2} , Beta1:{beta1} , Beta2:{beta2} , Expected: Alpha1=Alpha2, Beta1=Beta1", "Pass" if alpha1==alpha2 and beta1==beta2 else "Fail"])

                                renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(renegpwr*1000)}mW",limit=[ECAP[2],templmt[1]],Type='TesterMsg')
                                # print("renegload:",renegload)
                                if len(renegload)>2:
                                    res.append([f"Set_Load {int(renegpwr*1000)}mW found at {round(renegload[0],3)} sec", "Pass"])
                                    ideal2 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[renegload[2],templmt[1]],Type="TesterMsg")
                                    if len(ideal2)>2:
                                        res.append([f"MPP_XCEV_Ideal found at {round(ideal2[0],3)} sec", "Pass"])
                                        x = ideal2[2]
                                        Pwrs = []
                                        cnt = 0
                                        while x < templmt[1]:
                                            pla2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[x,templmt[1]],Type="Packet")
                                            if len(pla2)>2:
                                                prect = float(self.PktMethod.GetPayloadDetails(pla2[2],"PRECT")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                                Pwrs.append(prect)
                                                cnt += 1
                                                if cnt >= 10: break
                                            x += 1
                                        if len(Pwrs) > 0:
                                            Pavg = sum(Pwrs)/len(Pwrs)
                                            if len(Pwrs) < 10:
                                                res.append([f"Only {len(Pwrs)} PLA_2 packets found after MPP_XCEV_Ideal, Expected: >=10", "Fail"])
                                            res.append([f"Average of {len(Pwrs)} PLA_2 Prect's is {Pavg} W, Expected: > 24.5 W", "Pass" if Pavg > 24.5 else "Fail"])
                                    else: res.append([f"MPP_XCEV_Ideal not found", "Fail"])
                                else: res.append([f"Set_Load {int(renegpwr*1000)}mW not found", "Fail"])
                            else:res.append([f"DPCAL_PARAM packet not recevied","Fail"])
                        else:res.append([f"Extended_Power_Transmitter_Extended_Capabilities packet not recevied","Fail"])
                    else:res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response not recevied","Fail"])
                else:res.append([f"MSR(Main Mode) packet not recevied","Fail"])
            else:res.append([f"DPCAL_PARAM packet not recevied","Fail"])
        else: res.append([f"MPP_XCEV_Ideal not found", "Fail"])

    return res

def PLAOffsetCheck(self,Flow_limit,Check):
    res = []
    duration_flag = False
    removepwr = False
    duration = None
    nak_chk =False
    AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
    AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
    Flow_limit = Flow_limit
    # print("Flow_limit:",Flow_limit)

    if "after" in Check:
        TempPkt = Check['after']
    else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]
    #1.check for stabilizaton
    TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
    if len(TempPkt1)>2:
        res.append([f"Prect offset: {Check['FixedOffsetValues']['Prect']} W and RP offset: {Check['FixedOffsetValues']['RP']} W applied from {TempPkt[0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}","Pass"])
        packetCount = 0
        #2.Find PLA packts has power offset
        id = TempPkt1[2]
        while id < Flow_limit[1]:
            TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
            if len(TempPkt2)>2:
                TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                if len(TempPkt3)>2 and len(TempPkt4)>2:
                    packetCount+=1
                    RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[1]
                    Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[0]

                    RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                    Prect_Offset =  GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                    
                    Prect_Rcv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"PRECT")[0]['sDescription'])[0]
                    RP_Rcvd = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'])[0]
                    
                
                    #check for offset value are applied as like mentioned in the CTS
                    if 'FixedOffsetValues' in Check:
                        # # print(RP_Offset,Prect_Offset)
                        if RP_Offset!=Check['FixedOffsetValues']['RP'] or Prect_Offset!=Check['FixedOffsetValues']['Prect']:
                            res.append([f"PLA offset issue at {round(TempPkt2[0],3)}: RP Offset:{RP_Offset}W Expected :{Check['FixedOffsetValues']['RP']}, Prect Offset:{Prect_Offset}W Expected :{Check['FixedOffsetValues']['Prect']}W","Fail"])
                    #Ensure that the offset calculations are correct
                    if Prect_Rcv == round((Prect_Actual-Prect_Offset),3) and RP_Rcvd == round((RP_Actual-RP_Offset),3):
                    # res.append([f"PLA_2 packet found at {round(TempPkt2[0],3)}sec with Prect={Prect_Rcv}W and RP={RP_Rcvd}W, Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
                        res.append([f"PLA_2 packet found at {round(TempPkt2[0],3)}sec with Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and RP={RP_Rcvd}W,RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", "Pass"])
                    else: res.append([f"Mismatch with power values in PLA_2 packet found at {round(TempPkt2[0],3)}sec with Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and RP={RP_Rcvd}W,RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", "Fail"])
                    
                    # PLA response
                    x = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                    if x is not None:
                        if 'exp_resp' in Check:
                            if 'Response' in self.PktMethod.GetPacketType(x):
                                if Check["exp_resp"]["resp_comp"] == "EQL":
                                    if self.file_list[x]['pktType'] in Check["exp_resp"]["resp_value"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", "Pass"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", "Fail"])
                                elif Check["exp_resp"]["resp_comp"] == "NEQL":
                                    if self.file_list[x]['pktType'] not in Check["exp_resp"]["resp_value"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", "Pass"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", "Fail"])
                        else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}", "Pass"])
                        
                        # Throttle check
                        if 'Throttle' in Check:
                            if 'NAK' in self.file_list[x]['pktType']:
                                nak_chk = True
                                vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                Prect1 = vrect1*irect1

                                vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                Prect2 = vrect2*irect2
                                
                                pwr_diff = round((Prect2-Prect1)*1000,3)
                            
                                if Check['Throttle']:
                                    if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                else:
                                    if pwr_diff <= 50:
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                            elif 'ACK' in self.file_list[x]['pktType']:
                                res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", "Pass"])
                    
                    #check PLA until
                    if 'CheckDuration' in Check:
                        # # print('diff',TempPkt2[0] - TempPkt1[0])
                        duration = (TempPkt2[0] - TempPkt1[0])
                        if (TempPkt2[0] - TempPkt1[0]) >= Check['CheckDuration']:
                            duration_flag = True
                            break
                id = TempPkt2[2]+1
            else:break
        # Power remove
        if 'Remove_Power' in Check:
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
            if Check['Remove_Power']:
                if len(sd)> 2:
                    removepwr = True
                    res.append([f"PTx removed power at {round(sd[0],3)} sec", "Pass"])
                else: res.append([f"PTx does not removed power", "Fail"])
            else:
                if len(sd)> 2:
                    removepwr = True
                    res.append([f"PTx removed power at {round(sd[0],3)} sec", "Fail"])
                else: res.append([f"PTx does not removed power", "Pass"])

        if 'CheckDuration' in Check:
            if not removepwr:
                if duration_flag:
                    res.append([f"TPR monitored PLA packets for at least 1 minute after stabilizing.", "Pass"])
                else: res.append([f"TPR monitored PLA packets for only {round(duration,3)} sec after stabilizing.", "Fail"])

        if packetCount == 0: 
            res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
        elif not nak_chk:
            res.append([f"Received {packetCount} PLA Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
        else:res.append([f"Received {packetCount} PLA Packets with offset value between {self.PktMethod.Timeconvert(TempPkt1[0])} - {self.PktMethod.Timeconvert(self.file_list[Flow_limit[1]]['stopTime'])}","Pass"])
    else:res.append([f"{TempPkt[0]} packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res

    
def PLAOffsetCheck2(self,Flow_limit,Check):
    res = []
    duration_flag = False
    removepwr = False
    duration = None
    nak_chk =False
    AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
    AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
    Flow_limit = Flow_limit
    # print("Flow_limit:",Flow_limit)

    if "after" in Check:
        TempPkt = Check['after']
    else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]
    #1.check for stabilizaton
    TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
    if len(TempPkt1)>2:
        res.append([f"{Check['ReceivedPower_offset']} offset applied from {TempPkt[0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}","Pass"])
        packetCount = 0
        #2.Find PLA packts has power offset
        id = TempPkt1[2]
        while id < Flow_limit[1]:
            TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
            if len(TempPkt2)>2:
                TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                if len(TempPkt3)>2 and len(TempPkt4)>2:
                    packetCount+=1
                    Received_Power = float(self.file_list[TempPkt4[2]]['value'].split("Received:")[1].split("mW")[0].strip())
                    RP_offset = float(self.file_list[TempPkt3[2]]['value'].split("RP offset:")[1].split("W")[0].strip())*1000

                    PLA_ReceivedPower = round(float(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'].split(":")[1].split("W")[0].strip())*1000,1)
                    # print("PLA_ReceivedPower:",PLA_ReceivedPower)

                    # print("Received_Power:",Received_Power,"RP_offset:",RP_offset)
                    if abs(Check['ReceivedPower_offset']) == RP_offset:
                        # print("same offset applied")
                        pass
                    else: res.append([f"Mismatch in offset applied: {RP_offset} mW, Expected offset: {abs(Check['ReceivedPower_offset'])}", "Fail"])
                    
                    if PLA_ReceivedPower == (Received_Power + Check['ReceivedPower_offset']):
                        res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW is matching to calculated power: {(Received_Power + Check['ReceivedPower_offset'])} mW after applying {Check['ReceivedPower_offset']} mW offset at {self.PktMethod.Timeconvert(TempPkt2[0])}", "Pass"])
                    else: res.append([f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {(Received_Power + Check['ReceivedPower_offset'])} mW after applying {Check['ReceivedPower_offset']} mW offset at {self.PktMethod.Timeconvert(TempPkt2[0])}", "Fail"])

                    # PLA response
                    x = TempPkt2[2]+1
                    if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                        x += 1
                    if 'exp_resp' in Check:
                        if 'Response' in self.PktMethod.GetPacketType(x):
                            if self.file_list[x]['pktType'] in Check["exp_resp"]:
                                res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Pass"])
                            else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Fail"])

                    # Throttle check
                    if 'Throttle' in Check:
                        if 'NAK' in self.file_list[x]['pktType']:
                            nak_chk = True
                            vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                            irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                            Prect1 = vrect1*irect1

                            vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                            irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                            Prect2 = vrect2*irect2
                            
                            pwr_diff = round((Prect2-Prect1)*1000,3)
                            
                            if Check['Throttle']:
                                if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                            else:
                                if pwr_diff <= 50:
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                        elif 'ACK' in self.file_list[x]['pktType']:
                            res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", "Pass"])

                    #check PLA until
                    if 'CheckDuration' in Check:
                        # # print('diff',TempPkt2[0] - TempPkt1[0])
                        duration = (TempPkt2[0] - TempPkt1[0])
                        if (TempPkt2[0] - TempPkt1[0]) >= Check['CheckDuration']:
                            duration_flag = True
                            break
                id = TempPkt2[2]+1    
            else:break

        # Power remove
        if 'Remove_Power' in Check:
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
            if Check['Remove_Power']:
                if len(sd)> 2:
                    removepwr = True
                    res.append([f"PTx removed power at {round(sd[0],3)} sec", "Pass"])
                else: res.append([f"PTx does not removed power", "Fail"])
            else:
                if len(sd)> 2:
                    removepwr = True
                    res.append([f"PTx removed power at {round(sd[0],3)} sec", "Fail"])
                else: res.append([f"PTx does not removed power", "Pass"])

        if 'CheckDuration' in Check:
            if not removepwr:
                if duration_flag:
                    res.append([f"TPR monitored PLA packets for at least 1 minute after stabilizing.", "Pass"])
                else: res.append([f"TPR monitored PLA packets for only {round(duration,3)} sec after stabilizing.", "Fail"])

        if packetCount == 0: 
            res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
        elif not nak_chk:
            res.append([f"Received {packetCount} PLA Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
        else:res.append([f"Received {packetCount} PLA Packets with offset value between {self.PktMethod.Timeconvert(TempPkt1[0])} - {self.PktMethod.Timeconvert(self.file_list[Flow_limit[1]]['stopTime'])}","Pass"])
    else:res.append([f"{TempPkt[0]} packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res
def PLAThrottleCheck(self,Flow_limit,Check):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
    #check for the PLA packets after stabilization and ensure no throttle for ACK res and Throttle should happen for the NAK res
    res=[]
    #1.check for stabilizaton
    TempPkt1 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=Flow_limit,Type="TesterMsg")
    if len(TempPkt1)>2:
        res.append([f"Stabilization found at {round(TempPkt1[0],3)}sec","Pass"])
        packetCount = 0
        PLANAK_count = 0
        #2.Find PLA packts has power offset
        id = TempPkt1[2]
        while id < Flow_limit[1]:
            TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
            if len(TempPkt2)>2:
                packetCount+=1
                PktResponse = self.PktMethod.GetPacketResponse(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                if PktResponse is not None:
                    if 'NAK' in self.file_list[PktResponse]['pktType'] :PLANAK_count+=1
                    #find throttle voltages
                    v1 = self.PlotMethod.CalculateAVGPowerTimePeriod(self.AllChannelData,self.AllChannelData3,(TempPkt2[1]*1000)+Check['V1'], (TempPkt2[1]*1000)+Check['V1']+Check['Average'])
                    v2 = self.PlotMethod.CalculateAVGPowerTimePeriod(self.AllChannelData,self.AllChannelData3,(TempPkt2[1]*1000)+Check['V2'], (TempPkt2[1]*1000)+Check['V2']+Check['Average'])
                    # print(v1,v2) 
                    if v2-v1 <= 50:
                        #found throttle exp for NAK response
                        if "NAK" not in self.file_list[PktResponse]['pktType']:
                            res.append([f"Observed Throttle for PLA packet at {round(TempPkt2[0],3)}sec with {self.file_list[PktResponse]['pktType']} response.P1={round(v1,3)}mW Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms, P2={round(v2,3)}W Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms","Fail"])
                    else:
                        if 'NAK' in self.file_list[PktResponse]['pktType']:
                            res.append([f"Not Observed Throttle for PLA packet at {round(TempPkt2[0],3)}sec with {self.file_list[PktResponse]['pktType']} response.P1={round(v1,3)}mW Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms, P2={round(v2,3)}W Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms","Fail"])
                else:res.append([f"Response not found for the PLA packet at {round(TempPkt2[0],3)}sec","Fail"])
                id = TempPkt2[2]+1
            else:break
        if packetCount == 0:
            res.append([f"No PLA packets found after the stabilization","Fail"])
        else:res.append([f"Found {packetCount} PLA packets after the stabilization","Pass"])
        if Check['Throttle']==True:
            if PLANAK_count==0: res.append([f"PLA packet with NAK response not found","Fail"])
        elif Check['Throttle']==False:
            if PLANAK_count!=0: res.append([f"PLA packet with NAK response found","Fail"])
        
    else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res
def PLA_Throttle2(self,Flow_limit,Check):
    res = []
    duration_flag = False
    removepwr = False
    duration = None
    nak_chk =False
    AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
    AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
    
    Flow_limit = Flow_limit
    
    # print("Flow_limit:",Flow_limit)

    if "after" in Check:
        TempPkt = Check['after']
    else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]

    #1.check for stabilizaton
    TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
    if len(TempPkt1)>2:
        packetCount = 0
        #2.Find PLA packts has power offset
        id = TempPkt1[2]
        while id < Flow_limit[1]:
            TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
            if len(TempPkt2)>2:
                packetCount+=1
                # PLA response
                x = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                if x is not None:
                    if 'exp_resp' in Check:
                        if 'Response' in self.PktMethod.GetPacketType(x):
                            if Check["exp_resp"]["resp_comp"] == "EQL":
                                if self.file_list[x]['pktType'] in Check["exp_resp"]["resp_value"]:
                                    res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", "Pass"])
                                else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", "Fail"])
                            elif Check["exp_resp"]["resp_comp"] == "NEQL":
                                if self.file_list[x]['pktType'] not in Check["exp_resp"]["resp_value"]:
                                    res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", "Pass"])
                                else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", "Fail"])
                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}", "Pass"])

                # Throttle check
                if 'Throttle' in Check:
                    if 'NAK' in self.file_list[x]['pktType']:
                        nak_chk = True
                        vrect1 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                        irect1 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                        Prect1 = vrect1*irect1

                        vrect2 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                        irect2 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                        Prect2 = vrect2*irect2

                        pwr_diff = round((Prect2-Prect1)*1000,3)
                        
                        if Check['Throttle']:
                            if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                            else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                        else:
                            if pwr_diff <= 50:
                                res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                            else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                    elif 'ACK' in self.file_list[x]['pktType']:
                        res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", "Pass"])

                #check PLA until
                if 'CheckDuration' in Check:
                    # # print('diff',TempPkt2[0] - TempPkt1[0])
                    duration = (TempPkt2[0] - TempPkt1[0])
                    if (TempPkt2[0] - TempPkt1[0]) >= Check['CheckDuration']:
                        duration_flag = True
                        break
                id = TempPkt2[2]+1    
            else:break

        # Power remove
        if 'Remove_Power' in Check:
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
            if Check['Remove_Power']:
                if len(sd)> 2:
                    removepwr = True
                    res.append([f"PTx removed power at {round(sd[0],3)} sec", "Pass"])
                else: res.append([f"PTx does not removed power", "Fail"])
            else:
                if len(sd)> 2:
                    removepwr = True
                    res.append([f"PTx removed power at {round(sd[0],3)} sec", "Fail"])
                else: res.append([f"PTx does not removed power", "Pass"])

        if 'CheckDuration' in Check:
            if not removepwr:
                if duration_flag:
                    res.append([f"TPR monitored PLA packets for at least 1 minute after stabilizing.", "Pass"])
                else: res.append([f"TPR monitored PLA packets for only {round(duration,3)} sec after stabilizing.", "Fail"])

        if packetCount == 0: 
            res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
        elif not nak_chk:
            res.append([f"Received {packetCount} PLA Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
        else:res.append([f"Received {packetCount} PLA Packets with offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
    else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res

def PLAThrottleCheck_2(self,Flow_limit,Check):
    #Since the PLA thrittle calculations makes issues , only check for the PLA response
    res = []
    PLA_count = 0
    PLA_NAK = 0
    #1.check for stabilizaton
    TempPkt1 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=Flow_limit,Type="TesterMsg")
    if len(TempPkt1)>2:
        res.append([f"Stabilization found at {round(TempPkt1[0],3)}sec","Pass"])
        #check for PLA with NAK response
        id =  TempPkt1[2]
        while id < Flow_limit[1]:
            TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
            if len(TempPkt2)>2:
                PLA_count+=1
                #get response
                PLAResp = self.PktMethod.GetPacketResponse(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                if PLAResp is not None:
                    if "NAK" in self.file_list[PLAResp]['pktType']:
                        PLA_NAK+=1
                        respres = "Pass" if Check["Throttle"]==True else "Fail"
                        res.append([f"Found NAK response for the PLA packet at {round(TempPkt2[0],3)}sec",respres])
                else:res.append([f"Response not found for the PLA_2 packet at {round(TempPkt2[0],3)}sec","Fail"])
                id=TempPkt2[2]+1
            else:break
        if Check["Throttle"]==True:
            respres= "Pass" if PLA_NAK>0 else "Fail"
        else:respres= "Fail" if PLA_NAK>0 else "Pass"
        res.append([f"Found {PLA_NAK} PLA_2 packet with NAK response out of {PLA_count} PLA_2 packets between {round(self.file_list[TempPkt1[2]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",respres])
    else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res
def DPlossCalibrationCheck(self,Flow_limit,Check):
    if 'PktLimit' in Check:
        Flow_Limit = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
    else: Flow_Limit = Flow_limit

    res =[]
    #PRE CHECK
    # MODEXCAP
    Excapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Extended Capabilities",limit=Flow_limit,Type="Packet")
    if len(Excapreq)> 2:
        # res.append([f"Get Request-PTx Power Modes Extended Capabilities Packet found at {round(Excapreq[0],3)} sec", 'Pass'])
        Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=[Excapreq[2],Flow_limit[1]],Type="Response")
        if len(Excapres)> 2:
            # res.append([f"MODEXCAP {self.file_list[Excapres[2]]['value']} Packet found at {round(Excapres[0],3)} sec", 'Pass'])
            EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
            for ck in EXCAP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
            # print("EXCAP:",EXCAP)

            MSRreq = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=Flow_limit,Type="Packet")
            if len(MSRreq)> 2:
                PrefMode = self.PktMethod.GetPayloadDetails(MSRreq[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                # print("PrefMode:",PrefMode)
                # if "chks" in Check:
                #     if "ModeSwitch" in Check['chks']:
                if Check.get('ModeSwitch'):
                    if Check["ModeSwitch"]:
                        mode1 = sorted(EXCAP, key=EXCAP.get, reverse=True)[1]  # second highest potential load power
                        mode2 = max(EXCAP, key=EXCAP.get)    # highest potential load power
                        
                        # print("mode1:",mode1, "mode2:",mode2)
                        res.append([f"Potential powers in MODEXCAP is {EXCAP}", "Pass"])
                        res.append([f"Mode 1 should be {mode1} and Mode 2 should be {mode2}", "Pass"])
                        res.append([f"Main mode in MSR packet is {PrefMode}, Expected: Mode1: {mode1}", "Pass" if mode1 == PrefMode else "Fail"])


    

                # print("DPlossCalibrationCheck started")
                
                calbPoints = None
                ECAP = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=Flow_limit,Type="Response")
                if len(ECAP)>2:
                    # print("cal:",self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'cal')[0]['sRawData']))
                    CAL = self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'cal')[0]['sRawData'])
                    if CAL == 1:
                        res.append([f"Received CAL = 1(Calibration supported) in ECAP packet at {round(ECAP[0],2)} sec, expected: 1", "Pass"])
                    
                        #1. Check for CAL_ENTER  packet
                        Pkt = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",limit=Flow_limit)
                        if len(Pkt)>2:
                            if CAL == 0 or CAL != 1: res.append([f"Calibration started even though CAL = {CAL} in ECAP packet at {round(ECAP[0],2)} sec, expected: 1", "Fail"])
                            CAL_ENTER_STOP = Pkt[1]
                            
                            resume = abs(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt[2],"Resume")[0]['sRawData'])[1])
                            if resume == 0:
                                res.append([f"Received CAL_ENTER packet at {round(Pkt[0],2)} sec with resume: 0, expected: 0", "Pass"])
                            else: res.append([f"Received CAL_ENTER packet at {round(Pkt[0],2)} sec with resume: {resume}, expected: 0", "Fail"])
                        else:res.append([f"CAL_ENTER packet not recevied","Fail"])

                        #2. Get the of.of Calib points from CAL_ENTER_RSP packet
                        Pkt_res = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=Flow_limit,Type="Response")
                        if len(Pkt_res)>2:
                            calduration =int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_B")[0]['sDescription'])[0])*60
                            calbPoints = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_A")[0]['sDescription'])[0])
                            response = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Response")[0]['sRawData'])[1]
                            # print("response:",response)
                            Reason = self.PktMethod.GetPayloadDetails(Pkt_res[2],"Reason")[0]['sDescription'].split(":")[1].strip()
                            if calduration == 300 and calbPoints >= 80 and response == 1:
                                res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec","Pass"])
                            else: res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec","Fail"])
                        else:res.append([f"CAL_ENTER_RSP packet not recevied","Fail"])

                        #3.ensure the CAL_CAPTURE with count of calib points.
                        id = Pkt[2] if len(Pkt)>0 else Flow_limit[0]
                        CAL_CAPTURE_cnt = 0
                        CalStart = 0
                        CalEnd = 0
                        CalLevels = []
                        prevIndex = 0
                        #Get the calexit packet and set the liimit else consider flow limit
                        pkt_cmt = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="CMT",limit=Flow_limit)
                        
                        DPLC_type = {"DPLC1":{"Level1":{"Power":10,"Voltage":18.5},"Level2":{"Power":12.5,"Voltage":18},"Level3":{"Power":15,"Voltage":16.25},"Level4":{"Power":25,"Voltage":18}},"DPLC2":{"Level1":{"Power":10,"Voltage":18.5},"Level2":{"Power":12.5,"Voltage":18},"Level3":{"Power":15,"Voltage":16.25},"Level4":{"Power":25,"Voltage":18}},"DPLC3":{"Level1":{"Power":8,"Voltage":18},"Level2":{"Power":10,"Voltage":18.5},"Level3":{"Power":12.5,"Voltage":18},"Level4":{"Power":15,"Voltage":16.5}},"DPLC4":{"Level1":{"Power":9,"Voltage":15.4},"Level2":{"Power":12,"Voltage":15.6},"Level3":{"Power":15,"Voltage":15.8},"Level4":{"Power":20,"Voltage":16.1}}}
                        TempLimit = [id,len(self.file_list)-1]#[id,Flow_limit[1]]
                        # print('TempLimit',TempLimit)
                        sts_chk = []
                        
                        newlmt = TempLimit
                        for level,pwr in DPLC_type[Check["DPLC"]].items():
                            if Check.get('skiplevel'):
                                if level in Check["skiplevel"]:
                                    # print("skipping")
                                    continue
                            res.append([f"{Check["DPLC"]}, {level}: {pwr['Power']} W, {pwr['Voltage']} V calibration started ","Pass"])
                            set_load = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(pwr['Power']*1000)}mW",limit=newlmt,Type='TesterMsg')
                            # print("set_load:",set_load)
                            if len(set_load)>2:
                                res.append([f"Set_Load {int(pwr['Power']*1000)}mW packet found at {round(set_load[0],3)} sec","Pass"])
                                id = set_load[2]
                                ccnt = 0
                                while id < newlmt[1]:
                                    if 'CAL_CAPTURE' in self.file_list[id]['pktType']:
                                        # # print("ID:",id)
                                        if self.PktMethod.GetPacketType(id)=="Packet":
                                            ccnt += 1
                                            prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id,"PRECT")[0]['sDescription'])[0]
                                            vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id,"VRECT")[0]['sDescription'])[0]
                                            # print("prect:",prect, ccnt)
                                            # if abs(prect - pwr['Power']) > 0.01 * pwr['Power'] or abs(vrect - pwr['Voltage']) > 0.01 * pwr['Voltage']:
                                            if prect <= (pwr['Power']-(pwr['Power']*0.01)) or vrect <= (pwr['Voltage']-(pwr['Voltage']*0.01)):
                                                res.append([f"CAL_CAPTURE power:{prect}W, voltage:{vrect}W is out range found at {round(self.file_list[id]['startTime'],3)} sec, Expected: Prect>={pwr['Power']*(1-0.01)}W and Vrect>={pwr['Voltage']*(1-0.01)}V","Fail"])
                                                break
                                            if CAL_CAPTURE_cnt == 1: CalStart = round(self.file_list[id]['startTime'],3)
                                            CAL_CAPTURE_cnt+=1
                        
                                        if 'CAL_CAPTURE_RSP' in self.file_list[id+1]['pktType']:
                                            status = abs(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id+1,"Status")[0]['sRawData'])[0])
                                            if status != 0:
                                                sts_chk.append(status)
                                                res.append([f"CAL_CAPTURE_RSP response is received with status:{status} for CAL_CAPTURE packet at index@{id+1}, expected:0", "Fail"])
                                        if ccnt >= 20: 
                                            newlmt = [id,TempLimit[1]]
                                            res.append([f"All CAL_CAPTURE packets have Prect in {round(pwr['Power']-(0.01*pwr['Power']),3)} W - {round(pwr['Power']+(0.01*pwr['Power']),3)} W, Vrect in {round(pwr['Voltage']-(0.01*pwr['Voltage']),3)} V - {round(pwr['Voltage']+(0.01*pwr['Voltage']),3)} V, Expected: 1% of {pwr['Power']}W and 1% of {pwr['Voltage']} V", "Pass"])
                                            res.append([f"Received {ccnt} CAL_CAPTURE packets in {level}, Expected: 20", "Pass"])
                                            
                                            break
                                    id+=1

                                # Renegotiation
                                if (Check["DPLC"] != "DPLC3" and level == "Level3") or (Check["DPLC"] == "DPLC3" and level == "Level4"):
                                    calop = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="CMT",limit=newlmt)
                                    if len(calop)>2:
                                        res.append([f"CAL_OP(CMT) found at index@{calop[2]}", "Pass"])
                                        calop_rsp = self.PktMethod.GetPacketDetails(packet="CAL_OP_RSP",limit=[calop[2],newlmt[1]],Type='Response')
                                        if len(calop_rsp)>2:
                                            res.append([f"CAL_OP_RSP found at index@{calop_rsp[2]}", "Pass"])
                                            ECAP2 = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=[calop_rsp[2],newlmt[1]],Type="Response")
                                            if len(ECAP2)>2:
                                                negpwr2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP2[2],'Negotiable_Load_Power')[0]['sDescription'])[0]
                                                # print("negpwr2:",negpwr2)
                                                res.append([f"Extended_Power_Transmitter_Extended_Capabilities with Negotiable_Load_Power: {negpwr2}W found at index@{ECAP2[2]}", "Pass"])
                                                reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[ECAP2[2],newlmt[1]])
                                                if len(reneg)>2:
                                                    res.append([f"Renegotiate packet found at index@{reneg[2]}", "Pass"])
                                                    respid = self.PktMethod.GetPacketResponse(reneg,[reneg[2]+1,newlmt[1]])
                                                    if respid is not None:
                                                        if self.file_list[respid]['pktType'] =="ACK":
                                                            res.append([f"ACK response found at index@{respid}", "Pass"])
                                                            srqepl = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=[respid,newlmt[1]])
                                                            if len(srqepl)>2:
                                                                res.append([f"SRQ(Extended Power Level Selection) found at index@{srqepl[2]}", "Pass"])
                                                                respid2 = self.PktMethod.GetPacketResponse(srqepl,[srqepl[2]+1,newlmt[1]])
                                                                if respid2 is not None:
                                                                    if self.file_list[respid2]['pktType'] =="ACK":
                                                                        res.append([f"ACK response found at index@{respid2}", "Pass"])
                                                                        srqen = self.PktMethod.GetPacketDetails(packet="SRQ",value="End Negotiation",limit=[respid2,newlmt[1]])
                                                                        if len(srqen)>2:
                                                                            res.append([f"SRQ(End Negotiation) found at index@{srqen[2]}", "Pass"])
                                                                            respid3 = self.PktMethod.GetPacketResponse(srqen,[srqen[2]+1,newlmt[1]])
                                                                            if respid3 is not None:
                                                                                if self.file_list[respid3]['pktType'] =="ACK":
                                                                                    res.append([f"ACK response found at index@{respid3}", "Pass"])

                                                                                    if Check["DPLC"] == "DPLC1" and level == "Level3":
                                                                                        continue
                                                                                    renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(negpwr2*1000)}mW",limit=[respid3,newlmt[1]],Type='TesterMsg')
                                                                                    # print("renegload:",renegload)
                                                                                    if len(renegload)>2:
                                                                                        self.GetInitailVoltage(Check['flow'],[renegload[2],newlmt[1]])
                                                                                        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
                                                                                        self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
                                                                                        irect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                                                                                        vrect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData)
                                                                                        power = round(vrect[0]*irect[0],3)
                                                                                        # print("vrect:",vrect,"irect:",irect,"power:",power)
                                                                                        res.append([f"Prect after control stabilization is {power} W at {round(self.file_list[self.stability]['startTime'],3)} sec, Expected: >= {negpwr2}W", "Pass" if power>=negpwr2 else "Fail"])
                                                                                    else: res.append([f"Set_Load {int(negpwr2*1000)}mW not found", "Fail"])



                                                                                    if Check.get('ModeSwitch'):
                                                                                        if Check["ModeSwitch"]:
                                                                                            if Check.get('skiplevel'):
                                                                                                # if level in Check["skiplevel"]:
                                                                                                index = list(DPLC_type[Check["DPLC"]].keys()).index(level)
                                                                                                # print("index:",index,list(DPLC_type[Check["DPLC"]].keys())[index+1])
                                                                                                if list(DPLC_type[Check["DPLC"]].keys())[index+1] in Check["skiplevel"]:
                                                                                                    # newlmt = [renegload[2],TempLimit[1]]
                                                                                                    continue
                                                                                        
                                                                                            calext = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",value="Clear: Retain CAL points",limit=[respid3,newlmt[1]])
                                                                                            if len(calext)>2:
                                                                                                clear = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(calext[2],"clear")[0]['sRawData'])[0]
                                                                                                res.append([f"CAL_EXIT(Clear: Retain CAL points) with clear: {clear} found at index@{calext[2]}, Expected: 0", "Pass" if clear == 0 else "Fail"])
                                                                                            else: res.append([f"CAL_EXIT(Clear: Retain CAL points) not found", "Fail"])
                                                                                            MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=[respid3,newlmt[1]],Type="Packet")
                                                                                            if len(MSRreq2)> 2:
                                                                                                PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                                                                                                # print("PrefMode2:",PrefMode2)
                                                                                                res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: Mode2: {mode2}", "Pass" if mode2 == PrefMode2 else "Fail"])
                                                                                                MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],newlmt[1]],Type="Response")
                                                                                                if len(MSS2)> 2:
                                                                                                    res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", "Pass"])

                                                                                                    Pkt = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",value="Resume: 1",limit=[MSS2[2],newlmt[1]])
                                                                                                    if len(Pkt)>2:
                                                                                                        Resume = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt[2],"Resume")[0]['sRawData'])[1]
                                                                                                        # print("Resume:",Resume)
                                                                                                        res.append([f"CAL_ENTER(Resume: 1) with Resume: {Resume} found at index@{Pkt[2]}, Expected: 1", "Pass" if Resume == 1 else "Fail"])
                                                                                                        Pkt_res = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=[Pkt[2],newlmt[1]],Type="Response")
                                                                                                        if len(Pkt_res)>2:
                                                                                                            calduration =int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_B")[0]['sDescription'])[0])*60
                                                                                                            calbPoints = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_A")[0]['sDescription'])[0])
                                                                                                            response = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Response")[0]['sRawData'])[1]
                                                                                                            # print("response:",response)
                                                                                                            Reason = self.PktMethod.GetPayloadDetails(Pkt_res[2],"Reason")[0]['sDescription'].split(":")[1].strip()
                                                                                                            if calduration == 300 and calbPoints >= 80 and response == 1:
                                                                                                                res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec","Pass"])
                                                                                                            else: res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec","Fail"])
                                                                                                            Pktop = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="Operation: INIT",limit=[Pkt_res[2],newlmt[1]])
                                                                                                            if len(Pktop)>2:
                                                                                                                res.append([f"CAL_OP(Operation: INIT) found at index@{Pktop[2]}", "Pass"])
                                                                                                                Pktop_res = self.PktMethod.GetPacketDetails(packet="CAL_OP_RSP",limit=[Pktop[2],newlmt[1]],Type="Response")
                                                                                                                if len(Pktop_res)>2:
                                                                                                                    newlmt = [Pktop_res[2],TempLimit[1]]
                                                                                                                    res.append([f"CAL_OP_RSP found at index@{Pktop_res[2]}", "Pass"])
                                                                                                                else: res.append([f"CAL_OP_RSP not found", "Fail"])
                                                                                                            else: res.append([f"CAL_OP(Operation: INIT) not found", "Fail"])
                                                                                                        else: res.append([f"CAL_OP_RSP not found", "Fail"])
                                                                                                    else: res.append([f"CAL_ENTER(Resume: 1) not found", "Fail"])

                                                                                                else: res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response not received", "Fail"])
                                                                                            else: res.append([f"MSR(Main mode) packet not found", "Fail"])

                                                                                else: res.append([f"NAK response received", "Fail"])
                                                                            else: res.append([f"Response not found for SRQ(End Negotiation)", "Fail"])
                                                                        else: res.append([f"SRQ(End Negotiation) not found", "Fail"])
                                                                    else: res.append([f"NAK response received", "Fail"])
                                                                else: res.append([f"Response not found for SRQ(Extended Power Level Selection)", "Fail"])
                                                            else: res.append([f"SRQ(Extended Power Level Selection) not found", "Fail"])
                                                        else: res.append([f"NAK response received", "Fail"])
                                                    else: res.append([f"Response not found for Renegotiate", "Fail"])
                                                else: res.append([f"Renegotiate not found", "Fail"])
                                            else: res.append([f"Extended_Power_Transmitter_Extended_Capabilities not found", "Fail"])
                                        else: res.append([f"CAL_OP_RSP not found", "Fail"])
                                    else: res.append([f"CAL_OP(CMT) not found", "Fail"])



                            else: res.append([f"{level}, {int(pwr['Power']*1000)}mW is not set","Fail"])

                        if len(sts_chk) == 0:
                            res.append(["Received CAL_CAPTURE_RSP responses with status:0 for all CAL_CAPTURE packets, expected:0", "Pass"])

                        
                        if calbPoints is not None:
                            if Check.get('skiplevel'):
                                pointlmt = (4-len(Check["skiplevel"]))*20
                            else: pointlmt = 80
                            if CAL_CAPTURE_cnt >= pointlmt:
                                res.append([f"Recived all the {CAL_CAPTURE_cnt} CAL_CAPTURE packets, Expected: >= {pointlmt}","Pass"])
                            else: 
                                #If all calib points not recvd, then check for the renego happened for 15W else it's Fail
                                res.append([f"Mismatch in CAL_CAPTURE packet count, Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}, Expected: >= {pointlmt}","Fail"])
                        else: res.append([f"CAL_ENTER_RSP packet not recevied, Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}","Fail"])

                        
                        #6.Verify CAL_EXIT packet 
                        pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",value="Clear: Retain CAL points",limit=newlmt)
                        if len(pkt_exit)>2:
                            clear = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(pkt_exit[2],"clear")[0]['sRawData'])[0]
                            res.append([f"CAL_EXIT(Clear: Retain CAL points) with clear: {clear} found at index@{pkt_exit[2]}", "Pass"])
                        
                            #6b, Ensure the CAlib duration which is mentioned on the CAL_ENTER_RSP packet , and calculate the interval btw CAL_ENTER to CAL_EXIT
                            if CAL_ENTER_STOP and calduration:
                                if (pkt_exit[0]-CAL_ENTER_STOP) > calduration:
                                    res.append([f"Calculated Calib duration is {round(pkt_exit[0]-CAL_ENTER_STOP,2)}Sec, which is not in limit of {calduration}Sec","Fail"])
                                else:res.append([f"Calculated Calib duration is {round(pkt_exit[0]-CAL_ENTER_STOP,2)}Sec, which is in limit of {calduration}Sec","Pass"])
                            else:res.append([f"CAL_ENTER Packet or CAL duration not found","Pass"])
                        else: res.append([f"CAL_EXIT(Clear: Retain CAL points) not found", "Fail"])

                        #7.Check the Alpha and Beta values from the DPCAL_PARAM packet.
                        pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=newlmt,Type="Response")
                
                        if len(pkt_DPM)>2:
                            alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                            beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                            if any(res == 0 for res in [alpha,beta]):
                                res.append([f"The DPCAL_PARAM packet wit Alpha: {alpha}, Beta: {beta} received at {round(pkt_DPM[0],2)}sec","Fail"])
                            else:res.append([f"The DPCAL_PARAM packet with Alpha: {alpha}, Beta: {beta} received at {round(pkt_DPM[0],2)}sec","Pass"])
                        else:res.append([f"DPCAL_PARAM packet not recevied","Fail"])
                    

                        
                    elif CAL == 0:
                        res.append([f"Received CAL = 0(Calibration not supported) in ECAP packet at {round(ECAP[0],2)} sec, expected: 0", "Pass"])
                    else: res.append([f"Received CAL = {CAL} in ECAP packet at {round(ECAP[0],2)} sec, expected: 0 or 1", "Fail"])
    return res

def CAL_CAPCheck(self,Flow_limit,Check):
    res = []
    pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM [0x54]",limit=Flow_limit,Type="Response")
    CAL_PKT = self.PktMethod.GetPacketDetails(packet="CAL_CAP [0x43]",limit=[pkt_DPM[2],Flow_limit[1]],Type="Response")
    # # print("pkt_CALCAP:",pkt_DPM)
    # # print("CAL_PKT:",CAL_PKT)
    # # print("hvjk",self.PktMethod.GetPayloadDetails(CAL_PKT[2],"CAL_M0: Calibration Mode 0 is supported"))
    if len(CAL_PKT) > 1:
        CAL_M0 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(CAL_PKT[2],"CAL_M0: Calibration Mode 0 is supported")[0]['sRawData'])[1]
        if CAL_M0 == 1:
            res.append([f"CAL_M0: Found CAL_CAP [0x43] packet at @index {CAL_PKT[2]} and CAL_M0 is set to {CAL_M0}, Expected: CAL_M0 = 1", "Pass"])
        else: res.append([f"CAL_M0: Found CAL_CAP [0x43] packet at @index {CAL_PKT[2]} and CAL_M0 is set to {CAL_M0}, Expected: CAL_M0 = 1", "Fail"])
    else: res.append("CAL_CAP [0x43] packet is not found.", "Fail")
    # # print("CAL_CAPCheck:",res)
    return res

def CalculateGainG(self,Flow_limit,Check):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    res = []
    #1. Get mentiond load
    loadpkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Load']}",limit=Flow_limit,Type="TesterMsg")
    if len(loadpkt)>2:
        res.append([f"Found set load {Check['Load']}mA packet at {round(loadpkt[0],3)}Sec","Pass"])
        #find the Inv packet
        InvPkt = self.PktMethod.GetPacketDetails(packet="Inverter_Voltage",limit=[loadpkt[2],Flow_limit[1]],Type="Response")
        if len(InvPkt)>2:
            res.append([f"The Inverter_Voltage packet found at {round(InvPkt[0],3)}sec","Pass"])
            #Calculate G 
            Vinv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(InvPkt[2],"Vinv")[0]['sDescription'])[0]
            Vrect = self.PktMethod.CalculateVoltTwindow(InvPkt[2]-1,self.AllChannelData)
            ChkRes = CommonMethods.check_measure(Check['expected'],round(Vrect[0]/Vinv,2),Check['comp'])
            res.append([f"Calculated G is {round(Vrect[0]/Vinv,2)} limit {ChkRes[2]}, where Vinv={Vinv}V measured at {round(InvPkt[0],3)}sec and Vrect={Vrect[0]}V measured at {round(self.file_list[InvPkt[2]-1]['startTime'],3)}sec",ChkRes[1]])
        else:res.append([f"The Inverter_Voltage packet not found between","Fail"])
    else:res.append([f"Set load {Check['Load']}mA packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}","Fail"])
    return res
def PrectWithLoad(self,Flow_limit,Check):
    res=[]
    #1. Get mentiond load
    TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load 1040",limit=Flow_limit,Type="TesterMsg")
    if len(TempPkt1)>2:
        #iterat with all prects
        cnt = 1
        res.append([f"Found set load 1040mA packet at {round(TempPkt1[0],3)}Sec","Pass"])
        TempLimit = [TempPkt1[2]+1,Flow_limit[1]]
        for prect in Check['expected']:
            TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {prect['Load']}",limit=TempLimit,Type="TesterMsg")
            # print("TempPkt2:",TempPkt2)
            if len(TempPkt2)>2:
                res.append([f"Prect_{cnt}:Found set load {prect['Load']}mW packet at {round(TempPkt2[0],3)}Sec","Pass"])
                #find the stabilization
                TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Flow_limit[1]],Type="TesterMsg")
                # print("TempPkt3:",TempPkt3)
                if len(TempPkt3)>2:
                    res.append([f"Prect_{cnt}:Stabilization found at {round(TempPkt3[0],3)}sec","Pass"])
                    #Get Prect from PLA
                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2],Flow_limit[1]])
                    # print("TempPkt4:",TempPkt4)
                    if len(TempPkt4)>2:
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                        ChkRes = CommonMethods.check_measure(prect['exp'],Prect,prect['comp'])
                        res.append([f"Prect_{cnt}:Found PLA_2 packet at {round(TempPkt4[0],3)}sec with Prect {Prect}W, limit {ChkRes[2]}W",ChkRes[1]])
                    else:res.append([f"Prect_{cnt}:PLA packet not found between {round(TempPkt3[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}","Fail"])
                else:res.append([f"Prect_{cnt}:Stabilization is not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}","Fail"])
                TempLimit=[TempPkt2[2]+1,Flow_limit[1]]
            else:res.append([f"Prect_{cnt}:Set load {prect['Load']}mA packet not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}","Fail"])
            cnt+=1
    else:res.append([f"Set load {Check['Inputs']['AFLoad']}mA packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}","Fail"])
    # # print("PrectWithLoad:",res)
    return res
def PrectFall(self,Flow_limit,Check):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
    res=[]
    x = 1
    for chk in Check['expected']:
        if "LimitType" in chk:
            Limit = self.PktMethod.GetLimits(chk['LimitType'],chk,Flow_limit)
        else: Limit = Flow_limit
        SRQ = self.PktMethod.GetPacketDetails(packet="SRQ",value="Control Gain",limit=Limit)
        if len(SRQ)>2:
            resp = self.PktMethod.GetPacketResponse(SRQ,[SRQ[2]+1,Limit[1]])
            if resp is not None:
                if self.file_list[resp]['pktType'] =="ACK":
                    res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(SRQ[0],3)}sec","Pass"])
                else:res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(SRQ[0],3)}sec","Fail"])
            else:res.append([f"Response not found for SRQ_Control Gain packet at {round(SRQ[0],3)}sec","Fail"])
            gtarget = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(SRQ[2],'G_TARGET')[0]['sDescription'])[0]

            #1. Get potential load power
            TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Extended_Power_Transmitter_Extended_Capabilities",limit=Limit,Type="Response")
            # print("TempPkt1:",TempPkt1)
            PotLoad = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],"Potential Load Power value: 25W")[0]['sDescription'])[0]*1000)
            # print("PotLoad:",PotLoad)
            res.append([f"Potential load power in Extended_Power_Transmitter_Extended_Capabilities is {PotLoad}mW", "Pass"])
            if len(TempPkt1)>2:
                TempLimit = [TempPkt1[2],Limit[1]]
                TempPkt2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {PotLoad}mW:ILim:Enabled",limit=TempLimit,Type="TesterMsg")
                # print("PrecLimit:",TempPkt2)
                if len(TempPkt2) > 2:
                    res.append([f"Set_load found for {PotLoad}mW @index {TempPkt2[2]}, Expected power: {PotLoad}mW i.e, ECAP[potential load power].", "Pass"])
                    #find the stabilization
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Limit[1]],Type="TesterMsg")
                    # print("TempPkt3:",TempPkt3)
                    if len(TempPkt3)>2:
                        res.append([f"Control stabilized at @index {TempPkt3[2]}", "Pass"])
                        TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2]-15,TempPkt3[2]+15],Type="Packet")
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                        # print("Prect:",Prect)
                        ChkRes = CommonMethods.check_measure([(PotLoad/1000)-0.5],Prect,"GTEQL")
                        res.append([f"Found PLA_2 packet at {round(TempPkt4[0],3)}sec with Prect {Prect}W, Expected power in ECAP:{PotLoad}mW", ChkRes[1]])
                        # TPR ramp its load power within a 50 microsecond period down to ECAP[Potential Load Power]/2
                        TempPkt5 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(PotLoad/2)}mW:ILim:Disabled",limit=[TempPkt3[2],Limit[1]],Type="TesterMsg")
                        # print("TempPkt5:",TempPkt5)
                        if len(TempPkt5)>2:
                            res.append([f"Set_load found for {int(PotLoad/2)}mW @index {TempPkt5[2]}, Expected power: {int(PotLoad/2)}mW, i.e, ECAP[potential load power]/2.", "Pass"])
                            VrectTarget = [] #V
                            # Vrect1 = self.PktMethod.GetPacketDetails(packet="Vrect_VTarget",limit=[TempPkt5[2],Flow_limit[1]],Type="TesterMsg")
                            id = TempPkt5[2]
                            Vrect = []

                            cnt = 0
                            while id != Limit[1]:
                                if "Vrect_VTarget" in self.file_list[id].get('pktType'):
                                    # print("Vrect_VTarget:",self.file_list[id].get('value'))
                                    match = re.search(r"Target_voltage:\s*([\d.]+)V.*Rectified_voltage:\s*([\d.]+)V", self.file_list[id].get('value'))
                                    VrectTarget.append(float(match.group(1)))
                                    Vrect.append(float(match.group(2)))
                                    
                                    cnt += 1
                                    if cnt == 2: break
                                id += 1
                            # print("match:",VrectTarget,Vrect)
                            Vrec1del = Vrect[1]-Vrect[0]
                            validation = round(abs(Vrec1del/(VrectTarget[0]-Vrect[0])-gtarget),3)
                            # print("validation:",validation)
                            res.append([f"Vrect_target_{x}: {VrectTarget[0]}V, Vrect_{x}: {Vrect[0]}V, Vrect_after_{x}: {Vrect[1]}V", 'Pass'])
                            ChkRes = CommonMethods.check_measure([0.4],validation,"LTEQL")
                            res.append([f"|∆Vrect_{x} / (Vrect_target_{x}- Vrect_{x})- g_target_{x}| = {ChkRes[3]}, Expected: {ChkRes[2]}", ChkRes[1]])
                            
                            CE = self.PktMethod.GetPacketDetails(packet=f"Extended Control Error",limit=[Limit[1],TempPkt5[2]],Type="Packet")
                            # print("Extended Control Error:",CE)
                            if len(CE) > 2:
                                voltage = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                                current = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData3)
                                # # print("TIME:",self.AllChannelData["Interval"]*voltage[1])
                                # print("power(W):",voltage[0]*current[0])
                                if voltage[0]*current[0] >= float(PotLoad/2000):
                                    res.append([f"After control stabilization, power is {round((voltage[0]*current[0]),3)}W, Limit: >= {float(PotLoad/2000)}W", "Pass"])
                                else: res.append([f"After control stabilization, power is {voltage[0]*current[0]}W Limit: >= {float(PotLoad/2000)}W", "Fail"])
                            else: res.append([f"Control not stabilized for {int(PotLoad/2)}mW", "Fail"])

                        else: res.append([f"Set_Load {int(PotLoad/2)}mW packet not found", "Fail"])   
                    else: res.append([f"MPP_XCEV_Ideal packet not found", "Fail"])
                else: res.append([f"Set_Load {PotLoad}mW packet not found", "Fail"])
            else: res.append([f"Extended_Power_Transmitter_Extended_Capabilities packet not found", "Fail"])
        else: res.append([f"SRQ Control Gain packet not found", "Fail"])
        x += 1
    return res

def MODEXCAPCheck(self,Flow_limit,Check):
    res=[]
    # MODECAP
    Ecapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Capabilities",limit=Flow_limit,Type="Packet")
    if len(Ecapreq)> 2:
        res.append([f"Get Request-PTx Power Modes Capabilities Packet found at {round(Ecapreq[0],3)} sec", 'Pass'])
        Ecapres = self.PktMethod.GetPacketDetails(packet="MODECAP",value="Active Main Mode:",limit=[Ecapreq[2],Flow_limit[1]],Type="Response")
        if len(Ecapres)> 2:
            res.append([f"MODECAP {self.file_list[Ecapres[2]]['value']} Packet found at {round(Ecapres[0],3)} sec", 'Pass'])
            ECAP = {"LPM":"","NPM":"","HPM":"","CPM":""}
            for ck in ECAP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(Ecapres[2],ck)
                # print(ck,":",self.PktMethod.hex_to_decimal(payloadDetails[0]['sRawData']))
                ECAP[ck] = self.PktMethod.hex_to_decimal(payloadDetails[0]['sRawData'])
            # print(ECAP)
            res.append([f"ECAP values: {ECAP}", 'Pass'])
        else: res.append([f"MODECAP Packet not found", 'Fail'])
    else: res.append([f"Get Request-PTx Power Modes Capabilities Packet not found", 'Fail'])

    # MODEXCAP
    Excapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Extended Capabilities",limit=Flow_limit,Type="Packet")
    if len(Excapreq)> 2:
        res.append([f"Get Request-PTx Power Modes Extended Capabilities Packet found at {round(Excapreq[0],3)} sec", 'Pass'])
        Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=[Excapreq[2],Flow_limit[1]],Type="Response")
        if len(Excapres)> 2:
            res.append([f"MODEXCAP {self.file_list[Excapres[2]]['value']} Packet found at {round(Excapres[0],3)} sec", 'Pass'])
            EXCAP = {"LPMVoltage_Ref0":"","LPMVoltage_Ref1":"","Low_Power_Mode":"","NPMVoltage_Ref0":"","NPMVoltage_Ref1":"","Nominal_Power_Mode":"","HPMVoltage_Ref0":"","HPMVoltage_Ref1":"","High_Power_Mode":"","CPMVoltage_Ref0":"","CPMVoltage_Ref1":"","Continuous_Power_Mode":""}
            for ck in EXCAP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
            # print(EXCAP)
            res.append([f"EXCAP values: {EXCAP}", 'Pass'])
        else: res.append([f"MODEXCAP Packet not found", 'Fail'])
    else: res.append([f"Get Request-PTx Power Modes Extended Capabilities Packet not found", 'Fail'])

    # GMP
    GMPreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Gain Measurement Parameters",limit=Flow_limit,Type="Packet")
    if len(GMPreq)> 2:
        res.append([f"Get Request-PTx Gain Measurement Parameters Packet found at {round(GMPreq[0],3)} sec", 'Pass'])
        GMPres = self.PktMethod.GetPacketDetails(packet="GMP",limit=[Ecapreq[2],Flow_limit[1]],Type="Response")
        if len(GMPres)> 2:
            res.append([f"GMP {self.file_list[GMPres[2]]['value']} Packet found at {round(GMPres[0],3)} sec", 'Pass'])
            GMP = {"G_NPM_CO":"","G_HPM_CO":"","G_CPM_CO":""}
            for ck in GMP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(GMPres[2],ck)
                # print(ck,":",float(payloadDetails[0]['sDescription'].split(":")[1].strip()))
                GMP[ck] = float(payloadDetails[0]['sDescription'].split(":")[1].strip())
            # print(GMP)
            res.append([f"GMP values: {GMP}", 'Pass'])
        else: res.append([f"GMP Packet not found", 'Fail'])
    else: res.append([f"Get Request-PTx Gain Measurement Parameters Packet not found", 'Fail'])


    if ECAP == {'LPM': 1, 'NPM': 0, 'HPM': 0, 'CPM': 0}:
        res.append([f"Power modes in MODECAP packet are {ECAP}", 'Pass'])
        if EXCAP["LPMVoltage_Ref0"] != 0:
            res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", 'Fail'])

        if EXCAP["LPMVoltage_Ref1"] != 0:
            res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", 'Fail'])
        
        if EXCAP["Low_Power_Mode"] != 0 and EXCAP["Low_Power_Mode"] <= 10:
            res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: != 0 W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", 'Pass'])
        else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: != 0 W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", 'Fail'])

        if all(EXCAP[key] == 0 for key in EXCAP if key not in ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]):
            res.append([f'All values are equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]', "Pass"])
        else: res.append([f'All values are not equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]', "Fail"])

        if all(GMP[key] == 0 for key in GMP):
            res.append([f'All values are equal to zero in GMP', "Pass"])
        else: res.append([f'All values are not equal to zero in GMP', "Fail"])

    elif ECAP == {'LPM': 1, 'NPM': 1, 'HPM': 0, 'CPM': 0}:
        res.append([f"Power modes in MODECAP packet are {ECAP}", 'Pass'])
        if EXCAP["LPMVoltage_Ref0"] != 0:
            res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", 'Fail'])

        if EXCAP["LPMVoltage_Ref1"] != 0:
            res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", 'Fail'])  

        if EXCAP["Low_Power_Mode"] != 0 and EXCAP["Low_Power_Mode"] <= 10:
            res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: != 0 and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: <= 10", 'Pass'])
        else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: != 0 and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: <= 10", 'Fail'])

        if EXCAP["NPMVoltage_Ref0"] != 0:
            res.append([f"NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: != 0 V", 'Fail'])

        if EXCAP["NPMVoltage_Ref1"] != 0:
            res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V, Expected: != 0 V", 'Fail'])  

        if EXCAP["Nominal_Power_Mode"] != 0:
            res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, Expected: != 0 W", 'Pass'])
        else: res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, Expected: != 0 W", 'Fail']) 

        if all(EXCAP[key] == 0 for key in EXCAP if key not in ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode","NPMVoltage_Ref0","NPMVoltage_Ref1","Nominal_Power_Mode"]):
            res.append([f'All values are equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode","NPMVoltage_Ref0","NPMVoltage_Ref1","Nominal_Power_Mode"]', "Pass"])
        else: res.append([f'All values are not equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode","NPMVoltage_Ref0","NPMVoltage_Ref1","Nominal_Power_Mode"]', "Fail"])

        if EXCAP["LPMVoltage_Ref1"] >= EXCAP["NPMVoltage_Ref0"]:
            res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", 'Pass'])
        else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", 'Fail'])

        if EXCAP["Nominal_Power_Mode"] > EXCAP["Low_Power_Mode"]:
            res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: NPM Potential Load Power > LPM Potential Load Power", 'Pass'])
        else: res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: NPM Potential Load Power > LPM Potential Load Power", 'Fail'])

        if GMP["G_NPM_CO"] != 0:
            res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", 'Pass'])
        else: res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", 'Fail'])

        if GMP["G_HPM_CO"] == 0:
            res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", 'Pass'])
        else: res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", 'Fail'])

        if GMP["G_CPM_CO"] == 0:
            res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", 'Pass'])
        else: res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", 'Fail'])

    elif ECAP == {'LPM': 1, 'NPM': 1, 'HPM': 1, 'CPM': 0}:
        res.append([f"Power modes in MODECAP packet are {ECAP}", 'Pass'])
        if EXCAP["CPMVoltage_Ref0"] == 0:
            res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: = 0 V", 'Pass'])
        else: res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: = 0 V", 'Fail'])
        if EXCAP["CPMVoltage_Ref1"] == 0:
            res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: = 0 V", 'Pass'])
        else: res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: = 0 V", 'Fail'])  
        if EXCAP["Continuous_Power_Mode"] == 0:
            res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", 'Pass'])
        else: res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", 'Fail']) 
        if all(EXCAP[key] != 0 for key in EXCAP if key not in ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]):
            res.append([f'All values are NOT equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', "Pass"])
        else: res.append([f'All values are equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', "Fail"])
        if EXCAP["LPMVoltage_Ref1"] >= EXCAP["NPMVoltage_Ref0"]:
            res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", 'Pass'])
        else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", 'Fail'])
        if EXCAP["NPMVoltage_Ref1"] >= EXCAP["HPMVoltage_Ref0"]:
            res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V and HPMVoltage_Ref0 is {EXCAP["HPMVoltage_Ref0"]} V, Expected: NPMVoltage_Ref1 >= HPMVoltage_Ref0", 'Pass'])
        else: res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V and HPMVoltage_Ref0 is {EXCAP["HPMVoltage_Ref0"]} V, Expected: NPMVoltage_Ref1 >= HPMVoltage_Ref0", 'Fail'])
        if EXCAP["High_Power_Mode"] > EXCAP["Nominal_Power_Mode"] > EXCAP["Low_Power_Mode"]:
            res.append([f"HPM Potential Load Power is {EXCAP["High_Power_Mode"]} W, NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W Expected: HPM Potential Load Power > NPM Potential Load Power > HPM Potential Load Power", 'Pass'])
        else: res.append([f"HPM Potential Load Power is {EXCAP["High_Power_Mode"]} W, NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W Expected: HPM Potential Load Power > NPM Potential Load Power > HPM Potential Load Power", 'Fail'])
        if EXCAP["Low_Power_Mode"] <= 10:
            res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", 'Pass'])
        else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", 'Fail']) 
        if GMP["G_NPM_CO"] != 0:
            res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", 'Pass'])
        else: res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", 'Fail'])
        if GMP["G_HPM_CO"] != 0:
            res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: != 0", 'Pass'])
        else: res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: != 0", 'Fail'])
        if GMP["G_CPM_CO"] == 0:
            res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", 'Pass'])
        else: res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", 'Fail'])

    elif ECAP == {'LPM': 1, 'NPM': 1, 'HPM': 1, 'CPM': 1}:
        res.append([f"Power modes in MODECAP packet are {ECAP}", 'Pass'])
        if EXCAP["CPMVoltage_Ref0"] != 0:
            res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: != 0 V", 'Fail'])
        if EXCAP["CPMVoltage_Ref1"] != 0:
            res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: != 0 V", 'Pass'])
        else: res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: != 0 V", 'Fail'])  
        if EXCAP["Continuous_Power_Mode"] != 0:
            res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", 'Pass'])
        else: res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", 'Fail']) 
        if all(EXCAP[key] == 0 for key in EXCAP if key not in ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]):
            res.append([f'All values are equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', "Pass"])
        else: res.append([f'All values are not equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', "Fail"])
        if GMP["G_NPM_CO"] == 0:
            res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: = 0", 'Pass'])
        else: res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: = 0", 'Fail'])
        if GMP["G_HPM_CO"] == 0:
            res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", 'Pass'])
        else: res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", 'Fail'])
        if GMP["G_CPM_CO"] != 0:
            res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: != 0", 'Pass'])
        else: res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: != 0", 'Fail'])
    else: res.append([f"This is an unexpected {ECAP} power mode sequence in MODECAP packet", 'Fail'])  
    return res

def PrectWithMODECAP(self,Flow_limit,Check):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    res = []
    TypeSD = ""
    TyepDscr = ""
    # print(self.Header['TestcaseName'])
    if 'NPM' in self.Header['TestcaseName']:
        TypeSD = "NPM"
        TyepDscr = "Nominal_Power_Mode"
    elif 'LPM' in self.Header['TestcaseName']:
        TypeSD = "LPM"
        TyepDscr = "Low_Power_Mode"
    elif 'HPM' in self.Header['TestcaseName']:
        TypeSD = "HPM"
        TyepDscr = "High_Power_Mode"
    elif 'CPM' in self.Header['TestcaseName']:
        TypeSD = "CPM"
        TyepDscr = "Continuous_Power_Mode"


    #1. Find the MODEXCAP packet
    TempPkt1 = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
    if len(TempPkt1)>2:
        # print(TypeSD,TyepDscr,TempPkt1)
        TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref0")[0]['sDescription']
        if ':' in TempVal:TempVal = TempVal.split(':')[1]
        ref0 = GeneralMethods.GetFloatFromStr(TempVal)[0]
        
        TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref1")[0]['sDescription']
        if ':' in TempVal:TempVal = TempVal.split(':')[1]
        ref1 = GeneralMethods.GetFloatFromStr(TempVal)[0]
        
        TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],TyepDscr)[0]['sDescription']
        if ':' in TempVal:TempVal = TempVal.split(':')[1]
        MaxW = GeneralMethods.GetFloatFromStr(TempVal)[0]

        # Check for the DPLOSS calibration
        if TypeSD != "LPM":
            ECAP = self.PktMethod.GetPacketDetails(packet="Extended_Power_Transmitter_Extended_Capabilities",limit=Flow_limit,Type="Response")
            if len(ECAP)>2:
                Nego = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'])[0]
                # print("Nego:",Nego)
                if Nego >= 15:
                    res.append([f"Negotiable_Load_Power is {Nego} W in Extended_Power_Transmitter_Extended_Capabilities, so DPLOSS calibration will perform, Expected: >= 15 W", "Pass"])
                    tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,"Inconclusive": False,"CheckSEQ": 1}
                    if TypeSD == "NPM":
                        tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","skiplevel": ["Level4"],"flow": 2,"Result_check": True,"Inconclusive": False,"CheckSEQ": 1}
                    dploss_res=self.DPlossCalibrationCheck(tempcheck)
                    for tempres in dploss_res: res.append(tempres)
                else: res.append([f"Negotiable_Load_Power is {Nego} W in Extended_Power_Transmitter_Extended_Capabilities, so DPLOSS calibration won't perform, Expected: >= 15 W", "Pass"])
            else: res.append([f"Extended_Power_Transmitter_Extended_Capabilities response is not observed", "Fail"])





        res.append([f"Found MODEXCAP at {round(TempPkt1[0],3)}sec, with {TypeSD} : Voltage Ref0: {ref0} V, Voltage Ref1: {ref1} V and Potential Load Power: {MaxW} W","Pass"])

        #check for the PRECT1 & 2 with set load value of MAXW 
        #Prect 1###########################################################################
        Load1Pkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(MaxW*1000)}",limit=[TempPkt1[2],Flow_limit[1]],Type="TesterMsg")
        if len(Load1Pkt)>2:
            #Find Stabilization 
            Stable1Pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Load1Pkt[2],Flow_limit[1]],Type="TesterMsg")
            if len(Stable1Pkt)>2:
                res.append([f"Prect1:Stabilization found at {round(Stable1Pkt[0],3)}sec","Pass"])
                #Get the Prect from next PLA_2 packet and Vrect measure on before CE packet
                PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[Stable1Pkt[2],Flow_limit[1]])
                if len(PLAPkt)>2:
                    Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"PRECT")[0]['sDescription'])[0]
                    # ChkRes = CommonMethods.check_measure([MaxW-0.1,MaxW+0.1],Prect)
                    ChkRes = CommonMethods.check_measure([MaxW-0.1],Prect,comp='GTEQL')
                    # print("ChkRes:",ChkRes)
                    res.append([f"Prect1: {Prect}W found in PLA_2 packet at {round(PLAPkt[0],3)}sec, limit:{ChkRes[2]} W (MODEXCAP[Potential Load Power]- 0.1 W)",ChkRes[1]])
                else:res.append([f"Prect1: PLA_2 packet not found after the stabilization","Fail"])
                #Ensure the Vrect
                CE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[Stable1Pkt[2],Load1Pkt[2]])
                if len(CE)>2:
                    reslt = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                    ChkRes = CommonMethods.check_measure([ref0-((ref0/100)*5),ref0+((ref0/100)*5)],reslt[0])
                    res.append([f"Prect1: The Measured Vrect on the CE packet at {round(CE[0],3)}sec is {reslt[0]}V, limit: {ChkRes[2]}V (MODEXCAP[Main Active Mode (Voltage Vref0)])",ChkRes[1]])
                else:res.append("Prect1: CE packet not found before the Stabilization","Fail")
            else:res.append([f"Prect1:Stablization not found between {round(Load1Pkt[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Fail"])
        else:res.append([f"Prect1: The Set_Load {int(MaxW*1000)} packet not found between {round(TempPkt1[0],3)}sec to {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Fail"])
        #prect2###################################################################################
        Load2Pkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(MaxW*1000)}",limit=[Flow_limit[1],TempPkt1[2]],Type="TesterMsg")
        if len(Load2Pkt)>2:
            #Find Stabilization 
            Stable2Pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Load2Pkt[2],Flow_limit[1]],Type="TesterMsg")
            if len(Stable2Pkt)>2:
                res.append([f"Prect2:Stabilization found at {round(Stable2Pkt[0],3)}sec","Pass"])
                #Get the Prect from next PLA_2 packet and Vrect measure on before CE packet
                PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[Stable2Pkt[2],Flow_limit[1]])
                if len(PLAPkt)>2:
                    Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"PRECT")[0]['sDescription'])[0]
                    # ChkRes = CommonMethods.check_measure([MaxW-0.1,MaxW+0.1],Prect)
                    ChkRes = CommonMethods.check_measure([MaxW-0.1],Prect,comp='GTEQL')
                    res.append([f"Prect2: {Prect} W found in PLA_2 packet at {round(PLAPkt[0],3)}sec, limit:{ChkRes[2]} W (MODEXCAP[Potential Load Power]- 0.1 W)",ChkRes[1]])
                else:res.append([f"Prect2: PLA_2 packet not found after the stabilization","Fail"])
                #Ensure the Vrect
                CE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[Stable2Pkt[2],Load2Pkt[2]])
                if len(CE)>2:
                    reslt = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                    ChkRes = CommonMethods.check_measure([ref1-((ref1/100)*5),ref1+((ref1/100)*5)],reslt[0])
                    res.append([f"Prect2: The Measured Vrect on the CE packet at {round(CE[0],3)}sec is {reslt[0]}V, limit: {ChkRes[2]}V (MODEXCAP[Main Active Mode (Voltage Vref1)])",ChkRes[1]])
                else:res.append("Prect2: CE packet not found before the Stabilization","Fail")
            else:res.append([f"Prect2:Stablization not found between {round(Load1Pkt[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Fail"])
        else:res.append([f"Prect2: The Set_Load {int(MaxW*1000)} packet not found between {round(TempPkt1[0],3)}sec to {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Fail"])

    else:res.append([f"The MODEXCAP packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
    return res
def PrectCompare(self,Flow_limit,Check):
    try:
        Prectlist = []
        res =[]
        cnt = 1
        for ld in Check['Loads']:
            #1.Get Loads
            LoadPkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(ld)}",limit=Flow_limit,Type="TesterMsg")
            if len(LoadPkt)>2:
                res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec","Pass"])
                #Get Stabilization
                StablePkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[LoadPkt[2],Flow_limit[1]],Type="TesterMsg")
                if len(StablePkt)>2:
                    res.append([f"Stablization found for load {ld} mA at {round(StablePkt[0],3)} sec","Pass"])
                    #Get the PLA_2
                    PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[StablePkt[2],Flow_limit[1]])
                    if len(PLAPkt)>2:
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"PRECT")[0]['sDescription'])[0]
                        Prectlist.append(Prect)
                        res.append([f"Prect{cnt}:PLA_2 packet found at {round(PLAPkt[0],3)}sec, with PRECT value {Prect}W","Pass"])
                    else:res.append([f"Prect{cnt}:PLA_2 packet not found after the stabilization","Fail"])
                else:res.append([f"Stablization not found for load {ld}","Fail"])
            else:res.append([f"Set Load for {ld}mA not received","Fail"])
            cnt+=1
        if len(Prectlist)==2:
            if Prectlist[0]<Prectlist[1]:
                res.append([f"Prect1 : {Prectlist[0]} W, Prect2:{Prectlist[1]} W, Expected Prect1<Prect2","Pass"])
            else:res.append([f"Prect1 : {Prectlist[0]} W, Prect2:{Prectlist[1]} W, Expected Prect1<Prect2","Fail"])
        else:res.append([f"Not found 2 prect values for the comparison","Fail"])
        return res
    except Exception as e:
        print(e)
def FODTempCheck(self,Flow_limit,Check):


    self.test_halt = False
    res = []
    Flow_limit = Flow_limit
    self.AllChannelData12= self.PlotMethod.GetAllChannelData('12',self.JapiData)

    TS = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[0,len(self.file_list)],Type="TesterMsg")
    # CHECK 1: Test has run for 30 minutes
    if not self.test_halt:
        # print("TS:",TS)
        if len(TS)>2:
            # # print(self.PktMethod.Timeconvert(TS[0]))
            if TS[0] > 1800:
                res.append([f"Test has run for 30 minutes: Test_Stop is observed at {self.PktMethod.Timeconvert(TS[0])}", "Pass"])
        else: res.append([f"Test_Stop not observed", "Fail"])

    # CHECK 2: TFO exceeds the FO’s safe temperature limit.
    id = 0
    CP = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station",limit=[0,Flow_limit[1]],Type="TesterMsg")
    if len(CP)>2:
        t1 = CP[0]
    else: t1 = self.file_list[id]['startTime'] #sec
    t1 = self.file_list[id]['startTime'] #sec
    sindex = int((t1*1000)/self.AllChannelData12['Interval'])
    tempdata = self.AllChannelData12['RV']['displayDataChunk'][sindex:]
    
    Maxtemp = max(tempdata)
    T2 = ((self.AllChannelData12['RV']['displayDataChunk'].index(Maxtemp))*self.AllChannelData12['Interval'])/1000
    # print("Maxtemp:", max(tempdata), "time:",T2)
    if not self.test_halt:
        if Maxtemp > Check['FOtempLimit'][1]:
            res.append([f"TFO exceeds the FO’s safe temperature limit: TFO: {Maxtemp} °C at {T2} sec, Maximum temperature limit of {Check['FOtempLimit'][0]}: {Check['FOtempLimit'][1]} °C", "Pass"])
            self.test_halt = True

    # CHECK 3: TFO stabilizes to ±1 °C within 5 minutes
    if not self.test_halt:
        id = 0
        t1 = self.file_list[id]['startTime'] #sec
        t2 = 300 #5min
        end = self.file_list[Flow_limit[1]]['startTime']
        
        while t2 <= end:
            sindex = int((t1*1000)/self.AllChannelData12['Interval'])
            eindex = int((t2*1000)/self.AllChannelData12['Interval'])
            temp1 = round(self.AllChannelData12['RV']['displayDataChunk'][sindex],3)
            temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex],3)
            if abs(temp2 - temp1) <= 1:
                # print("t1:",self.PktMethod.Timeconvert(t1),"temp1:",temp1,"t2:",self.PktMethod.Timeconvert(t2),"temp2:",temp2)
                res.append([f"TFO Stabilises to ±1 °C between {self.PktMethod.Timeconvert(t1)} with TFO: {temp1} °C and {self.PktMethod.Timeconvert(t2)} with TFO: {temp2} °C in 5 minutes period.", "Pass"])
                self.test_halt = True
                break

            t1 += 1
            t2 += 1

    # CHECK 4: TFO < 0.8*maximum temperature after 10 minutes
    if not self.test_halt:
        if len(TS)>2 and TS[0] > 600:
            id = 0
            t1 = self.file_list[id]['startTime'] #sec
            t2 = 600 #sec -->10min
            FOtemp = Check['FOtempLimit'][1]
            eindex = int((t2*1000)/self.AllChannelData12['Interval'])
            temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex],3)
            if temp2 < (0.8*FOtemp):
                # print("TFO < 0.8*maximum temperature after 10 minutes:", temp2, "Expected:>=",0.8*FOtemp)
                res.append([f"TFO < 0.8*maximum temperature after 10 minutes: TFO: {temp2} °C, Maximum temperature limit of {Check['FOtempLimit'][0]}: {FOtemp} °C", "Pass"])
                self.test_halt = True

    # Power removal
    if not self.test_halt:
        if len(TS)>2:
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[0],TS[2]+1],Type="TesterMsg")
            if len(sd)>2:
                res.append([f"Test case terminated due to power signal removal at {self.PktMethod.Timeconvert(sd[0])}", "Pass"])
        else: res.append([f"Test_Stop not observed", "Fail"])

    res.append([f"Measured maximum temperature of FO is: {Maxtemp} °C", "Pass"])

    return res



def VrectPeak(self,Flow_limit,Check):
    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
    
    res =[]
    Maxlimit = Check['Count']
    # id = 1
    # Cloak after 3 CXE
    Templimt = Flow_limit
    clk1 = self.PktMethod.GetPacketDetails(packet="Cloak",limit=Templimt,Type="Packet")
    if len(clk1)>2:
        xce_cnt = 0
        x = Templimt[0]
        while x < clk1[2]:
            XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[x,clk1[2]],Type="Packet")
            if len(XCE)>2:
                x = XCE[2]
                xce_cnt += 1
            x += 1
        if xce_cnt >= 3:
            res.append([f"TPR requested Cloak after {xce_cnt} Extended Control Error packets, Expected: Atleast after 3 Extended Control Error packets","Pass"])
        else: res.append([f"TPR requested Cloak after {xce_cnt} Extended Control Error packets, Expected: Alteast after 3 Extended Control Error packets","Fail"])

        # Load to 0mA
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        sindex = int((clk1[0]*1000)/AllChannelData3['Interval'])-5
        eindex = int((self.file_list[len(self.file_list)-1]['startTime']*1000)/AllChannelData3['Interval'])
        id1 = sindex
        Irect = 0
        threshold = 0.020
        interval = AllChannelData3['Interval']
        required_samples = int(0.030 / interval)
        count = 0
        t_prev = 0
        t_curr = 0
        t_total = 0
        for id1 in range(id1, eindex + 1):
            Irect = round(AllChannelData3['RV']['displayDataChunk'][id1], 3)
            # # print("Irect:",Irect)
            if Irect < threshold:
                count += 1
                if count == 1: 
                    res.append([f"TPR set load to 0 mA from {round((id1*AllChannelData3['Interval'])/1000,3)} sec", "Pass"])
                else:
                    t_prev = (id1-1)*AllChannelData3['Interval']
                    t_curr = id1*AllChannelData3['Interval']
                    t_total += (t_curr-t_prev)
                    # # print(t_prev,t_curr,t_total)
                if t_total > 30:
                    res.append([f"TPR stayed below 20 mA and 50 mA ballast load is not applied for at least 30 ms", 'Pass'])
                    # print("Stayed below 0.020 for 30 ms. Breaking loop.")
                    break      
            else:
                count = 0
                t_total = 0
        else:
            res.append([f"TPR not stayed below 20 mA for at least 30 ms", 'Fail'])
            # print("Signal did NOT stay below 0.020 for 30 ms.")

        # Crx 174 nF
        crx = self.PktMethod.GetPacketDetails(packet="CRx_Status",value="_174nF",limit=[clk1[2],len(self.file_list)-1],Type="TesterMsg")
        if len(crx)>2:
            res.append([f"Crx=174 nF is found at {round(crx[0])} sec", 'Pass'])
        else: res.append([f"Crx=174 nF is not found after 1st cloak", 'Fail'])

        # Vrect max before 10 cloak pings
        id = clk1[2]
        clk_cnt = 0
        end = len(self.file_list)-1
        vrect_max = [0]
        vrect_min = [0]
        while id < end:
            PD = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[id,end],Type="TesterMsg")
            if len(PD)>2:
                # print("pd:",PD)
                clk = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[PD[2],end],Type="Packet")
                if len(clk)>2:
                    peakvol =  self.PlotMethod.CalculateHighVoltageTimePeriod(self.AllChannelData,PD[0]*1000,clk[0]*1000)
                    if peakvol is None:
                        res.append([f"Peak voltage calculation not performed","Fail"])
                    else:
                        ChkRes = CommonMethods.check_measure(Check['expected'],peakvol,Check['comp'])
                        res.append([f"The Calculated Vrect peak is {peakvol}V, measured before Cloak packet between {round(PD[0],3)}Sec- {round(clk[0],3)}Sec, limit {ChkRes[2]}V",ChkRes[1]])
                    clk_cnt += 1
                    if clk_cnt == 1:
                        vrect_min = vrect_max = [peakvol,round(PD[0],3),round(clk[0],3)]
                    else:
                        if peakvol < vrect_min[0]: vrect_min = [peakvol,round(PD[0],3),round(clk[0],3)]
                        if peakvol > vrect_max[0]: vrect_max = [peakvol,round(PD[0],3),round(clk[0],3)]
                    id = clk[2]
            id+=1
        
        if clk_cnt == 10:
            res.append([f"10 cloak pings observed, Expected: 10","Pass"])
        else: res.append([f"{clk_cnt} cloak pings observed, Expected: 10","Fail"])
        res.append([f"Vrect_min is {vrect_min[0]}V, measured before Cloak packet between {vrect_min[1]}Sec- {vrect_min[2]}Sec", "Pass"])
        res.append([f"Vrect_max is {vrect_max[0]}V, measured before Cloak packet between {vrect_max[1]}Sec- {vrect_max[2]}Sec", "Pass"])

    return res
        
def PrectAFLoads(self,Flow_limit,Check):
    try:
        res=[]
        # prect = []
        #1.Get the Loads
        for Prect in Check['expected']:
            #Get Prect value from the PLA packet
            LoadPkt =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {Prect['Load']}",limit=Flow_limit,Type="TesterMsg")
            if len(LoadPkt)>2:
                res.append([f"Set Load {Prect['Load']} packet found at {round(LoadPkt[0],3)}sec","Pass"])
                if Check['MeasureType'] == "Packet":
                    #calculate Prec value
                    if Prect['Condition']['Type']=="PowerLimit":
                        #Get the power value from PLA packet once after reaching the powerlimit
                        id = LoadPkt[2]
                        while id < Flow_limit[1]:
                            PLApkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                            if len(PLApkt)>2:
                                PLAprect =GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLApkt[2],"PRECT")[0]['sDescription'])[0]
                                # prect.append(PLAprect)
                                if Prect['Condition']['comp'] =="GTEQL":
                                    if PLAprect >= Prect['Condition']['value']:
                                        res.append([f"Found Prect {PLAprect}W at {round(PLApkt[0],3)}sec, which is above the Limit {Prect['Condition']['value']}W","Pass"])
                                        break
                                id = PLApkt[2]+1
                            else:
                                res.append([f"PLA_2 packet with Prect value above the limit {Prect['Condition']['value']} not found.","Fail"])
                                break  
                elif Check['MeasureType']=="Plot":
                    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
                    self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
                    #Default get the measure af the stabilization
                    if Prect['Condition']['Type']=="Stabilization":
                        staPkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[LoadPkt[2],Flow_limit[1]],Type="TesterMsg")
                        if len(staPkt)>2:
                            #Get the CE packet
                            CEpkt = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[staPkt[2],Flow_limit[0]])
                            if len(CEpkt)>2:
                                res.append([f"Stablization found at {round(CEpkt[0],3)}sec","Pass"])

                                #Get the index of the allchannel data 
                                ChIndex = int((CEpkt[0]*1000)-6/self.AllChannelData['Interval'])
                                # print("ChIndex1:",int((CEpkt[0]*1000)-8/self.AllChannelData['Interval']))
                                # print("ChIndex2:",int((CEpkt[0]*1000)-6/self.AllChannelData['Interval']))
                                
                                I = round(abs(self.AllChannelData3['RV']['displayDataChunk'][ChIndex]*1000),4)
                                V = round(abs(self.AllChannelData['RV']['displayDataChunk'][ChIndex]*1000),4)
                                p = round((I/1000)*(V/1000),3)
                                PowerChkRes = CommonMethods.check_measure(Prect['exp'],p,Prect['comp'])
                                res.append([f"Measured Prect is {p}W measured at {round(CEpkt[0]-0.006,3)}sec, limit {PowerChkRes[2]}W",PowerChkRes[1]])
                                res.append([f"Measured Irect is {round(I/1000,3)}A measured at {round(CEpkt[0]-0.006,3)}sec","Pass"])
                                if 'Vrect' in Prect:
                                    VrectChkRes = CommonMethods.check_measure(Prect['Vrect']['exp'],round(V/1000,3),Prect['Vrect']['comp'])
                                    res.append([f"Measured Vrect is {round(V/1000,3)}V measured at {round(CEpkt[0]-0.006,3)}sec, limit {VrectChkRes[2]}W",VrectChkRes[1]])
                                # respkt = self.PktMethod.CalculateVoltTwindow(CEpkt[2],self.AllChannelData)
                            else:res.append([f"Stabilization not found for the load {Prect['Load']}mW","Fail"])
                        else:res.append([f"Stabilization not found for the load {Prect['Load']}mW","Fail"])
            else:res.append[f"Set Load {Prect['Load']} packet not found","Fail"]
        return res
    except Exception as e:
        print(e)
def t_modecomplete(self,Flow_limit,Check):
    try:
        res=[]
        pwrvalue = Check["PowerMode"]
        #1.find the packet MSR packet with powermode change
        Pkt1 = self.PktMethod.GetPacketDetails(packet="MSR",value=pwrvalue,limit=Flow_limit)
        if len(Pkt1)>2:
            res.append([f"Power Mode update packet MSR with value {pwrvalue} found at {round(Pkt1[0],3)}sec","Pass"])
            #get the reponse of the packet
            responseID = self.PktMethod.GetPacketResponse(Pkt1[2],[Pkt1[2]+1,Flow_limit[1]])
            if responseID is not None:
                Pkt2 = self.PktMethod.GetPacketDetails(packet="EPTR",limit=[Pkt1[2],Flow_limit[1]],Type="Response")
                if len(Pkt2)>2:
                    res.append([f"EPTR request received at {round(Pkt2[0],3)} sec","Pass"])
                    ChkRes = CommonMethods.check_measure(Check['expected'],round((Pkt2[0]-self.file_list[responseID]['stopTime'])*1000,3),Check['comp'])
                    res.append([f"The measured t_modecomplete is {ChkRes[3]}ms, Limit {ChkRes[2]}ms",ChkRes[1]])
                else:res.append([f"Packet EPTR not found","Fail"])
            else:res.append([f"Response not found for the MSR packet","Fail"])
        else:res.append([f"Power Mode update packet MSRwith {pwrvalue} not found","Fail"])
        return res
    except Exception as e:
        print(e)
        
def t_ept_modechange(self,Flow_limit,Check):

    res=[]
    
    EPTR = self.PktMethod.GetPacketDetails(packet="EPTR",value="Power Mode Change",limit=Flow_limit,Type="Response")
    if len(EPTR)>2:
        res.append([f"EPTR_Power Mode Change request received at {round(EPTR[0],3)} sec","Pass"])
        
        EPT = self.PktMethod.GetPacketDetails(packet="End Power Transfer",value="EPT/pmc",limit=[EPTR[2],Flow_limit[1]],Type="Packet")
        if len(EPT)>2:
            res.append([f"End Power Transfer packet found at {round(EPT[0],3)} sec","Pass"])

            PD = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[EPT[2],len(self.file_list)-1],Type="TesterMsg")
            if len(PD)>2:
                ChkRes = CommonMethods.check_measure(Check['expected'],round((PD[0]-EPT[1])*1000,3),Check['comp'])

                res.append([f"The measured t_ept_modechange is {ChkRes[3]}ms, Limit {ChkRes[2]}ms",ChkRes[1]])
            else:res.append([f"PD not found after the 360Khz flow","Fail"])


        else: res.append([f"End Power Transfer packet not found","Fail"])
    else: res.append([f"PTxDUT not sent EPTR","Pass"])
    
    return res

import sys
sys.path.append('Scripts')
import sqlite3
from pymongo import MongoClient
from MainModule import JsonOperations,UpdateStatusLogs
import traceback
import pandas as pd
import uuid
import orjson

class SQLiteConnection():
    def __init__(self):
        self.Conn =  sqlite3.connect('Resources/GRLDB.db', check_same_thread=False)
        # self.cursor = self.Conn.cursor()
        self.JTCP = JsonOperations('json/Test_config_properties.json')
        self.JTCPData = self.JTCP.read_file()
        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        #MongoDB Connection
        self.mongo_client = MongoClient(f"mongodb://{self.JsettingsData['MongoDB']['ServerIP']}:{self.JsettingsData['MongoDB']['Port']}")
        self.mongo_db = self.mongo_client[self.JsettingsData['MongoDB']['DB']]
        self.tables = ["Header","ChecksHeader","ChecksDetails"]
        self.StatusLogs = UpdateStatusLogs
        # self.tables = ["Header"]
    #To insert dict values to already created Table in SQLite, both Table and the DICT schema has to be same
    def InsertDataFromDict(self,Table,values):
        try:
            self.cursor = self.Conn.cursor()
            for row in values:
                columns = ', '.join(row.keys())
                placeholders = ', '.join(['?' for _ in row])
                values = tuple(row.values())
                self.cursor.execute(f"INSERT INTO {Table} ({columns}) VALUES ({placeholders})", values)
            self.Conn.commit()
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")

    # convert dict/list to JSON string if needed
    # def safe_sql_value(self,val):
    #     if isinstance(val, (dict, list)):
    #         return json.dumps(val)
    #     return val
    def safe_sql_value(self, val):
        if isinstance(val, (dict, list)):
            return orjson.dumps(val).decode()  # convert bytes → string
        return val

    def SyncWithJsonReportFile(self):
        try:

            self.cursor = self.Conn.cursor()
            self.JTCPData = self.JTCP.read_file()
            print("off sync")
            RepPath=[self.JTCPData['test_config_data']['Report_path']]
            for Path in RepPath:
                TCObj = JsonOperations(Path)
                TCdata = TCObj.read_file()
                # TCdata = json.dumps(TCdata)
                # print("off paths")
                # print("TCdata:",TCdata)
                for Test in TCdata:
                    print("Header:",Test['Header']['TestcaseID'])
                    #########################################################Sync Headers
                    columns = ', '.join(Test['Header'].keys())
                    placeholders = ', '.join(['?' for _ in Test['Header']])
                    values = tuple(Test['Header'].values())
                    # ensure that the same project with testcase already available in the DB, if so repleace with new
                    #use SWversion, FWversion, ProjectName, testcase name
                    self.DeleteDuplicateTests(Test['Header'])
                    self.cursor.execute(f"INSERT INTO Header ({columns}) VALUES ({placeholders})", values)
                    # self.Conn.commit()
                    for SEQID in Test['SeqResults']:
                        ###########################################Timings
                        TimingsList = []
                        for timings in Test['SeqResults'][SEQID]['Timings']:
                            if all(res not in timings for res in ['_remark','_allres',"_exp","_res","_temp_","_remarks","_SEQ","_Details"]):
                                if Test['SeqResults'][SEQID]['Timings'][timings] not in ["NA",""]:
                                    TimingsList.append(timings)
                        # print(TimingsList)
                        if len(TimingsList)>0:
                            for Tim in TimingsList:
                                #Header
                                rmrk = Test['SeqResults'][SEQID]['Timings'][f"{Tim}_remark"] if f"{Tim}_remark" in Test['SeqResults'][SEQID]['Timings'] else "NA"
                                self.cursor.execute("INSERT INTO ChecksHeader (UID, SEQID, Type, Description, ExpValue,MinValue, MaxValue, Value, Result, Remarks,CheckSEQ) VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                                                    (Test['Header']['UID'],int(SEQID),"Timings",Tim,Test['SeqResults'][SEQID]['Timings'][f"{Tim}_exp"],
                                                    'NA','NA',Test['SeqResults'][SEQID]['Timings'][Tim],Test['SeqResults'][SEQID]['Timings'][f"{Tim}_res"],rmrk,Test['SeqResults'][SEQID]['Timings'][f"{Tim}_SEQ"]))
                                #Update sub checks from Details
                                subSeq = 1
                                if f"{Tim}_Details" in  Test['SeqResults'][SEQID]['Timings']:
                                    if len(Test['SeqResults'][SEQID]['Timings'][f"{Tim}_Details"])>0:
                                        for subchk in Test['SeqResults'][SEQID]['Timings'][f"{Tim}_Details"]:
                                            self.cursor.execute("INSERT INTO ChecksDetails (UID, SEQID, Type, Description, Result, Remarks, CheckSEQ) VALUES (?,?,?,?,?,?,?)", 
                                                    (Test['Header']['UID'],int(SEQID),"Timings",Tim,subchk[1],subchk[0],subSeq))
                                            subSeq+=1
                                # TimList = list(map(float,Test['SeqResults'][SEQID]['Timings'][Tim].split(';')))
                                # self.cursor.execute("INSERT INTO ChecksHeader (UID, SEQID, Type, Description, ExpValue, MinValue, MaxValue, Value, Result) VALUES (?,?,?,?,?,?,?,?,?)", 
                                #                     (Test['Header']['UID'],int(SEQID),"Timing",Tim,Test['SeqResults'][SEQID]['Timings'][f"{Tim}_exp"],
                                #                     min(TimList),max(TimList),'NA',Test['SeqResults'][SEQID]['Timings'][f"{Tim}_res"]))
                                # #Details - Sync later since having more records
                                
                                # CK_res = Test['SeqResults'][SEQID]['Timings'][f"{Tim}_allres"].split(';')
                                # CK_remarks = Test['SeqResults'][SEQID]['Timings'][f"{Tim}_remark"].split(';')
                                # id = 0
                                # while id < len(TimList):
                                #     self.cursor.execute("INSERT INTO ChecksDetails (UID, SEQID, Type, Description, Value, Result,Remarks) VALUES (?,?,?,?,?,?,?)", 
                                #                     (Test['Header']['UID'],int(SEQID),"Timing",Tim,TimList[id],CK_res[id],CK_remarks[id]))
                        #Measures##############################################################################################
                        MeasureList = []
                        if Test['SeqResults'][SEQID]['Measures'] is not None:
                            for Measures in Test['SeqResults'][SEQID]['Measures']:
                                if all(res not in Measures for res in ["_exp","_res","_temp_","_remarks","_SEQ","_Details"]) and Test['SeqResults'][SEQID]['Measures'][Measures] not in ["NA",""]:
                                    MeasureList.append(Measures)
                            if len(MeasureList)>0:
                                for Mes in MeasureList:
                                    #check for remarks 
                                    rmrk = Test['SeqResults'][SEQID]['Measures'][f"{Mes}_remarks"] if f"{Mes}_remarks" in Test['SeqResults'][SEQID]['Measures'] else "NA"
                                    self.cursor.execute("INSERT INTO ChecksHeader (UID, SEQID, Type, Description, ExpValue,MinValue, MaxValue, Value, Result, Remarks,CheckSEQ) VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                                                        (self.safe_sql_value(Test['Header']['UID']),int(SEQID),"Measures",Mes,self.safe_sql_value(Test['SeqResults'][SEQID]['Measures'].get(f"{Mes}_exp", "NA")),
                                                        'NA','NA',self.safe_sql_value(Test['SeqResults'][SEQID]['Measures'].get(Mes, "NA")),self.safe_sql_value(Test['SeqResults'][SEQID]['Measures'].get(f"{Mes}_res", "NA")),self.safe_sql_value(rmrk),self.safe_sql_value(Test['SeqResults'][SEQID]['Measures'].get(f"{Mes}_SEQ", "NA"))))
                                    #Update sub checks from Details
                                    subSeq = 1
                                    if f"{Mes}_Details" in  Test['SeqResults'][SEQID]['Measures']:
                                        if len(Test['SeqResults'][SEQID]['Measures'][f"{Mes}_Details"])>0:
                                            for subchk in Test['SeqResults'][SEQID]['Measures'][f"{Mes}_Details"]:
                                                self.cursor.execute("INSERT INTO ChecksDetails (UID, SEQID, Type, Description, Result, Remarks, CheckSEQ) VALUES (?,?,?,?,?,?,?)", 
                                                        (Test['Header']['UID'],int(SEQID),"Measures",Mes,subchk[1],subchk[0],subSeq))
                                                subSeq+=1
                        #Other checks
                        OtherList = []
                        for Others in Test['SeqResults'][SEQID]['Others']:
                            if all(res not in Others for res in ['_remark','_allres',"_exp","_res","_temp_","_remarks","_SEQ","_Details"]) and Test['SeqResults'][SEQID]['Others'][Others] not in ["NA",""]:
                                OtherList.append(Others)
                        # print(OtherList)
                        if len(OtherList)>0:
                            for Oth in OtherList:
                                 #Header
                                rmrk = Test['SeqResults'][SEQID]['Others'][f"{Oth}_remark"] if f"{Oth}_remark" in Test['SeqResults'][SEQID]['Others'] else "NA"
                                self.cursor.execute("INSERT INTO ChecksHeader (UID, SEQID, Type, Description, ExpValue,MinValue, MaxValue, Value, Result, Remarks,CheckSEQ) VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                                                    (Test['Header']['UID'],int(SEQID),"Others",Oth,Test['SeqResults'][SEQID]['Others'][f"{Oth}_exp"],
                                                    'NA','NA',Test['SeqResults'][SEQID]['Others'][Oth],Test['SeqResults'][SEQID]['Others'][f"{Oth}_res"],rmrk,Test['SeqResults'][SEQID]['Others'][f"{Oth}_SEQ"]))
                                #Update sub checks from Details
                                subSeq = 1
                                if f"{Oth}_Details" in  Test['SeqResults'][SEQID]['Others']:
                                    if len(Test['SeqResults'][SEQID]['Others'][f"{Oth}_Details"])>0:
                                        for subchk in Test['SeqResults'][SEQID]['Others'][f"{Oth}_Details"]:
                                            self.cursor.execute("INSERT INTO ChecksDetails (UID, SEQID, Type, Description, Result, Remarks, CheckSEQ) VALUES (?,?,?,?,?,?,?)", 
                                                    (Test['Header']['UID'],int(SEQID),"Others",Oth,subchk[1],subchk[0],subSeq))
                                            subSeq+=1
                        # break
                    self.Conn.commit()
                    # break
                    # self.Conn.close()
        except Exception as e:
            print(e)
    def DeleteTableData(self,Table):
        try:
            self.cursor = self.Conn.cursor()
            DeleteQry = f"Delete from {Table}"
            self.cursor.execute(DeleteQry)
            #self.cursor.execute("VACUUM")
        except Exception as e:
            print(e)
    def FetchDataFromQRY(self,QRY):
        try:
            QRY_DF = pd.read_sql_query(QRY, self.Conn)
            if QRY_DF.shape[0] > 0:
                # print(list(QRY_DF['Name']))
                return QRY_DF
            return None
        except Exception as e:
            print(e)
            return None
    def ExecutebyQuery(self, QRY, params=None):
        """
        Execute a SQL query with optional parameters.

        :param QRY:   SQL query string (may contain ? placeholders)
        :param params: tuple or list of parameters for placeholders
        """
        try:
            self.cursor = self.Conn.cursor()
            if params:
                self.cursor.execute(QRY, params)
            else:
                self.cursor.execute(QRY)
            self.Conn.commit()
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")
        except Exception as e:
            print(e)

    def DeleteDuplicateTests(self,HeaderData):
        try:
            Header_Qry = f"SELECT *FROM Header WHERE ProjectName = '{HeaderData['ProjectName']}' and SWVersion='{HeaderData['SWVersion']}' and FWVersion='{HeaderData['FWVersion']}' and TestcaseName='{HeaderData['TestcaseName']}'"
            # print(Header_Qry)
            Header_df = pd.read_sql_query(Header_Qry, self.Conn)
            if Header_df.shape[0] > 0:
                print("Deleteing the UID:",Header_df["UID"].iloc[0])
                deleteHeader = f"DELETE FROM Header WHERE UID = '{Header_df["UID"].iloc[0]}'"
                deleteCheckHeader = f"DELETE FROM ChecksHeader WHERE UID = '{Header_df["UID"].iloc[0]}'"
                deleteCheckDetails = f"DELETE FROM ChecksDetails WHERE UID = '{Header_df["UID"].iloc[0]}'"
                self.cursor.execute(deleteHeader)
                self.cursor.execute(deleteCheckHeader)
                self.cursor.execute(deleteCheckDetails)
                self.Conn.commit()
        except Exception as e:
            traceback.print_exc()
    #Sync#############################################################
    def get_table_columns(self,table_name):
        """Fetch column names of a table"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return [col[1] for col in self.cursor.fetchall()]
    def GetSingleValuesFromDB(self,Header_Qry):
        # print(Header_Qry)
        # Header_Qry = '''
        #             SELECT DISTINCT(SWVersion) FROM Header 
        #             WHERE BoardModel = "GRL-WP-TPR-C3" and Certification="1.3.3"
        #                 '''
        Header_df = pd.read_sql_query(Header_Qry, self.Conn)
 
        return(Header_df.iloc[:,0].tolist())
    def sync_table(self):
        try:
            """Sync a specific SQLite table to MongoDB"""
            columns = self.get_table_columns('Header')
            self.cursor.execute(f"SELECT * FROM Header")
            rows = self.cursor.fetchall()
            collection = self.mongo_db['Header']
            for row in rows:
                # print(row)
                doc = {columns[i]: row[i] for i in range(len(columns))}
                #ensure the doc
                res = self.fetch_data('Header',{"UID":doc['UID']})
                # print(len(list(res)))
                if len(list(res))==0:
                    # print(doc['UID'])
                    doc["_id"] = str(uuid.uuid4())
                    collection.insert_one(doc)
                    #Insert related columns from checksheader
                    CH_columns = self.get_table_columns('ChecksHeader')
                    self.cursor.execute(f"SELECT * FROM ChecksHeader WHERE UID='{doc['UID']}'")
                    CH_rows = self.cursor.fetchall()
                    CH_collection = self.mongo_db['ChecksHeader']
                    for row in CH_rows:
                        doc = {CH_columns[i]: row[i] for i in range(len(CH_columns))}
                        doc["_id"] = str(uuid.uuid4())
                        CH_collection.insert_one(doc)
                    #inser for related columns in ChecksDetails
                    CD_columns = self.get_table_columns('ChecksDetails')
                    self.cursor.execute(f"SELECT * FROM ChecksDetails WHERE UID='{doc['UID']}'")
                    CD_rows = self.cursor.fetchall()
                    CD_collection = self.mongo_db['ChecksDetails']
                    for row in CD_rows:
                        doc = {CD_columns[i]: row[i] for i in range(len(CD_columns))}
                        doc["_id"] = str(uuid.uuid4())
                        CD_collection.insert_one(doc)
            print("Sync Done")
            # self.Conn.close()
            self.mongo_client.close()
        except Exception as e:
            traceback.print_exc()
    def fetch_data(self,table,sets):
        """Fetch and display all documents from a MongoDB collection."""
        collection = self.mongo_db[table]
        documents = collection.find(sets)
        return documents

        # for doc in documents:
        #     print(doc)
    #MongoDB Operations
    def DeleteRecords(self):
        #fetch headers
        Qry = {"SWVersion":"2.220.0.20"}
        Header_CL = self.mongo_db['Header']
        Header_Docs = Header_CL.find(Qry)
        for doc in Header_Docs:
            print(doc['UID'])
            CheckHeader_CL = self.mongo_db['ChecksHeader']
            CheckDetails_CL = self.mongo_db['ChecksDetails']
            CheckHeader_CL.delete_many({'UID':doc['UID']})
            CheckDetails_CL.delete_many({'UID':doc['UID']})
        Header_CL.delete_many(Qry)
        self.mongo_client.close()
# obj = SQLiteConnection()
# obj.FetchDataFromQRY(f"select DISTINCT(Position) FROM AllTestcases")
# obj.DeleteRecords()
# obj.fetch_data("Header",{"UID":"12fc4ce7-e2c7-11ef-af43-98db54c9a5"})
# obj.sync_table()

# obj.SyncWithJsonReportFile()
# # obj.GetValuesFromDB()


#Sync SQLite DB with MongoDB on remote
# class SyncToMongoDB():
#     def __init__(self):
#         pass
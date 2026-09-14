import orjson
import datetime
from typing import Optional


class JsonConfig:
    """
    Static container for all global JSON configs.
    Uses static methods to read and write without creating JsonOperations objects.
    """

    # File paths
    SETTINGS_PATH = "json/setting.json"
    TESTER_PATH = "json/Tester.json"
    XPATH_PATH = "json/Xpath.json"
    QI_PATH = "json/QIconfig.json"
    MOI_PATH = "json/MOIJson.json"
    PAYLOAD_PATH = "json/PayLoadChecks.json"
    TIMING_PATH = "json/TimingSetup.json"
    GENCHECK_PATH = "json/GeneralChecks.json"
    TESTCONF_PATH = "json/TestConfig.json"
    PHAPKT_PATH = "json/PhasePackets.json"
    TCP_PATH = "json/Test_config_properties.json"
    LOGS_PATH = "json/DebugLogs.json"
    ALLMOI_PATH = "json/AllMOIRun.json"
    TESTER_CONFIG_PATH = "json/TesterConfig.json"
    ESDF_PATH = "json/ESDF.json"
    TESTS_COMP_PATH = "json/TestsComp.json"
    TEST_RESULTS_PATH = "json/TestResults.json"
    CTS_PATH = ""

    # Cached in-memory data dictionaries
    JsettingsData: dict = {}
    JtesterData: dict = {}
    JapiData: dict = {}
    JQIData: dict = {}
    JMOIData: dict = {}
    JPayLoadCheckData: dict = {}
    JTimeData: dict = {}
    JGenCheckData: dict = {}
    JTestConfData: dict = {}
    JPhaPktData: dict = {}
    JTCPData: dict = {}
    JLogsData: dict = {}
    JAllMOIData: dict = {}
    TesterConfigData: dict = {}
    JEsdfData: dict = {}
    EsdfTestData: dict = {}
    TestData: dict = {}
    JCTSData: dict = {}

    # ------------------- Static Helper Methods -------------------
    @staticmethod
    def defaultconverter(o):
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        raise TypeError(f"Type not serializable: {type(o)}")

    @staticmethod
    def read_file(path: str) -> dict:
        """Static method to read and parse a JSON file directly by path."""
        try:
            with open(path, "rb") as rf:
                return orjson.loads(rf.read())
        except Exception as e:
            print(f"Read File Error ({path}): {e}")
            return {}

    @staticmethod
    def write_file(path: str, values: dict):
        """Static method to serialize and write data to a JSON file directly by path."""
        try:
            with open(path, "wb") as outfile:
                outfile.write(
                    orjson.dumps(
                        values,
                        default=JsonConfig.defaultconverter,
                        option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
                    )
                )
        except Exception as e:
            print(f"Write File Error ({path}): {e}")

    # ------------------- Lifecycle Batch Methods -------------------
    @classmethod
    def load_all(cls):
        """Loads all static JSON files once into memory at app startup."""
        cls.JsettingsData = cls.read_file(cls.SETTINGS_PATH)
        cls.JtesterData = cls.read_file(cls.TESTER_PATH)
        cls.JapiData = cls.read_file(cls.XPATH_PATH).get("API", {})
        cls.JQIData = cls.read_file(cls.QI_PATH)
        cls.JMOIData = cls.read_file(cls.MOI_PATH)
        cls.JPayLoadCheckData = cls.read_file(cls.PAYLOAD_PATH)
        cls.JTimeData = cls.read_file(cls.TIMING_PATH)
        cls.JGenCheckData = cls.read_file(cls.GENCHECK_PATH)
        cls.JTestConfData = cls.read_file(cls.TESTCONF_PATH)
        cls.JPhaPktData = cls.read_file(cls.PHAPKT_PATH)
        cls.JTCPData = cls.read_file(cls.TCP_PATH)
        cls.JLogsData = cls.read_file(cls.LOGS_PATH)
        cls.JAllMOIData = cls.read_file(cls.ALLMOI_PATH)
        cls.TesterConfigData = cls.read_file(cls.TESTER_CONFIG_PATH)
        cls.JEsdfData = cls.read_file(cls.ESDF_PATH)
        cls.EsdfTestData = cls.read_file(cls.TESTS_COMP_PATH)
        cls.TestData = cls.read_file(cls.TEST_RESULTS_PATH)

  
    @classmethod
    def save_all(cls):
        """Writes all in-memory JSON data back to their files on disk at once."""
        cls.write_file(cls.SETTINGS_PATH, cls.JsettingsData)
        cls.write_file(cls.TESTER_PATH, cls.JtesterData)
        cls.write_file(cls.QI_PATH, cls.JQIData)
        cls.write_file(cls.MOI_PATH, cls.JMOIData)
        cls.write_file(cls.PAYLOAD_PATH, cls.JPayLoadCheckData)
        cls.write_file(cls.TIMING_PATH, cls.JTimeData)
        cls.write_file(cls.GENCHECK_PATH, cls.JGenCheckData)
        cls.write_file(cls.TESTCONF_PATH, cls.JTestConfData)
        cls.write_file(cls.PHAPKT_PATH, cls.JPhaPktData)
        cls.write_file(cls.TCP_PATH, cls.JTCPData)
        cls.write_file(cls.LOGS_PATH, cls.JLogsData)
        cls.write_file(cls.ALLMOI_PATH, cls.JAllMOIData)
        cls.write_file(cls.TESTER_CONFIG_PATH, cls.TesterConfigData)
        cls.write_file(cls.ESDF_PATH, cls.JEsdfData)
        cls.write_file(cls.TESTS_COMP_PATH, cls.EsdfTestData)
        cls.write_file(cls.TEST_RESULTS_PATH, cls.TestData)
        print("All JSON files updated successfully on disk.")

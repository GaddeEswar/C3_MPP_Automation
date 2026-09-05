"""
Enums module for C3 and MPP Automation.
Defines standard enumerations used across testing, validation, reporting, and hardware interfaces.
"""

from enum import Enum, unique


class StrEnum(str, Enum):
    """Base string enumeration allowing direct string comparisons and serialization."""

    def __str__(self) -> str:
        return str(self.value)


@unique
class Product(StrEnum):
    """Supported product types."""
    MPP = "MPP"
    C3 = "C3"


@unique
class Mode(StrEnum):
    """Testing modes."""
    TPT = "TPT"  # Test Power Transmitter
    TPR = "TPR"  # Test Power Receiver

@unique
class ConnectionStatus(StrEnum):
    """Hardware and tester connection status."""
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    ERROR = "Error"


@unique
class TestResult(StrEnum):
    """Execution and validation test results."""
    PASS = "Pass"
    FAIL = "Fail"
    INCONCLUSIVE = "Inconclusive"
    NOT_RUN = "Not Run"

@unique
class Phase(StrEnum):
    """Qi / MPP protocol transaction phases."""
    PING = "Ping"
    CONFIGURATION = "Configuration"
    NEGOTIATION = "Negotiation"
    POWER_TRANSFER = "PT"
    CALIBRATION = "Calibration"
    RENEGOTIATION = "Renegotiation"


@unique
class PacketResponse(StrEnum):
    """Packet acknowledgment and response types."""
    ACK = "ACK"
    NAK = "NAK"
    ND = "ND"
    ATN = "ATN"


class Enums:
    """
    Consolidated container class providing access to all automation enumerations.
    Allows both namespace access (e.g. Enums.Mode.TPT) and direct imports.
    """
    Product = Product
    Mode = Mode
    ConnectionStatus = ConnectionStatus
    TestResult = TestResult
    Phase = Phase
    PacketResponse = PacketResponse


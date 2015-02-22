class DeviceError(Exception):
    """Exception raised for errors given by the connected device.

    Attributes:
        desc -- A detailed description of the error
    """

    def __init__(self, desc):
        self.desc = expr


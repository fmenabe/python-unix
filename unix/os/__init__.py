class InvalidOS(Exception):
    """Exception raised when an invalid class for an operating system (ie: using
    Ubuntu object for a Red Hat operating system for exemple).
    """
    pass

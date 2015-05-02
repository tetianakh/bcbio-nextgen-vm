"""
Shared constants across the bcbio-nextgen-vm project.
"""
import os

NFS_OPTIONS = "rw,async,nfsvers=3"  # NFS tuning


class PATH:
    BCBIO = os.path.join(os.path.expanduser("~"), '.bcbio')
    EC = os.path.join(BCBIO, "elasticluster")
    EC_CONFIG = os.path.join(EC, "config")
    EC_STORAGE = os.path.join(EC, "storage")
    PICKLE_FILE = os.path.join(EC_STORAGE, "%(cluster)s.pickle")


class LOG:

    NAME = "bcbiovm"
    LEVEL = 10
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    FILE = ""

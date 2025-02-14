import os
from logging import getLogger, basicConfig, StreamHandler, INFO


logger = getLogger()

FORMAT = "%(asctime)s : %(filename)s : %(funcName)s : %(levelname)s : %(message)s"

stream = StreamHandler()
stream.setLevel(INFO)

basicConfig(level=INFO, format=FORMAT, handlers=[stream])

import os
from logging import getLogger, basicConfig, FileHandler, StreamHandler, INFO


logger = getLogger()

FORMAT = "%(asctime)s : %(filename)s : %(funcName)s : %(levelname)s : %(message)s"

file_handler = FileHandler(os.path.join("botlogger", "data.log"))
file_handler.setLevel(INFO)

stream = StreamHandler()
stream.setLevel(INFO)

basicConfig(level=INFO, format=FORMAT, handlers=[file_handler, stream])

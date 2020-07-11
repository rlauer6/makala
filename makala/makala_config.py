import os
import json
import configparser

class MakalaConfig(): # pylint: disable=R0902, disable=C0116
    """makal config object
    """
    @property
    def region(self):
        return self._region

    @property
    def memory(self):
        return self._memory

    @property
    def timeout(self):
        return self._timeout

    @property
    def runtime(self):
        return self._runtime

    @property
    def log_retention(self):
        return self._log_retention

    @property
    def cache_dir(self):
        return self._cache_dir

    @property
    def clean_files(self):
        return self._clean_files

    @property
    def create_role(self):
        return self._create_role

    def __init__(self, **kwargs): # pylint: disable=R0912
        name = kwargs.get("name") or "makala.cfg"

        config = configparser.ConfigParser()
        if os.path.exists(name):
            config.read(name)
        else:
            raise Exception("no {} file found.".format(name))

        defaults = config["DEFAULT"]

        self._region = defaults.get("region", "us-east-1")

        self._timeout = defaults.get("timeout", "120")

        self._memory = defaults.get("memory", "128")

        self._runtime = defaults.get("runtime", "python3.6")

        self._log_retention = defaults.get("log_retention", "7")

        self._cache_dir = defaults.get("cache_dir", "cache")

        if defaults.get("create_role"):
            self._create_role = defaults.get("create_role") == "true"
        else:
            self._create_role = True

        self._template = defaults.get("template", "")

        if defaults.get("clean_files"):
            try:
                self._clean_files = json.loads(config["DEFAULT"]["clean_files"])
            except:
                print("WARNING: clean files must be a JSON list.")
                self._clean_files = []
        else:
            self._clean_files = []

        if not os.path.exists(self._cache_dir):
            os.mkdir(self._cache_dir)

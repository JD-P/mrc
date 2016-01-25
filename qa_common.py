# Constructs that are common to multiple portions of the QA system
import json

class Configuration:
    """Represents a configuration file. Provides an easy interface to modify the
    internal configuration data using __getitem__ and __setitem__ and save 
    changes."""
    def __init__(self, filepath):
        self._filepath = filepath
        config_file = open(filepath)
        self._data = json.load(config_file)
        config_file.close()

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, item):
        self._data[key] = item

    def save():
        """Save the changes made to the configuration to the config file."""
        config_file = open(self._filepath, "w")
        json.dump(self._data, config_file)
        config_file.close()
        return True

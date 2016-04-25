"""
The base file for web bank connect plugins

Author: Alex Yushin <alexis@ww.net>

"""

from selenium import webdriver

# Configuration defaults
PLUGIN_PREFIX = ".".join(__name__.split(".")[:-1])
PLUGIN_SUFFIX = '.Plugin'

# Load plugin
def load_plugin(plugin_name):
    plugin = PLUGIN_PREFIX + '.' + plugin_name + PLUGIN_SUFFIX
    parts = plugin.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m()

# Definition of web bank connector
class Plugin(object):
    logged_in = False

    def open_browser(self):
        """
        Opens the web browser and sets up the required settings if neeeded

        :return:
        """
        fp = webdriver.FirefoxProfile()
        # fp.set_preference("network.proxy.socks_remote_dns", True)
        self.driver = webdriver.Firefox(firefox_profile=fp)

    def login(self, username, password):
        self.open_browser()
        self.logged_in = True

    def list_accounts(self):
        pass

    def logout(self):
        self.close_browser()
        self.logged_in = False

    def close_browser(self):
        self.driver.quit()
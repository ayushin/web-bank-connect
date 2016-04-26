"""
The base file for web bank connect plugins

Author: Alex Yushin <alexis@ww.net>

"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    user_input = raw_input

    # Some reasonable defaults
    DEFAULT_TIMEOUT = 5
    CLICK_SLEEP = 1
    LOGIN_TIMEOUT = 45

    # Plugin interface methods
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

    # Some handy shortcuts
    def wait(self, wait = DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, wait)

    def locate(self, locator, wait = DEFAULT_TIMEOUT):
        """
        This is our own implementation of implicitly_wait with more control.

        :param by:     selenium.webdriver.common.by
        :param arg:
        :param wait:
        :return:
        """
        return self.wait(wait = wait).until(
            EC.visibility_of_element_located(locator))

    def locate_all(self, locator, wait = DEFAULT_TIMEOUT):
        return self.wait(wait = wait).until(
            EC.presence_of_all_elements_located(locator)
        )
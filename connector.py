from selenium import webdriver

# Definition of web bank connector
class Connector:
    def open_browser(self):
        try:
            os.environ['PATH'] = FIREFOX_PATH
        except NameError:
            print "No FIREFOX_PATH setting is defined, trying default PATH..."
            pass

        self.driver = webdriver.Firefox()

    def login(self, username, password):
        pass

    def scrape(self, account, datefrom):
        pass

    def logout(self):
        self.close_browser()
        pass

    def close_browser(self):
        self.driver.quit()

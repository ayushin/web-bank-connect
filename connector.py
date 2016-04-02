from selenium import webdriver

# Definition of web bank connector
class Connector:
    def open_browser(self):
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

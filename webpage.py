#!/usr/bin/env python3

"""Michael duPont - michael@mdupont.com
Premonition Python Tools - web.webpage.py
Uses Selenium to interact/crawl a given web page
"""

# pylint: disable=W0702

#stdlib
import logging, json
from os import path, R_OK, access
from shutil import rmtree
from contextlib import contextmanager
from time import sleep
from random import randint
import tempfile
from copy import deepcopy
#library
from pkg_resources import resource_filename
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.expected_conditions import \
    staleness_of, presence_of_element_located, alert_is_present
from user_agent import generate_user_agent
import socket
#module


#Firefox normal and download preferences
FF_PREFS = {
    'browser.cache.disk.enable': False,
    'browser.cache.offline.enable': False,
    'browser.link.open_newwindow': 2,
    'network.http.connection-timeout': 60,
    'network.http.use-cache': False,
    'security.warn_entering_secure': False,
    'security.ssl.enable_ocsp_must_staple': False,
    'security.ssl.enable_ocsp_stapling': False,
    'security.insecure_field_warning.contextual.enabled': False
}
FF_PROXY_PREFS = {
    'network.proxy.type': 1,
    'network.proxy.no_proxies_on': 'localhost, 127.0.0.1',
    'network.proxy.socks_remote_dns': False,
    'network.proxy.socks_version': 5,
    'signon.autologin.proxy': True,
    'app.update.auto': False,
    'app.update.enabled': False,
    'app.update.silent': False
}

FF_REFERAL_PREFS = {
    "modifyheaders.config.active": False,
    "modifyheaders.config.alwaysOn": False
}
FF_DOWNLOAD_PREFS = {
    'browser.download.folderList': 2,
    'browser.download.manager.showWhenStarting': False,
    'browser.helperApps.neverAsk.saveToDisk': 2,
    'browser.helperApps.neverAsk.saveToDisk': 'application/octet-stream:application/pdf:application/x-pdf:application/force-download:image/tifftext/vcard:text/x-vcard:text/directory;profile=vCard:text/directory',
    'plugin.disable_full_page_plugin_for_types': 'application/pdf:text/vcard',
    'pdfjs.disabled': True,
    'browser.helperApps.alwaysAsk.force': False,
    'browser.download.panel.shown': False
}

class DriverFailure(Exception):
    """Custom exception thrown when the browser connection fails
    """
    def __init__(self, value):
        super().__init__()
        self.value = value
    def __str__(self):
        return repr(self.value)

class WebPage:
    """Provides an API for interacting with selenium and its chosen web driver
    """

    def __init__(self, url: str, browser: str='firefox',
                    proxy: dict=None, uses_recaptcha: bool=False,download_document: bool=False,
                    load_images: bool=True):
        """Init a Selenium driver. Must be given a URL.
        Specify the type of browser and version to use (Firefox, PhantomJS)
        """
        browser = browser.lower()
        self.download_dir = tempfile.TemporaryDirectory()
        self.url = url
        self.browser = browser
        if browser.startswith('firefox'):
            #Generate Firefox Profile from desired preferences
            self.profile = webdriver.FirefoxProfile()
            prefs = deepcopy(FF_PREFS)
            if not load_images:
                prefs['permissions.default.image'] = 2
                prefs['browser.migration.version'] = 9999
                #prefs['permissions.default.stylesheet'] = 2
            #Add referal header
            self.profile.add_extension(resource_filename(__name__, 'modify-headers.xpi'))
            #self.profile.add_extension(resource_filename(__name__, 'canvas-defender.xpi'))
            prefs.update(FF_REFERAL_PREFS)
            #Set user agent to FF46 if the browser will be solving a ReCaptcha
            if uses_recaptcha:
                gen = generate_user_agent(navigator='firefox')
                prefs['general.useragent.override'] = gen[:gen.rfind('/')+1]+'46.0'
            else:
                prefs['general.useragent.override'] = generate_user_agent(device_type=['desktop'])
            if proxy:
                prefs.update(self.__configure_proxy_prefs(proxy))
            if download_document:
                prefs.update(FF_DOWNLOAD_PREFS)
                prefs['browser.download.dir'] = self.download_dir.name
            for pref, val in prefs.items():
                self.profile.set_preference(pref, val)
            try:
                #Allow insecure connections
                self.profile.accept_untrusted_certs = True
                caps = DesiredCapabilities.FIREFOX
                caps['acceptSslCerts'] = True
                location = '/opt/firefox-46/firefox'
                while not access(location,R_OK):
                    sleep(1)
                binary = FirefoxBinary(location)
                self.driver = webdriver.Firefox(
                    self.profile,
                    firefox_binary=binary,
                    #log_path='/dev/null',
                    capabilities=caps)
                self.driver.set_page_load_timeout(60)
            except:
                #Make sure the failed tmp profile gets removed from disk
                if path.isdir(self.profile.path):
                    rmtree(self.profile.path)
                if self.profile.tempfolder is not None:
                    rmtree(self.profile.tempfolder)
                raise DriverFailure('An error occured initializing the Firefox browser')
        elif browser == 'chrome':
            proxy_details = user_agent = None
            PROXY='221.126.249.102:8080'
            self.chrome_profile = tempfile.TemporaryDirectory()
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--proxy-server=%s' % PROXY)
            driver=webdriver.Chrome('/usr/lib/chromium-browser/chromedriver',chrome_options=chrome_options)
            profile_dir = '--user-data-dir='+self.chrome_profile.name
            chrome_switches = ['--allow-outdated-plugins','--allow-running-insecure-content',
            '--crash-on-hang-threads=UI:60,IO:60','--deny-permission-prompts','--disable-component-update',
            '--disable-popup-blocking','--no-default-browser-check','--ignore-ssl-errors',
            '--ignore-certificate-errors',profile_dir,'--no-first-run','--start-maximized',
            '--no-sandbox']
            if not uses_recaptcha:
                user_agent = '--user-agent='+generate_user_agent(device_type=['desktop'])
            if user_agent:
                chrome_switches.append(user_agent)
            if proxy:
                if '@' in proxy['ip']:
                    cred = proxy['ip'].split('@')[0]
                    credentials = {'user':cred.split(':')[0],'pass':cred.split(':')[1]}
                    chrome_options.add_extension(resource_filename(__name__,'closeproxyauth.crx'))
                    chrome_options.add_extension(resource_filename(__name__,'Empty-New-Tab-Page.crx'))
                if 'is_socks5' in proxy and proxy['is_socks5'] == 1:
                    if '@' not in proxy['ip']:
                        p_socks = 'socks5://'+proxy['ip']+':'+str(proxy['port'])
                    else:
                        p_socks = 'socks5://'+proxy['ip'].split('@')[1]+':'+str(proxy['port'])
                    proxy_details = '--proxy-server={}'.format(p_socks)
                else:
                    if '@' not in proxy['ip']:
                        http = 'http://'+proxy['ip']+':'+str(proxy['port'])
                    else:
                        http = 'http://'+proxy['ip'].split('@')[1]+':'+str(proxy['port'])
                    proxy_details = '--proxy-server={}'.format(http)
            if proxy_details:
                chrome_switches.append(proxy_details)
            for chrswt in chrome_switches:
                chrome_options.add_argument(chrswt)
            self.driver = webdriver.Chrome(executable_path="/usr/lib/chromium-browser/chromedriver",chrome_options=chrome_options)
            if proxy and 'ip' in proxy and '@' in proxy['ip']:
                self.configure_proxy(credentials['user'],credentials['pass'])
        elif browser == 'phantomjs':
            try:
                self.driver = webdriver.PhantomJS(
                    service_args=['--ignore-ssl-errors=true']#,
                    #service_log_path='/dev/null'
                    )
                self.driver.set_window_size(1440, 900)
            except:
                raise DriverFailure('An error occured initializing the PhantomJS driver')
        else:
            raise DriverFailure('"{}" is not a valid browser option'.format(browser))

    #These two allow the WebPage to be used in a "with" clause
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.close_page()

    @staticmethod
    def delay(msec: int):
        '''Wait a given number of milliseconds'''
        sleep(msec / 1000)

    @staticmethod
    def get_proxy_resp_header(url: str, port: int, header: str) -> str:
        """Makes a simple request through a proxy and returns the value of a response header"""
        from requests import get
        proxy = 'http://{}:{}'.format(url, port)
        proxies = {'http': proxy}
        resp = get('http://54.91.52.231/', proxies=proxies)
        header_val = resp.headers[header]
        print(header_val)
        return header_val

    def configure_proxy(self,username: str, password: str) -> bool:
        windows = self.driver.window_handles
        self.driver.switch_to_window(windows[len(windows)-1])
        self.driver.close()
        windows = self.driver.window_handles
        self.driver.switch_to_window(windows[len(windows)-1])
        self.driver.find_element_by_id('login').send_keys(username)
        self.driver.find_element_by_id('password').send_keys(password)
        self.driver.find_element_by_id('save').click()

    def __configure_proxy_prefs(self, proxy: dict) -> dict:
        """Returns a dict of profile preferences from a dict of proxy settings
        proxy keys: url, port (, response_header)
        """
        proxy_url, proxy_port = proxy['ip'], proxy['port']
        proxy_prefs = FF_PROXY_PREFS
        #Add custom response header if available
        if 'sticky_ip_header' in proxy and proxy['sticky_ip_header']:
            header = proxy['sticky_ip_header']
            value = self.get_proxy_resp_header(proxy_url, proxy_port, header)
            proxy_prefs["modifyheaders.headers.count"] = 1
            proxy_prefs["modifyheaders.headers.action0"] = "Add"
            proxy_prefs["modifyheaders.headers.name0"] = header
            proxy_prefs["modifyheaders.headers.value0"] = value
            proxy_prefs["modifyheaders.headers.enabled0"] = True
            proxy_prefs["modifyheaders.config.active"] = False
            proxy_prefs["modifyheaders.config.alwaysOn"] = True
        #Check for credentials in proxy url
        if '@' in proxy_url and proxy['is_socks5'] != 1:
            creds, proxy_url = proxy_url.split('@')
            #self.profile.add_extension(resource_filename(__name__, 'autoauth.xpi'))
            self.profile.add_extension(resource_filename(__name__, 'close-proxy-auth.xpi'))
            from base64 import b64encode
            creds = b64encode(creds.encode('ascii')).decode('utf-8')
            proxy_prefs['extensions.closeproxyauth.authtoken'] = creds
        #Set either socks or the other protocols
        if 'is_socks5' in proxy and proxy['is_socks5'] == 1:
            proxy_prefs['network.proxy.socks'] = proxy_url
            proxy_prefs['network.proxy.socks_port'] = proxy_port
        else:
            for protocol in ('http', 'ssl', 'ftp'):
                proxy_prefs['network.proxy.'+protocol] = proxy_url
                proxy_prefs['network.proxy.'+protocol+'_port'] = proxy_port
        return proxy_prefs

    def get_page(self) -> str:
        '''Returns the url of the current web page'''
        return self.driver.execute_script("return window.location.href;")

    def get_source(self) -> str:
        """Returns the page's source HTML
        """
        return self.driver.execute_script("return document.documentElement.outerHTML")

    def load_page(self, url: str=''):
        '''Load a given URL or reload the current URL'''
        if url:
            self.url = url
        self.driver.get(self.url)
        #This waits for 5 seconds and handles alert popups
        try:
            if self.browser != 'phantomjs':
                WebDriverWait(self.driver, 5).until(alert_is_present())
                alert = self.driver.switch_to_alert()
                alert.accept()
            sleep(5)
        except Exception as e:
            print(e)

    def accept_alerts(self):
        try:
            if alert_is_present():
                alert = self.driver.switch_to_alert()
                alert.accept()
                sleep(1)
        except Exception as e:
            print(e)

    def back(self):
        '''Go back one page'''
        self.driver.execute_script("window.history.go(-1)")

    def close_page(self):
        '''Close the page/driver'''
        try:
            self.download_dir.cleanup()
            self.driver.quit()
        except:
            pass
        #Remove the profile if it exists
        if hasattr(self, 'profile'):
            if path.isdir(self.profile.path):
                rmtree(self.profile.path)
            if self.profile.tempfolder is not None:
                rmtree(self.profile.tempfolder)
        elif hasattr(self, 'chrome_profile'):
            if path.isdir(self.chrome_profile.name):
                rmtree(self.chrome_profile.name)
            self.chrome_profile == None

    def window_len(self) -> int:
        '''Returns to number of open windows for this driver'''
        return len(self.driver.window_handles)

    def close_window(self, override: bool=False):
        '''Closes the top-most window. Will only close last window if overriden'''
        if self.window_len() > 1 or override:
            self.driver.close()
            windows = self.driver.window_handles
            self.driver.switch_to_window(windows[len(windows)-1])

    def add_cookies(self, cookies: dict):
        '''Add a list of cookies to the driver'''
        for cookie in cookies:
            self.driver.add_cookie(cookie)

    def get_cookies(self) -> dict:
        '''Returns a set of current cookie dictionaries'''
        return self.driver.get_cookies()

    def clear_cookies(self):
            '''Deletes all cookies from browser'''
            self.driver.delete_all_cookies()

    @staticmethod
    def trim_exception(exc: str) -> str:
        '''Removes excess stacktrace from exception string'''
        index = exc.find('\n')
        if index > -1:
            return exc[:index]
        return exc

    def switch_iframe(self, xpath: str=None) -> bool:
        '''Returns focus to the main page before switching to an iframe at a given xpath'''
        try:
            self.driver.switch_to_default_content()
            if xpath:
                iframe = self.driver.find_element_by_xpath(xpath)
                self.driver.switch_to_frame(iframe)
            return True
        except:
            return False

    def changed_to_nested_iframe(self, xpath: str=None) -> bool:
        '''Returns focus to the main page before switching to an iframe at a given xpath'''
        try:
            if xpath:
                iframe = self.driver.find_element_by_xpath(xpath)
                self.driver.switch_to_frame(iframe)
            return True
        except:
            return False

    def xpath_len(self, xpath: str) -> int:
        '''Returns the number of elements matching a given xpath'''
        try:
            return len(self.driver.find_elements_by_xpath(xpath))
        except:
            logging.warning('WP - Fields not found')
            return 0

    def get_attribute(self, xpath: str, attr: str, out: bool=True) -> str:
        '''Returns the text associated with an attribute for a given xpath'''
        try:
            return self.driver.find_element_by_xpath(xpath).get_attribute(attr)
        except:
            if out:
                logging.warning('WP - Attribute not found')
            return ''

    def get_text(self, xpath: str) -> str:
        '''Returns the text for one or more elements at a given XPath'''
        try:
            text = []
            elements = self.driver.find_elements_by_xpath(xpath)
            for item in elements:
                if item.text:
                    text.append(item.text.strip())
                else:
                    text.append(item.get_attribute('value'))
            return '|'.join(set(text))
        except:
            logging.warning('WP - Text not found')
            return ''
    
    def list_text(self, xpath: str) -> str:
        '''Returns the text for one or more elements at a given XPath'''
        try:
            text = []
            data = []
            elements = self.driver.find_elements_by_xpath(xpath)
            #print(elements)
            for item in elements:
                if item.text:
                    text.append(item.text.strip())
                else:
                    text.append(item.get_attribute('value'))
            #print(text)
            for word in list(text):
                if word is None:
                    data.append("")
                else:
                    string=word.strip(':')
                    data.append(string)
            print(data)
            return data 
        except Exception as e:
            logging.warning(e)
            return ''

    def set_text(self, xpath: str, text: str) -> bool:
        '''Sets the text for a text field at a given XPath'''
        try:
            text_field = self.driver.find_element_by_xpath(xpath)
            if text_field:
                ActionChains(self.driver).move_to_element(text_field).click(text_field).perform()
                sleep(1)
                text_field.clear()
                text_field.send_keys(text)
                self.driver.find_element_by_xpath('/html//body').click()
                return True
            return False
        except:
            logging.warning('WP - Field not found')
            return False

    @contextmanager
    def wait_for_load(self, timeout: int=60) -> 'generator-with':
        '''Wait until a new page has finished loading in the same window'''
        old_page = self.driver.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.driver, timeout).until(staleness_of(old_page))

    @contextmanager
    def wait_for_window(self, timeout: int=60) -> 'generator-with':
        '''Wait until a new window opens and then that page finishes loading'''
        old_handles = self.driver.window_handles
        yield
        WebDriverWait(self.driver, timeout).until(
            lambda driver: len(old_handles) != self.window_len()
        )
        self.driver.switch_to_window(self.driver.window_handles[-1])
        WebDriverWait(self.driver, timeout).until(
            presence_of_element_located((By.TAG_NAME, 'html')) #visibility_of_element_located
        )

    def click_element(self, xpath: str, loadwait: bool=False,
                        new_window: bool=False, out: bool=True) -> bool:
        '''Clicks an element at a given XPath. Works with buttons and links'''
        try:
            button = self.driver.find_element_by_xpath(xpath)
            if button:
                #We can opt to wait for the new page or window to finish loading
                #Overwrite value until fixed
                loadwait = False
                if loadwait:
                    if new_window:
                        with self.wait_for_window():
                            ActionChains(self.driver).move_to_element(button).perform()
                            sleep(.5)
                            button.click()
                    else:
                        with self.wait_for_load():
                            ActionChains(self.driver).move_to_element(button).perform()
                            sleep(.5)
                            button.click()
                else:
                    ActionChains(self.driver).move_to_element(button).perform()
                    button.click()
                #Always make sure that the most recent window is active
                self.driver.switch_to_window(self.driver.window_handles[-1])
                self.accept_alerts()
                sleep(.01)
                return True
            return False
        except:
            if out:
                logging.warning('WP - Element not found')
            return False

    def click_element_from_fields(self, xpath: str, text: str) -> bool:
        """
            Clicks an element out of the page with a name provided in fields
        """
        try:
            link = self.driver.find_element_by_xpath(xpath)
            self.driver.execute_script("arguments[0].scrollIntoView();",link)
            ActionChains(self.driver).move_to_element(link).perform()
            sleep(.5)
            link.click()
            self.accept_alerts()
            return True
        except:
            logging.warning('WP - Element not found')
            return False

    def select_option(self, xpath: str, text: str) -> bool:
        '''Clicks an option of a select field at a given xpath
        whose text matches or starts with some given text'''
        try:
            select = self.driver.find_element_by_xpath(xpath)
            ActionChains(self.driver).move_to_element(select).perform()
            sleep(.5)
            select.click()
            sleep(.1)
            select.send_keys(text)
            sleep(.1)
            self.driver.find_element_by_xpath('/html//body').click()
            return True
            # select = Select(self.driver.find_element_by_xpath(xpath))
            # #Attempt the easy version before the long version
            # try:
            #     #This version if faster but matches EXACT text
            #     select.select_by_visible_text(text)
            #     return True
            # except:
            #     #This is slower but can match the start of the text
            #     for opt in select.options:
            #         if opt.text.startswith(text):
            #             opt.click()
            #             return True
            #     raise
        except:
            logging.warning('WP - Select/Option not found')
            return False

    
#http://selenium-python.readthedocs.org/api.html
#http://stackoverflow.com/questions/17540971/how-to-use-selenium-with-python
#http://www.marinamele.com/selenium-tutorial-web-scraping-with-selenium-and-python
#http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil
#http://stackoverflow.com/questions/25027385/using-selenium-on-raspberry-pi-headless
#http://stackoverflow.com/questions/27626783/python-selenium-browser-driver-back
#https://github.com/seleniumhq/selenium-google-code-issue-archive/issues/1934
#https://docs.python.org/3/reference/datamodel.html#with-statement-context-managers
#http://www.obeythetestinggoat.com/how-to-get-selenium-to-wait-for-page-load-after-a-click.html

#https://chromium.googlesource.com/chromium/src/+/master/chrome/common/pref_names.cc Chrome preferences
#https://chromium.googlesource.com/chromium/src/+/master/chrome/common/chrome_switches.cc Chrome switches
#https://peter.sh/experiments/chromium-command-line-switches/ full list of chrome commands

#https://christopher.su/2015/selenium-chromedriver-ubuntu/
#Or use PhantomJS which is designed to be headless, may break Captcha
#
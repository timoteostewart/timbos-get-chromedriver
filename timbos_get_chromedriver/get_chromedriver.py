import json
import logging
import os

import selenium_stealth
import seleniumbase
import seleniumwire
import seleniumwire.undetected_chromedriver as sw_uc
import undetected_chromedriver as ufa_uc
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from . import update_chromedriver

logger = logging.getLogger(__name__)


def patched_uc_quit(self):
    try:
        self.service.process.kill()
        logger.debug("webdriver process ended")
    except (AttributeError, RuntimeError, OSError):
        pass
    try:
        self.reactor.event.set()
        logger.debug("shutting down reactor")
    except AttributeError:
        pass
    try:
        os.kill(self.browser_pid, 15)
        logger.debug("gracefully closed browser")
    except Exception as exc:
        pass


def get_chromedriver(
    *,
    addl_chrome_options_args=None,
    chromedrivers_base_path=None,
    headless=True,
    incognito=True,
    profile_path=None,  # don't use
    proxy_string=None,
    root_cert_path=None,
    use_sb_uc=None,  # seleniumbase
    use_selenium_stealth=True,
    use_selenium_wire=True,
    use_selenium_wire_webdriver=True,
    use_sw_uc=True,  # seleniumwire
    use_ufa_uc=None,  # ultrafunkamsterdam
    user_agent=None,
    user_data_dir=None,
):
    for dir in [profile_path, user_data_dir]:
        if dir is not None:
            if not os.path.isdir(dir):
                raise FileNotFoundError(f"Directory {dir} does not exist")

    config_path_to_chromedriver = (
        update_chromedriver.match_chromedriver_to_chrome_browser(
            chromedrivers_base_path=chromedrivers_base_path
        )
    )

    if use_sw_uc:
        chrome_options = sw_uc.ChromeOptions()
    else:
        chrome_options = ChromeOptions()

    # options.preferences.default = {
    #         search: {
    #         suggest_enabled: false,
    #         },
    #         safebrowsing: {
    #         enabled: false,
    #         },
    #         translate: {
    #         enabled: false,
    #         },
    #         'signin': {
    #         'allowed': false,
    #         'allowed_on_next_startup': false,
    #         },
    #         'credentials_enable_autosignin': false,
    #         'credentials_enable_service': false,
    #         'alternate_error_pages': {
    #         'enabled': false,
    #         },
    #     }

    ## default additional chrome_options arguments
    if addl_chrome_options_args is None:
        addl_chrome_options_args = [
            "--disable-auto-reload",
            "--disable-background-networking",
            "--disable-breakpad",
            "--disable-crash-reporter",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsFetching,OptimizationTargetPrediction,OptimizationHints",
            "--disable-fetching-hints-at-navigation-start",
            "--ignore-certificate-errors",
            "--verbose",
            "--webview-disable-safebrowsing-support",
        ]
    for arg in addl_chrome_options_args:
        chrome_options.add_argument(arg)

    ## headless
    if headless is True:
        if use_ufa_uc is not True:
            chrome_options.add_argument("--headless")
    if use_ufa_uc is True:
        chrome_options.headless = headless

    ## incognito
    if incognito is True:
        chrome_options.add_argument("--incognito")

    ## user_data_dir
    if user_data_dir and incognito is not True:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    if profile_path and incognito is not True:
        chrome_options.add_argument(f"--profile-directory={profile_path}")

    if use_ufa_uc is not True:
        chrome_options.add_experimental_option(
            "prefs",
            {
                "intl.accept_languages": "en,en_US",
                "download.prompt_for_download": False,
                "download.default_directory": "/tmp",
                "automatic_downloads": 2,
                "download_restrictions": 3,
                "notifications": 2,
                "media_stream": 2,
                "media_stream_mic": 2,
                "media_stream_camera": 2,
                "durable_storage": 2,
            },
        )

    if use_ufa_uc is not True and use_sw_uc is not True:
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

    if user_agent:
        chrome_options.add_argument(f"--user-agent={user_agent}")

    chrome_service = ChromeService(executable_path=config_path_to_chromedriver)

    try:
        if use_ufa_uc is True:
            driver = ufa_uc.Chrome(
                options=chrome_options, service=chrome_service, use_subprocess=True
            )

        elif use_sb_uc is True:
            driver = seleniumbase.Driver(
                undetectable=True,
                headless2=headless,
                agent=user_agent,
                proxy=proxy_string,
                user_data_dir=user_data_dir,
                incognito=incognito,
                use_wire=use_selenium_wire,
            )

        elif use_selenium_wire_webdriver is True:
            # TODO: be able to provide cookies
            if use_sw_uc is True:
                which_driver = sw_uc.Chrome
            else:
                which_driver = seleniumwire.webdriver.Chrome

            chrome_options.headless = None

            seleniumwire_options = {
                "suppress_connection_errors": True,
                "verify_ssl": False,
            }
            if root_cert_path:
                seleniumwire_options["ssl_insecure_requests_allowed"] = True
            if proxy_string:
                seleniumwire_options["proxy"] = {
                    "http": proxy_string,
                    "https": proxy_string,
                    "no_proxy": "localhost",
                }

            driver = which_driver(
                options=chrome_options,
                service=chrome_service,
                seleniumwire_options=seleniumwire_options,
            )
        else:
            driver = seleniumwire.webdriver.Chrome(
                options=chrome_options, service=chrome_service
            )

    except Exception as exc:
        logger.warning(str(exc))
        raise

    if use_ufa_uc is True or use_sw_uc is True:
        # monkey patch uc's quit()
        driver.quit = lambda: patched_uc_quit(driver)

    if use_selenium_stealth is True:
        selenium_stealth.stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

    implicit_wait_time = 180
    driver.set_page_load_timeout(implicit_wait_time)
    driver.implicitly_wait(implicit_wait_time)

    return driver

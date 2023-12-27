import logging
import random
import time
import traceback
from queue import Queue

import bs4
from selenium.webdriver.common.by import By

import timbos_get_chromedriver as tgc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="tgc_demo.log",
    filemode="a",
)


logger = logging.getLogger(__name__)


# be sure to install https://raw.githubusercontent.com/wkeeling/selenium-wire/master/seleniumwire/ca.crt into the Chrome browser that will be used


def report_wan_ip_address(driver=None):
    url = "https://icanhazip.com/"
    driver.get(url)
    ip_addr = driver.find_elements(By.CSS_SELECTOR, "pre")[0].text
    return ip_addr


def get_page_source3(driver=None, url=None):
    if not driver:
        raise Exception("driver must be provided")
    if not url:
        raise Exception("url must be provided")
    try:
        got_200_response = False
        driver.get(url)
        for r in driver.requests:
            if r.response:
                if r.url == url and r.response.status_code == 200:
                    got_200_response = True
    except Exception as exc:
        logger.warning(str(exc))
        raise

    if got_200_response:
        html = driver.page_source
        return html

    raise Exception("Did not get a 200 response")


def shutdown_driver(driver=None):
    try:
        driver.close()
        driver.quit()
    except Exception as exc:
        if "Message: disconnected: not connected to DevTools" in (exc_str := str(exc)):
            pass
        else:
            logger.warning(exc_str)


def get_page_source2(url=None, proxy_string_gen_instance=None):
    inter_scrape_delay = 2
    attempts_left = 4

    while attempts_left > 0:
        attempts_left -= 1

        time.sleep(inter_scrape_delay)

        # get driver
        proxy_string = next(proxy_string_gen_instance)
        try:
            driver = tgc.get_chromedriver(
                proxy_string=proxy_string,
            )
        except Exception as exc:
            logger.warning(str(exc))
            continue

        # get page source
        page_source = None
        try:
            driver.get(url)
            page_source = str(driver.page_source)
            shutdown_driver(driver=driver)
        except Exception as exc:
            logger.warning(str(exc))

        if not page_source:
            continue

        # check for error messages in page_source
        hints_of_error = [
            "<h1>502 Bad Gateway</h1>",
            "<p>ProtocolException",
            "<title>502 Bad Gateway</title>",
        ]
        error_messages = [
            "An existing connection was forcibly closed by the remote host",
            "No connection could be made because the target machine actively refused it"
            "Socket error: Connection closed unexpectedly",
            "SOCKS5 authentication failed",
        ]

        found_hint_of_error = False
        found_specific_error = False
        for each_hint in hints_of_error:
            if each_hint in page_source:
                found_hint_of_error = True
                break

        if found_hint_of_error:
            for each_problem in error_messages:
                if each_problem in page_source:
                    found_specific_error = True
                    break

        if found_hint_of_error or found_specific_error:
            inter_scrape_delay *= 2

        else:
            return page_source


def proxy_string_gen(proxy_credentials=None):
    proxy_accounts = proxy_credentials["accounts"]
    weights = proxy_credentials["weights"]
    last_selected_list = None
    last_selected_host = None

    while True:
        # Select a list based on the weights
        selected_list = random.choices(proxy_accounts, weights=weights, k=1)[0]

        if selected_list == last_selected_list and len(selected_list) > 1:
            # Ensure the same name is not repeated if the same list is selected again
            choices = [host for host in selected_list if host != last_selected_host]
            selected_host = random.choice(choices)
        else:
            # Select a random name from the chosen list
            selected_host = random.choice(selected_list)

        yield selected_host

        # Update the last selected list and name
        last_selected_list = selected_list
        last_selected_host = selected_host


def get_proxy_string_gen_instance(proxy_credentials=None):
    weights = []
    accounts = []

    for each_account in proxy_credentials["accounts"]:
        weights.append(proxy_credentials["weights"][each_account])
        cur_account = []
        proxy_user = proxy_credentials["accounts"][each_account]["username"]
        proxy_pass = proxy_credentials["accounts"][each_account]["password"]

        for each_protocol in proxy_credentials["accounts"][each_account]["hosts"]:
            for each_host in proxy_credentials["accounts"][each_account]["hosts"][
                each_protocol
            ]:
                cur_account.append(
                    f"{each_protocol}://{proxy_user}:{proxy_pass}@{each_host[0]}:{each_host[1]}"
                )

        accounts.append(cur_account)

    proxy_credentials_by_accounts_and_weights = {
        "accounts": accounts,
        "weights": weights,
    }

    proxy_string_gen_instance = proxy_string_gen(
        proxy_credentials=proxy_credentials_by_accounts_and_weights
    )
    return proxy_string_gen_instance


def get_archive_urls(orig_url=None, proxy_string_gen_instance=None):
    res = []

    # WBM

    # archive.is

    return res


if __name__ == "__main__":
    # get urls

    proxy_credentials = {}

    # start with an original URL

    # generate additional archive URLs as additional sources

    # we'll need to do some scraping to retrieve the WBM and archive.is sources
    # scrape HTML from all those URLs
    # extract articles from these HTML strings
    # synthesize article from the multiple extracts
    # convert synthesized article into audio

    url = "https://www.nytimes.com/2023/11/19/technology/sam-altman-openai-board.html"
    url = "https://bot.sannysoft.com/"
    url = "https://bot.incolumitas.com/"

    # multiple_urls = []
    # multiple_urls.append(url)

    # multiple_urls.extend(
    #     get_archive_urls(
    #         orig_url=url,
    #         proxy_string_gen_instance=get_proxy_string_gen_instance(
    #             proxy_credentials=proxy_credentials
    #         ),
    #     )
    # )

    html = get_page_source2(
        url=url,
        proxy_string_gen_instance=get_proxy_string_gen_instance(
            proxy_credentials=proxy_credentials
        ),
    )

    with open("out.html", mode="w", encoding="utf-8") as fh:
        fh.write(html)

import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logger = logging.getLogger(__name__)


def wait_until_notebook_loaded(driver, timeout=10):
    """Wait until the Jupyter Notebook is loaded."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "notebook-container"))
        )
    except TimeoutException:
        logger.exception("Timed out waiting for page to load")
        driver.quit()


def wait_until_notebook_list_loaded(driver, timeout=10):
    """Wait until the Jupyter Notebook home page (list of files) is loaded."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#notebook_list > div > div > a > span")
            )
        )
    except TimeoutException:
        logger.exception("Timed out waiting for page to load")
        driver.quit()


def wait_until_loaded(driver, timeout=10):
    """Wait until the page is ready."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        logger.exception("Timed out waiting for page to load")
        driver.quit()


def wait_until_new_window(driver, current_handles, timeout=10):
    """Wait until the page is ready."""
    try:
        WebDriverWait(driver, timeout).until(EC.new_window_is_opened(current_handles))
    except TimeoutException:
        logger.exception("Timed out waiting for a new window to open")
        driver.quit()


def is_browser_disconnected(driver):
    """Check if the browser is disconnected."""
    # get_log is not supported by Firefox
    # return driver.get_log("driver")[-1]["message"] == DISCONNECTED_MSG    # not supported by Firefox
    try:
        _ = driver.window_handles
        return False
    except Exception:
        return True

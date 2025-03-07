from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


def wait_until_notebook_loaded(driver: WebDriver, timeout: int = 30):
    """Wait until the Jupyter Notebook is loaded."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "notebook-container"))
        )
    except TimeoutException:
        logger.exception("Timed out waiting for page to load")
        driver.quit()

    try:
        WebDriverWait(driver, timeout).until(
            # Sometimes if kernel is null, it will hang, so we check that.
            lambda d: d.execute_script("return Jupyter.notebook.kernel == null")
            is False
        )
    except TimeoutException:
        logger.exception("Timed out waiting for kernel to load (null)")
        driver.quit()

    try:
        WebDriverWait(driver, timeout).until(
            # Sometimes if kernel is null, it will hang, so we check that.
            lambda d: d.execute_script("return Jupyter.notebook.kernel.is_connected()")
            is True
        )
    except TimeoutException:
        logger.exception("Timed out waiting for kernel to load")
        driver.quit()


def wait_until_notebook_list_loaded(driver: WebDriver, timeout: int = 10):
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


def wait_until_loaded(driver: WebDriver, timeout: int = 10):
    """Wait until the page is ready."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        logger.exception("Timed out waiting for page to load")
        driver.quit()


def wait_until_new_window(
    driver: WebDriver, current_handles: list[str], timeout: int = 10
):
    """Wait until the page is ready."""
    try:
        WebDriverWait(driver, timeout).until(EC.new_window_is_opened(current_handles))
    except TimeoutException:
        logger.exception("Timed out waiting for a new window to open")
        driver.quit()


def is_browser_disconnected(driver: WebDriver):
    """Check if the browser is disconnected."""
    try:
        _ = driver.window_handles
    except Exception:  # noqa: BLE001
        return True
    return False

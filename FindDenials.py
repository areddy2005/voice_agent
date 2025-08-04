from warnings import filters
from ArchyDemoLogin import login_to_archy
from ArchyDemoLogin import login_to_archy
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait       # ← add this
from selenium.webdriver.support import expected_conditions as EC  # ← and this
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from FileMove import organize_latest_zip
import time

def find_denials():
    EMAIL    = "chase+sandbox@archy.com"
    PASSWORD = "NBM6xtp1vjg9juz*djd"

    # grab a browser already logged in
    driver = login_to_archy(EMAIL, PASSWORD, sandbox=True)
    wait   = WebDriverWait(driver, 10)  

    claims_btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        "svg[aria-label='Claims']"
    )))
    claims_btn.click()

    status_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space(text())='Status']"))
    )
    status_btn.click()

    denied_label = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//label[.//span[normalize-space(text())='Denied']]"
        ))
    )
    denied_label.click()


    filters_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//button[@type='submit' and normalize-space(text())='Apply Filters']"
        ))
    )
    filters_btn.click()


    return driver
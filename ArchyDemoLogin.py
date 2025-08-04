# archy_login.py
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def login_to_archy(email: str, password: str, sandbox: bool = True, pause_on_ready: bool = False):
    """
    Launches Chrome, logs into Archy (sandbox or prod), and returns the WebDriver.
    If pause_on_ready=True, will wait for Enter before returning.
    """
    url = (
        "https://practice.demo.archy.com/auth/sign-in"
        if sandbox
        else "https://portal.archy.com/auth/sign-in"
    )

    driver = webdriver.Chrome()      # ensure chromedriver is on your PATH
    wait   = WebDriverWait(driver, 10)

    # 1) go to the right login page
    driver.get(url)

    # 2) fill email
    email_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_el.clear()
    email_el.send_keys(email)

    # 3) fill password
    pwd_el = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd_el.clear()
    pwd_el.send_keys(password)

    # 4) click Sign in
    sign_in_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    sign_in_btn.click()

    # 5) wait for portal to load
    wait.until(EC.url_contains("practice.demo.archy.com" if sandbox else "portal.archy.com"))

    if pause_on_ready:
        input("🚀 Logged in! Press Enter to continue…")

    return driver

if __name__ == "__main__":
    # quick test when you run `python archy_login.py`
    EMAIL    = "chase+sandbox@archy.com"
    PASSWORD = "NBM6xtp1vjg9juz*djd"
    drv = login_to_archy(EMAIL, PASSWORD, sandbox=True, pause_on_ready=True)
    drv.quit()
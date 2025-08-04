import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# — your creds (hard-coded for now)
EMAIL    = "chase+sandbox@archy.com"
PASSWORD = "NBM6xtp1vjg9juz*djd"

# — start Chrome (make sure chromedriver is on your PATH)
driver = webdriver.Chrome()
wait   = WebDriverWait(driver, 10)

try:
    # 1. Go to the Archy homepage
    driver.get("https://archy.com")

    # 2. (Optional) Dismiss cookie banner if present
    try:
        accept_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a[fs-cc='allow']")
        ))
        accept_btn.click()
        print("🍪 Cookies accepted")
    except TimeoutException:
        # no banner showed up
        pass

    # 3. Click the "Login" dropdown
    login_dropdown = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "//div[normalize-space(text())='Login']"
    )))
    login_dropdown.click()

    # 4. Click the "Practice Portal" item
    practice_portal = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "//div[contains(@class,'navbar_item-right')]//div[normalize-space(text())='Practice Portal']"
    )))
    practice_portal.click()

    # 5. Wait for the sign-in form to load, then fill in creds
    email_in = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, "input[placeholder='example@gmail.com']"
    )))
    pass_in  = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Enter Password']")

    email_in.clear()
    email_in.send_keys(EMAIL)
    pass_in.clear()
    pass_in.send_keys(PASSWORD)

    # 6. Click "Sign in"
    sign_in_btn = driver.find_element(
        By.XPATH, "//button[contains(normalize-space(.), 'Sign in')]"
    )
    sign_in_btn.click()

    # 7. (Optional) Confirm landing in portal
    wait.until(EC.url_contains("portal.archy.com"))
    print("✅ Logged in successfully!")

finally:
    # give yourself a moment to see the result
    time.sleep(30)
    driver.quit()

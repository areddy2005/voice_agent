from ArchyDemoLogin import login_to_archy
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from FileMove import organize_latest_zip
import time


def export_patient_images(EMAIL, PASSWORD, patient_name: str, IMAGE_NUMBER, sandbox: bool = True) -> None:
    # login and setup
    driver = login_to_archy(EMAIL, PASSWORD, sandbox=sandbox)
    wait = WebDriverWait(driver, 10)

    # Click the Patients tab
    patients_btn = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        "svg[aria-label='Patients']"
    )))
    patients_btn.click()

    # Search for patient
    search_bar = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, "input[placeholder='Search']"
    )))
    search_bar.clear()
    search_bar.send_keys(patient_name)
    search_bar.send_keys(Keys.ENTER)

    # Wait for search results to populate
    wait.until(EC.visibility_of_element_located((
        By.XPATH,
        "//div[contains(text(),'Result') and contains(text(),'1')]"
    )))

    # Click the first result
    rows = wait.until(EC.presence_of_all_elements_located((
        By.CSS_SELECTOR,
        "div.contents.group[role='row']"
    )))
    first_row = rows[0]
    name_button = first_row.find_element(By.XPATH, ".//button[1]")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", name_button)
    wait.until(EC.element_to_be_clickable((By.XPATH, ".//button[1]")))
    name_button.click()

    # Navigate to Images
    images_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href$='/imaging']")))
    images_link.click()

    # Open specified image
    btn_xpath = (
        f"(//div[@role='row']//button"
        f"[contains(normalize-space(.), '{IMAGE_NUMBER}')])[1]"
    )
    mount_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
    driver.execute_script("arguments[0].scrollIntoView(true);", mount_btn)
    ActionChains(driver).double_click(mount_btn).perform()

    # Export original images
    export_toggle = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        "button[aria-label^='Export']"
    )))
    export_toggle.click()
    export_original_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//button[normalize-space(text())='Export Original Images']"
    )))
    export_original_btn.click()

    # Organize and move the ZIP
    organize_latest_zip()

    # Allow time for download
    time.sleep(15)

    # Quit browser
    driver.quit()

from selenium_driverless.sync import webdriver
from selenium_driverless.types.by import By


options = webdriver.ChromeOptions()
options.add_argument()
driver = webdriver.Chrome(options=options)
driver.maximize_window()
driver.get("https://abrahamjuliot.github.io/creepjs/")
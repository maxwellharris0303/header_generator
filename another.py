from flask import Flask, jsonify, request
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import *
from time import sleep


app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)
driver.get("file:///D:/header_generator/1.html")

# Route to trigger the async function in the background and get the result
@app.route('/get_popdata', methods=['POST'])
def run_async_task():
    driver.refresh()
    popData = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[id=\"popData\"]"))).get_attribute('value')
    return popData

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

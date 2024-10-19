import asyncio
import requests
from flask import Flask, jsonify, request
from threading import Thread, Event
from queue import Queue
import base64
import time
import traceback

from cdp_socket.exceptions import CDPError
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
import json
import os

app = Flask(__name__)

# A queue to store the result
result_queue = Queue()
async def on_request(params, global_conn):
    if "telemetry" not in params["request"]["url"] and "https://identity.o2.co.uk/auth/password_o2" in params["request"]["url"]:
        with open('result/data.json', 'w') as json_file:
            json.dump(params, json_file)

    url = params["request"]["url"]
    method = params["request"]["method"]
    if "product?" in url and method == "GET":
        headers = params["request"]["headers"]
        print("=========================")
        headers['Host'] = 'bck.hermes.com'
        for header_name, header_value in headers.items():
            print(f"'{header_name}' : '{header_value}'")
        print("=========================")
        with open('data.json', 'w') as json_file:
            json.dump(headers, json_file)
        
    _params = {"requestId": params['requestId']}
    if params.get('responseStatusCode') in [301, 302, 303, 307, 308]:
        # redirected request
        return await global_conn.execute_cdp_cmd("Fetch.continueResponse", _params)
    else:
        try:
            body = await global_conn.execute_cdp_cmd("Fetch.getResponseBody", _params, timeout=1)
        except CDPError as e:
            if e.code == -32000 and e.message == 'Can only get response body on requests captured after headers received.':
                # print(params, "\n", file=sys.stderr)
                traceback.print_exc()
                await global_conn.execute_cdp_cmd("Fetch.continueResponse", _params)
            else:
                raise e
        else:
            start = time.perf_counter()
            body_decoded = base64.b64decode(body['body'])

            # modify body here

            body_modified = base64.b64encode(body_decoded).decode("ascii")
            fulfill_params = {"responseCode": 200, "body": body_modified, "responseHeaders": params["responseHeaders"]}
            fulfill_params.update(_params)
            if params["responseStatusText"] != "":
                # empty string throws "Invalid http status code or phrase"
                fulfill_params["responsePhrase"] = params["responseStatusText"]

            _time = time.perf_counter() - start
            if _time > 0.01:
                print(f"decoding took long: {_time} s")
            await global_conn.execute_cdp_cmd("Fetch.fulfillRequest", fulfill_params)
            # print("Mocked response", url)
# Your asynchronous main function
async def main(username, password):
    options = webdriver.ChromeOptions()
    async with webdriver.Chrome(max_ws_size=2 ** 30, options=options) as driver:
        driver.base_target.socket.on_closed.append(lambda code, reason: print(f"chrome exited"))

        global_conn = driver.base_target
        await global_conn.execute_cdp_cmd("Fetch.enable",
                                          cmd_args={"patterns": [{"requestStage": "Response", "urlPattern": "*"}]}, timeout=100)
        await global_conn.add_cdp_listener("Fetch.requestPaused", lambda data: on_request(data, global_conn))

        await driver.get("https://accounts.o2.co.uk/signin", timeout=60, wait_load=False)
        
        while True:
            try:
                allow_cookie_button = await driver.find_element(By.CSS_SELECTOR, "button[aria-label=\"Accept all cookies button\"]")
                await allow_cookie_button.click()
                break
            except:
                await asyncio.sleep(0.2)

        # await asyncio.sleep(2)
        # USERNAME = "sdfwer23"
        # PASSWORD = "sdfwer23"
        while True:
            try:
                username_input = await driver.find_element(By.CSS_SELECTOR, "input[id=\"username\"]")
                await username_input.write(username)
                break
            except:
                await asyncio.sleep(0.2)
        password_input = await driver.find_element(By.CSS_SELECTOR, "input[id=\"password\"]")
        await password_input.write(password)

        signin_button = await driver.find_element(By.CSS_SELECTOR, "input[value=\"Sign in\"]")
        await signin_button.click()

        while True:
            try:
                with open('result/data.json', 'r', encoding='utf-8') as file:
                    data = json.load(file)
                break
            except:
                await asyncio.sleep(0.2)

        os.remove('result/data.json')
        # await asyncio.sleep(2)
        # result = {"status": "success", "data": "Async task completed!"}
        return data['request']['postData']

# A wrapper function to run the async function using asyncio.run()
def run_async(username, password):
    result = asyncio.run(main(username, password))
    result_queue.put(result)  # Put the result in the queue

# Route to trigger the async function in the background and get the result
@app.route('/get_popdata', methods=['GET'])
def run_async_task():
    data = request.get_json()
    print(data)
    username = data["username"]
    password = data['password']
    # Run the async function in a background thread
    thread = Thread(target=run_async, args=(username, password))
    thread.start()

    # Wait for the result to be available
    result = result_queue.get()  # This will block until the result is available
    return jsonify(result), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

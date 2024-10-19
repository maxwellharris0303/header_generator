import asyncio
import base64
import sys
import time
import traceback

from cdp_socket.exceptions import CDPError
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
import random
import json


async def on_request(params, global_conn):
    with open('index.txt', 'r') as file:
        content = file.read()
    index = int(content)
    
    with open(f'result/data{index}.json', 'w') as json_file:
        json.dump(params, json_file)

    index += 1
    print(index)
    with open('index.txt', 'w') as file:
        file.write(str(index))
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


async def main():
    options = webdriver.ChromeOptions()
    async with webdriver.Chrome(max_ws_size=2 ** 30, options=options) as driver:
        driver.base_target.socket.on_closed.append(lambda code, reason: print(f"chrome exited"))

        global_conn = driver.base_target
        await global_conn.execute_cdp_cmd("Fetch.enable",
                                          cmd_args={"patterns": [{"requestStage": "Response", "urlPattern": "*"}]}, timeout=100)
        await global_conn.add_cdp_listener("Fetch.requestPaused", lambda data: on_request(data, global_conn))

        await driver.get("https://accounts.o2.co.uk/signin", timeout=60, wait_load=False)
        await asyncio.sleep(5000)

asyncio.run(main())
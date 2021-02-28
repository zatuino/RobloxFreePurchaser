import sys, os, asyncio, json
import robloxapi
import robloxapi.utils
from aiohttp import ClientSession, ContentTypeError
from pathlib import Path

CONFIG_FILE = Path(__file__).absolute().parent / "config.json"
CATALOG_URL = "https://catalog.roblox.com/v1/search/items/details?Category=1&MaxPrice=0&Limit=30&IncludeNotForSale=false&CreatorTargetId=1"



async def get_asset_page(session, next_page_cursor=None):
    global CATALOG_URL

    if next_page_cursor is not None:
        next_page_url = CATALOG_URL + f"&cursor={next_page_cursor}"
    else:
        next_page_url = CATALOG_URL

    while True:
        resp = await session.get(next_page_url)
        if resp.status != 200:
            print(f"Possibly ratelimited, status: {resp.status}... Retrying in 40 seconds...")
            await asyncio.sleep(40)
        else:
            break


    assets = dict()
    asset_data = await resp.json()

    assets["nextPageCursor"] = asset_data["nextPageCursor"]

    for i in asset_data["data"]:
        asset_id = i["id"]
        assets[asset_id] = {
            "productId": i["productId"],
            "expectedSellerId": i["creatorTargetId"],
            "expectedPrice": i["price"]
        }

    return assets




async def get_owned_bundle_ids(user_id, session):
    res = await session.get(f"https://catalog.roblox.com/v1/users/{user_id}/bundles?sortOrder=Asc&limit=100")
    if res.status != 200:
        raise RequestException("Bundles could not be retrieved.")

    json = await res.json()

    ids = set()
    for i in json["data"]:
        ids.add(i["id"])

    return ids




async def buy_limited(roblox, asset_id, data):
    while True:
        try:
            res = await roblox.buy_limited(product_id=data["productId"], expected_price=data["expectedPrice"],
                                           seller_id=data["expectedSellerId"], user_asset_id=asset_id)

        except robloxapi.utils.errors.BadStatus as e:
            print(f"Rate limited when attempting to buy asset {asset_id}... Retrying in 60 secs...")
            await asyncio.sleep(60)
        else:
            print(f"Purchased asset {asset_id}; productId = {data['productId']}")
            break



async def process_page(page, bundles, inventory_url, next_page_cursor, roblox, session):
    for i in page:
        if type(i) == str: continue

        data = page[i]

        try:
            if i in bundles:
                print(f"User already owns bundle {i}")
                continue
            else:
                res = await session.get(inventory_url + str(i))
                if await res.json():
                    print(f"User already owns asset {i}; productId={data['productId']}")
                    continue

        except ContentTypeError as e:
            pass

        await buy_limited(asset_id=i, data=data, roblox=roblox)




async def on_ready():
    session = ClientSession()

    try:
        global CONFIG_FILE
        config = CONFIG_FILE.open()
        roblox = robloxapi.Client(json.load(config)["ROBLOXCOOKIE"], session=session)

    except OSError as e:
        print("Could not read config file.", e)
        await session.close()
        sys.exit(1)

    profile = await roblox.get_self()
    user_id = profile.id

    try:
        bundles = await roblox.get_owned_bundle_ids(user_id)
    except robloxapi.utils.errors.BadStatus as e:
        print(e)
        bundles = {}

    inventory_url = f"https://api.roblox.com/ownership/hasasset?userId={user_id}&assetId="

    page = await get_asset_page(session=session)
    next_page_cursor = page["nextPageCursor"]

    coroutines = list()
    while True:
        coroutines.append(process_page(page, bundles, inventory_url, next_page_cursor, roblox, session))

        page = await get_asset_page(session=session, next_page_cursor=next_page_cursor)
        if page["nextPageCursor"] is None: break
        next_page_cursor = page["nextPageCursor"]


    await asyncio.gather(*coroutines)

    print("Completed!")
    await session.close()




if __name__ == "__main__":
    version = sys.version_info
    if version < (3, 7, 0):
        print("You must have python 3.7 or later to continue.")
        sys.exit(1)

    if os.name == "nt":
        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(on_ready())
        loop.close()
    else:
        asyncio.run(on_ready())


import requests, time, argparse, json
URLS = ["https://api.exchange.coinbase.com/products/BTC-USD/book?level=2", "https://api.gemini.com/v1/book/BTCUSD"]

#Coinbase

#Fetch raw books
#.json() --> The return value for this is a python dictionary
#json.dump() --> Used for serializing a python object into a json formatted string, has two required arguments: 1. The object you want to write. 2. The file you want to write into
#json.load() --> loads the json file into the current python program and turns it into a python object
#json.dumps() --> converts python object into json formatted string
#json.loads() --> you can convert json formatted string data back into python objects
#When you want to write content to a JSON file, you use json.dump().
#json.load() is to load a JSON file into your Python program.
#The argument for the load() function must be either a text file or a binary file. The Python object that you get from json.load() depends on the top-level data type of your JSON file.
cb_response = requests.get(URLS[0])
cb_python_response = cb_response.json() #dictionary of list consisting of multiple lists

#Inspect structure format:
#print(json.dumps(cb_python_response, indent=2)) #structure format --> {bids: [[price, size, num_orders]], asks: [[price, size, num_orders]]} #check this from looking at the API docs from Coinbase

#Parse & Normalize
cb_bids = cb_python_response["bids"] #list of lists
cb_asks = cb_python_response["asks"] #list of lists
def coinbase_parser(bids, asks): #parse bids by descending price, parse asks by ascending price
    parsed_bids = []
    parsed_asks = []
    for i in range(len(bids)):
        bid = [float(bids[i][0]), float(bids[i][1])]
        parsed_bids.append(bid)
    for i in range(len(asks)):
        ask = [float(asks[i][0]), float(asks[i][1])]
        parsed_asks.append(ask)
    parsed_bids.sort(key=lambda x:x[0], reverse=True)
    parsed_asks.sort(key=lambda x:x[0])
    return parsed_bids, parsed_asks
cb_parsed_bids, cb_parsed_asks = coinbase_parser(cb_bids, cb_asks)

#Test to make sure bids are descending on price and asks are ascending
print(cb_parsed_bids[:3])
print(cb_parsed_asks[:3])


#Gemini

#Fetch raw books
gm_response = requests.get(URLS[1])
gm_python_response = gm_response.json() #dictionary of lists of dictionaries

#Acceptance test
assert isinstance(gm_python_response, dict)

#Inspect structure format:
#print(json.dumps(gm_python_response, indent=2)) #structure format --> {bids: [[price, amount, timestamp], asks: [[price, amount, timestamp]]}

#Parse & Normalize
gm_bids = gm_python_response["bids"] #list of dictionaries
gm_asks = gm_python_response["asks"] #list of dictionaries
def gemini_parser(bids, asks): #parse bids by descending price, parse asks by ascending price
    parsed_bids = []
    parsed_asks = []
    for i in range(len(bids)):
        bid = [float(bids[i]["price"]), float(bids[i]["amount"])]
        parsed_bids.append(bid)
    for i in range(len(asks)):
        ask = [float(asks[i]["price"]), float(asks[i]["amount"])]
        parsed_asks.append(ask)
    parsed_bids.sort(key=lambda x:x[0], reverse=True)
    parsed_asks.sort(key=lambda x:x[0])
    return parsed_bids, parsed_asks
gm_parsed_bids, gm_parsed_asks = gemini_parser(gm_bids, gm_asks)

#Merge Books
def merge_bids(cb_bids, gm_bids):
    cb = 0
    gm = 0
    merged = []
    while cb < len(cb_bids) and gm < len(gm_bids):
        #bids sorted by descending price
        if cb_bids[cb][0] >= gm_bids[gm][0]:
            merged.append(cb_bids[cb])
            cb += 1
        else:
            merged.append(gm_bids[gm])
            gm += 1
    if cb < len(cb_bids):
        merged.extend(cb_bids[cb:])
    elif gm < len(gm_bids):
        merged.extend(gm_bids[gm:])
    return merged

merged_bids = merge_bids(cb_parsed_bids, gm_parsed_bids)

def merge_asks(cb_asks, gm_asks):
    cb = 0
    gm = 0
    merged = []
    while cb < len(cb_asks) and gm < len(gm_asks):
        #asks sorted ascending by price
        if cb_asks[cb][0] <= gm_asks[gm][0]:
            merged.append(cb_asks[cb])
            cb += 1
        else:
            merged.append(gm_asks[gm])
            gm += 1
    if cb < len(cb_asks):
        merged.extend(cb_asks[cb:])
    elif gm < len(gm_asks):
        merged.extend(gm_asks[gm:])
    return merged

merged_asks = merge_asks(cb_parsed_asks, gm_parsed_asks)

#Rate limiting without sleep
MIN_INTERVAL = 2.0
cache = {"coinbase": None, "gemini": None}
last_call = {"coinbase": 0.0, "gemini": 0.0}
hits = {"coinbase": 0, "gemini": 0} #testing only

def rate_limiter(name, min_interval=MIN_INTERVAL):
    def decorator(func):
        def wrapper(*args, **kwargs):
            before = last_call[name]
            now = time.monotonic()
            elapsed = now - before
            use_cache = (elapsed < min_interval) #flag to determine whether elapsed time is less than the min_interval of two seconds
            if use_cache and cache[name] is not None:
                return cache[name]
            try:
                ans = func(*args, **kwargs)
            except Exception as e:
                if cache[name] is not None:
                    return cache[name]
                raise #otherwise raise the exception
            cache[name] = ans
            last_call[name] = now
            hits[name] += 1
            return ans
        return wrapper
    return decorator

def fetch_cb_with_timeout():
    response = requests.get(URLS[0], timeout=10)
    return response.json()

def fetch_gm_with_timeout():
    response = requests.get(URLS[1], timeout=10)
    return response.json()

@rate_limiter("coinbase", MIN_INTERVAL)
def fetch_cb():
    return fetch_cb_with_timeout()

@rate_limiter("gemini", MIN_INTERVAL)
def fetch_gm():
    return fetch_gm_with_timeout()

#Testing
fetch_cb()
fetch_gm()
#print(cache["coinbase"], cache["gemini"])
#print(last_call["coinbase"], last_call["gemini"])
#print(hits["coinbase"], hits["gemini"])

time.sleep(MIN_INTERVAL + 0.2)
fetch_cb()
fetch_gm()
#print("hits after cooldown:", net_hits)

#Execution prices

def calc_buy_total(asks, qty):
    remaining = qty
    bought = 0.0
    total_cost = 0.0
    for price, size in asks:
        btc = min(size, remaining) #you cannot buy more than the size of the bitcoin of the current ask, and you can't buy more than the qty remaining
        total_cost += btc * price
        remaining -= btc
        bought += btc
        if remaining <= 0:
            break
    return bought, total_cost

def calc_sell_total(bids, qty):
    remaining = qty
    sold = 0.0
    total_revenue = 0.0
    for price, size in bids:
        btc = min(size, remaining) #you cannot sell more than the size of the bitcoin, and you can't sell more than the qty you have remaining
        total_revenue += btc * price
        remaining -= btc
        sold += btc
        if remaining <= 0:
            break
    return sold, total_revenue

#Testing
total_bought, cost = calc_buy_total(merged_asks, 10)
#print("The price to buy 10 BTC: $", cost)

total_sold, revenue = calc_sell_total(merged_bids, 10)
#print("The price to sell 10 BTC: $", revenue)

#CLI & output

def get_live_books():
    cb_response = fetch_cb()
    gm_response = fetch_gm()
    cb_bids = cb_response["bids"]
    cb_asks = cb_response["asks"]
    gm_bids = gm_response["bids"]
    gm_asks = gm_response["asks"]
    sorted_cb_bids, sorted_cb_asks = coinbase_parser(cb_bids, cb_asks)
    sorted_gm_bids, sorted_gm_asks = gemini_parser(gm_bids, gm_asks)
    live_merged_bids = merge_bids(sorted_cb_bids, sorted_gm_bids)
    live_merged_asks = merge_asks(sorted_cb_asks, sorted_gm_asks)
    return live_merged_bids, live_merged_asks

live_bids, live_asks = get_live_books()

def parse_arguments():
    p = argparse.ArgumentParser() #creates parser object that knows how to read command-line flags
    p.add_argument("--qty", type=float, default=10) #tells to accept a flag named --qty, the type is float, and its default value is 10
    return p.parse_args() #uses built-in method to read CLI arguments

if __name__ == "__main__": #if you run python your_script.py, this block runs, if another file imports your script as a module, this block does not run.
    args = parse_arguments()
    if args.qty <= 0:
        raise SystemExit("Quantity must be greater than 0") #in case quantity is set to 0 or less
    live_bids, live_asks = get_live_books()
    bought, total_cost = calc_buy_total(live_asks, args.qty)
    sold, total_revenue = calc_sell_total(live_bids, args.qty)
    print(f"To buy {args.qty} BTC: ${total_cost:,.2f}")
    print(f"To sell {args.qty} BTC: ${total_revenue:,.2f}")


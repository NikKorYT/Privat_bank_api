import aiohttp
import asyncio
import sys
import datetime
from tqdm.asyncio import tqdm
import json


def get_needed_days():
    """
    Takes days as a parameter when calling a program
    """
    try:
        number_of_days = sys.argv[1]
        number_of_days = int(number_of_days)
        if number_of_days > 10:
            print("Please provide a number of days equal or less than 10.")
            sys.exit()
        elif number_of_days <= 0:
            print("Please provide a number of days greater than 0.")
            sys.exit()
        return number_of_days
    except IndexError:
        print("No argument provided. Please provide the number of days as an argument.")
        sys.exit()
    except ValueError:
        print(
            "Invalid argument. Please provide a valid integer for the number of days."
        )
        sys.exit()


def url_creator(days):
    """
    Creates a list of urls for the exchange rates, based on the number of days provided
    """
    urls = []
    base_url = "https://api.privatbank.ua/p24api/exchange_rates?json&date="
    today = datetime.datetime.now()
    for each_day in range(days):
        current_iterated_date = today - datetime.timedelta(days=each_day)
        formated_date = current_iterated_date.strftime("%d.%m.%Y")
        url = base_url + formated_date
        urls.append(url)
    return urls


async def fetch_exchange_rate(session, url, semaphore):
    async with semaphore:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.text()
                return data
            else:
                print(f"Failed to fetch data: {response.status}")
                return None


async def fetch_exchange_rates(urls, max_concurrent_requests=10):
    semaphore = asyncio.Semaphore(max_concurrent_requests)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_exchange_rate(session, url, semaphore) for url in urls]
        results = []
        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            result = await task
            if result:
                results.append(result)
        return results


def result_parser(result: str) -> list:
    """
    Parsing one result
    Leaves only EURO and USD sale and purchase rates,
    sorts them by date and prints them
    """
    # Unparsed result:
    # {
    # "date": "05.08.2024",
    # "bank": "PB",
    # "baseCurrency": 980,
    # "baseCurrencyLit": "UAH",
    # "exchangeRate": [
    #   {
    #     "baseCurrency": "UAH",
    #     "currency": "USD",
    #     "saleRateNB": 41.2250000,
    #     "purchaseRateNB": 41.2250000,
    #     "saleRate": 41.5000000,
    #     "purchaseRate": 40.9000000,
    #   },
    # {
    #     "baseCurrency": "UAH",
    #     "currency": "EUR",
    #     "saleRateNB": 44.6467000,
    #     "purchaseRateNB": 44.6467000,
    #     "saleRate": 45.2000000,
    #     "purchaseRate": 44.2000000,
    #         },
    #     ],
    # }
    # Parsed result:
    # {
    #     "03.11.2022": {
    #         "EUR": {"sale": 45.2, "purchase": 44.2},
    #         "USD": {"sale": 41.5, "purchase": 40.9},
    #     }
    # }
    parsed_results = {}
    for each_result in result:
        result = json.loads(each_result)
        date = result["date"]
        exchange_rate = result["exchangeRate"]
        parsed_results[date] = {}
        for each_exchange_rate in exchange_rate:
            currency = each_exchange_rate["currency"]
            if currency in ["EUR", "USD"]:
                sale_rate = each_exchange_rate["saleRate"]
                purchase_rate = each_exchange_rate["purchaseRate"]
                parsed_results[date][currency] = {
                    "sale": sale_rate,
                    "purchase": purchase_rate,
                }
    return parsed_results

def print_results(parsed_results):
    print(json.dumps(parsed_results, indent=4))

if __name__ == "__main__":
    urls = url_creator(get_needed_days())
    results = asyncio.run(fetch_exchange_rates(urls))
    parsed_results = result_parser(results)
    print_results(parsed_results)

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


def result_parser(results: list) -> list:
    """
    Leaves only EURO and USD sale and purchase rates,
    sorts them by date and prints them
    """
    parsed_results = {}
    for result in results:  # each result is a dictionary
        result = json.loads(result)
        date = result["date"]
        for currency in result["exchangeRate"]:
            if currency["currency"] == "EUR" or currency["currency"] == "USD":
                parsed_results[date] = {
                    "currency": currency["currency"],
                    "sale": currency["saleRate"],
                    "purchase": currency["purchaseRate"],
                }
    print(parsed_results)


if __name__ == "__main__":
    urls = url_creator(get_needed_days())
    results = asyncio.run(fetch_exchange_rates(urls))
    result_parser(results)

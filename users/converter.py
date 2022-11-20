from datetime import date

import httpx

from config import currency_api_conf


async def currency_converter(currency_from: str, currency_to: str, value: str):
    headers = {"apikey": currency_api_conf.get("apikey")}
    url = f"{currency_api_conf.get('url')}/convert?from={currency_from}&to={currency_to}&amount={value}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()


async def currency_list():
    headers = {"apikey": currency_api_conf.get("apikey")}
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{currency_api_conf.get("url")}/list', headers=headers)
        return response.json()


async def currency_fluctuation(start_date: str, end_date: str, base: str, symbols: str):
    headers = {"apikey": currency_api_conf.get("apikey")}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'{currency_api_conf.get("fluctuation_url")}?'
            f'start_date={start_date}&'
            f'end_date={end_date}&'
            f'base={base}&'
            f'symbols={symbols}',
            headers=headers
        )
        return response.json()

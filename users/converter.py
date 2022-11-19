import httpx
from config import currency_api_conf


async def currency_converter(currency_from, currency_to, value):
    headers = {"apikey": currency_api_conf.get("apikey")}
    url = f"{currency_api_conf.get('url')}?from={currency_from}&to={currency_to}&amount={value}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()


async def currency_list():
    headers = {"apikey": currency_api_conf.get("apikey")}
    async with httpx.AsyncClient() as client:
        response = await client.get(currency_api_conf.get("currency_list_url"), headers=headers)
        return response.json()
import httpx

from config import currency_api_conf


async def currency_converter(currency_from: str, currency_to: str, value: str):
    params = {"from": currency_from, "to": currency_to, "amount": value}
    url = f"{currency_api_conf.get('url')}/convert"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=currency_api_conf.get('headers'), params=params)
        return response.json()


async def currency_list():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'{currency_api_conf.get("url")}/symbols', headers=currency_api_conf.get('headers')
        )
        return response.json()


async def currency_fluctuation(start_date: str, end_date: str, base: str, symbols: str):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "base": base,
        "symbols": symbols
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'{currency_api_conf.get("url")}/fluctuation', headers=currency_api_conf.get('headers'), params=params
        )
        return response.json()

import httpx


async def currency_converter(currency_from, currency_to, value):
    headers = {"apikey": "taPxAI02BK4NITCwpZxqiCy3nDNXdtzs"}
    url = f"https://api.apilayer.com/currency_data/convert?from={currency_from}&to={currency_to}&amount={value}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()

# taPxAI02BK4NITCwpZxqiCy3nDNXdtzs
# taPxAI02BK4NITCwpZxqiCy3nDNXdtzs
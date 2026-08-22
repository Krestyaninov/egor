import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from config import BITRIX_WEBHOOK_URL

logger = logging.getLogger(__name__)

class BitrixClient:
    def __init__(self, webhook_url: str = BITRIX_WEBHOOK_URL):
        self.webhook_url = webhook_url.rstrip("/") + "/"
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={
                "Content-Type": "application/json",
                "User-Agent": "Egor-Analyst-Bot/1.0"
            })
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.webhook_url}{method}.json"
        session = await self.get_session()
        try:
            async with session.post(url, json=params or {}) as resp:
                data = await resp.json()
                if resp.status != 200:
                    logger.error(f"Bitrix API error [{resp.status}] for {method}: {data}")
                return data
        except Exception as e:
            logger.error(f"Network error calling {method}: {e}")
            return {"error": str(e)}

    async def get_deals_by_date(self, start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        deals = []
        start = 0
        filter_dict = {">=DATE_CREATE": start_date}
        if end_date:
            filter_dict["<=DATE_CREATE"] = end_date

        while True:
            res = await self.call("crm.deal.list", {
                "order": {"DATE_CREATE": "DESC"},
                "filter": filter_dict,
                "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "DATE_CREATE", "DATE_MODIFY", "ASSIGNED_BY_ID", "UTM_SOURCE", "UTM_CAMPAIGN"],
                "start": start
            })
            items = res.get("result", [])
            if not items:
                break
            deals.extend(items)
            if "next" in res:
                start = res["next"]
            else:
                break
        return deals

    async def get_deal_products(self, deal_id: int) -> List[Dict[str, Any]]:
        res = await self.call("crm.deal.productrows.get", {"id": deal_id})
        return res.get("result", [])

b24 = BitrixClient()

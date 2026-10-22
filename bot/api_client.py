"""
API client for communicating with backend.
"""
import aiohttp
from typing import Optional, Dict, List, Any
from config import settings


class APIClient:
    """
    Client for backend API requests.
    """
    
    def __init__(self):
        self.base_url = settings.BACKEND_URL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def register_user(self, telegram_id: int, full_name: str, surname: str, region: str) -> Dict:
        """
        Register a new user.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/users/register"
        
        data = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "surname": surname,
            "region": region
        }
        
        async with session.post(url, json=data) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """
        Get user by Telegram ID.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/users/telegram/{telegram_id}"
        
        async with session.get(url) as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            return await response.json()
    
    async def get_test_by_code(self, test_code: str) -> Optional[Dict]:
        """
        Get test by code.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/tests/code/{test_code}"
        
        async with session.get(url) as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            return await response.json()
    
    async def create_session(self, user_id: str, test_id: str) -> Optional[Dict]:
        """
        Create a new test session.
        Returns session dict on success, or {"error": "detail"} on 400.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/sessions/start"
        
        data = {
            "user_id": user_id,
            "test_id": test_id
        }
        
        async with session.post(url, json=data) as response:
            if response.status == 402:
                # Pullik test: balans yetarli emas
                error_data = await response.json()
                return {"error": "PAYMENT_REQUIRED", "payment_required": error_data.get("detail", {})}
            if response.status == 400:
                try:
                    error_data = await response.json()
                    return {"error": error_data.get("detail", "Unknown error")}
                except Exception:
                    return {"error": "Unknown error"}
            response.raise_for_status()
            return await response.json()
    
    async def get_user_results(self, user_id: str) -> List[Dict]:
        """
        Get all results for a user.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/results/user/{user_id}"
        
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_result_by_test_code(self, user_id: str, test_code: str) -> Optional[Dict]:
        """
        Get detailed result for a user by test code.
        Returns None if not found.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/results/user/{user_id}/test-code/{test_code}"
        
        async with session.get(url) as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            return await response.json()
    
    async def update_user(self, telegram_id: int, full_name: str, surname: str, region: str) -> Dict:
        """
        Update existing user info (for re-registration).
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/users/telegram/{telegram_id}"
        
        data = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "surname": surname,
            "region": region
        }
        
        async with session.put(url, json=data) as response:
            response.raise_for_status()
            return await response.json()


    # --- To'lov endpointlari ---

    async def get_payment_info(self) -> Dict:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/v1/payments/info") as response:
            response.raise_for_status()
            return await response.json()

    async def get_balance(self, telegram_id: int) -> Optional[Dict]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/v1/payments/balance/{telegram_id}") as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            return await response.json()

    async def submit_payment(self, telegram_id: int, amount: int, content: bytes, filename: str,
                             content_type: str, test_id: Optional[str] = None) -> Dict:
        """Chekni yuborish. Muvaffaqiyatda {"id": ...}, xatoda {"error": "..."}"""
        session = await self._get_session()
        form = aiohttp.FormData()
        form.add_field("telegram_id", str(telegram_id))
        form.add_field("amount", str(amount))
        if test_id:
            form.add_field("test_id", str(test_id))
        form.add_field("file", content, filename=filename, content_type=content_type)
        async with session.post(f"{self.base_url}/api/v1/payments/submit", data=form) as response:
            if response.status in (400, 404):
                try:
                    data = await response.json()
                    return {"error": data.get("detail", "Xatolik")}
                except Exception:
                    return {"error": "Xatolik"}
            response.raise_for_status()
            return await response.json()


# Global API client instance
api_client = APIClient()

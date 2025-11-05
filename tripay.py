import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional, List
import aiohttp
import config
from database import db

class TripayAPI:
    def __init__(self):
        self.api_key = None
        self.private_key = None
        self.merchant_code = None
        self.base_url = None
        self.mode = None

    async def load_config_from_db(self):
        self.api_key = await db.get_setting("tripay_api_key")
        self.private_key = await db.get_setting("tripay_private_key")
        self.merchant_code = await db.get_setting("tripay_merchant_code")
        self.mode = await db.get_setting("tripay_mode") or "sandbox"
        if self.mode == "production":
            self.base_url = "https://tripay.co.id/api"
        else:
            self.base_url = "https://tripay.co.id/api-sandbox"
        # Validasi field wajib
        if not all([self.api_key, self.private_key, self.merchant_code]):
            raise Exception("Konfigurasi Tripay belum lengkap! Set semua field di /tripayconfig.")

    def _generate_signature(self, method: str, endpoint: str, body: str = "") -> str:
        """Generate signature for Tripay API"""
        string_to_sign = f"{method.upper()}\n{endpoint}\n{body}"
        signature = hmac.new(
            self.private_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def get_payment_channels(self) -> Optional[Dict[str, Any]]:
        """Get available payment channels"""
        try:
            await self.load_config_from_db()
        except Exception as e:
            return {"success": False, "error": str(e)}
        endpoint = "/merchant/payment-channel"
        url = f"{self.base_url}{endpoint}"
        
        signature = self._generate_signature("GET", endpoint)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Signature": signature,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error getting payment channels: {response.status}")
                        return None
        except Exception as e:
            print(f"Exception in get_payment_channels: {e}")
            return None

    async def create_transaction(self, amount: int, user_id: int, order_items: list = None, method: str = "MYBVA") -> Optional[Dict[str, Any]]:
        """Create transaction in Tripay"""
        try:
            await self.load_config_from_db()
        except Exception as e:
            return {"success": False, "error": str(e)}
        if order_items is None:
            order_items = [
                {
                    "sku": "TOPUP",
                    "name": f"Top Up Saldo - {amount}",
                    "price": amount,
                    "quantity": 1,
                    "product_url": "",
                    "image_url": ""
                }
            ]
        
        # Generate unique merchant reference
        merchant_ref = f"TU{user_id}{int(time.time())}"
        
        payload = {
            "method": method,  # Payment method chosen by user
            "merchant_ref": merchant_ref,
            "amount": amount,
            "customer_name": f"User {user_id}",
            "customer_email": f"user{user_id}@telegram.bot",
            "customer_phone": "08123456789",
            "order_items": order_items,
            "return_url": f"{config.WEBHOOK_URL}/payment-return",
            "expired_time": int(time.time()) + (24 * 60 * 60)  # 24 hours
        }
        
        # Generate signature for Tripay (HMAC-SHA256 format)
        signature = hmac.new(
            self.private_key.encode('utf-8'),
            f"{self.merchant_code}{merchant_ref}{amount}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        payload["signature"] = signature
        
        url = f"{self.base_url}/transaction/create"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("success"):
                        print(f"✅ Transaction created successfully: {result['data']['reference']}")
                        return result["data"]
                    else:
                        print(f"❌ Error creating transaction (Status {response.status}): {result}")
                        print(f"   Request payload: {payload}")
                        return None
                        
        except aiohttp.ClientError as e:
            print(f"❌ Network error in create_transaction: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error in create_transaction: {e}")
            return None

    async def get_transaction_detail(self, reference: str) -> Optional[Dict[str, Any]]:
        """Get transaction detail by reference"""
        try:
            await self.load_config_from_db()
        except Exception as e:
            return {"success": False, "error": str(e)}
        endpoint = f"/transaction/detail"
        url = f"{self.base_url}{endpoint}"
        
        signature = self._generate_signature("GET", endpoint)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Signature": signature,
        }
        
        params = {"reference": reference}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            return result["data"]
                    print(f"Error getting transaction detail: {response.status}")
                    return None
        except Exception as e:
            print(f"Exception in get_transaction_detail: {e}")
            return None

    def verify_callback_signature(self, callback_signature: str, raw_body: str) -> bool:
        """Verify callback signature from Tripay"""
        if not self.private_key:
            return False
        expected_signature = hmac.new(
            bytes(self.private_key, 'latin-1'),
            bytes(raw_body, 'latin-1'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(callback_signature, expected_signature)

    async def get_fee_calculator(self, amount: int, method_code: str) -> Optional[Dict[str, Any]]:
        """Calculate fee for specific payment method"""
        try:
            await self.load_config_from_db()
        except Exception as e:
            return {"success": False, "error": str(e)}
        endpoint = f"/merchant/fee-calculator"
        url = f"{self.base_url}{endpoint}"
        
        signature = self._generate_signature("GET", endpoint)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Signature": signature,
        }
        
        params = {
            "amount": amount,
            "code": method_code
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            return result["data"]
                    return None
        except Exception as e:
            print(f"Exception in get_fee_calculator: {e}")
            return None

    async def get_active_payment_channels(self, active_channel_codes: list = None) -> Optional[List[Dict[str, Any]]]:
        """Get active payment channels (filtered by admin settings)"""
        all_channels = await self.get_payment_channels()
        
        if not all_channels or not all_channels.get("success"):
            return None
        
        if "error" in all_channels:
            # Propagate error up
            return all_channels

        channels_data = all_channels.get("data", [])
        
        # If no filter specified, return all
        if not active_channel_codes:
            return channels_data
        
        # Filter only active channels
        filtered_channels = []
        for channel in channels_data:
            if channel.get("code") in active_channel_codes:
                filtered_channels.append(channel)
        
        return filtered_channels

    async def get_channel_info(self, channel_code: str) -> Optional[Dict[str, Any]]:
        """Get specific channel information"""
        all_channels = await self.get_payment_channels()
        
        if not all_channels or not all_channels.get("success"):
            return None
        
        if "error" in all_channels:
            return all_channels

        channels_data = all_channels.get("data", [])
        
        for channel in channels_data:
            if channel.get("code") == channel_code:
                return channel
        
        return None

# Global Tripay API instance
tripay = TripayAPI() 
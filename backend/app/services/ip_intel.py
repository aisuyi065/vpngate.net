from __future__ import annotations

import httpx

from app.models import IpQualityRecord, utcnow_iso


class IpIntelService:
    def __init__(self, provider: str = "ipapi.is", token: str | None = None) -> None:
        self.provider = provider
        self.token = token

    async def lookup(self, ip: str) -> IpQualityRecord:
        if self.provider == "ipinfo" and self.token:
            return await self._lookup_ipinfo(ip)
        return await self._lookup_ipapi_is(ip)

    async def _lookup_ipapi_is(self, ip: str) -> IpQualityRecord:
        params = {"q": ip}
        if self.token:
            params["key"] = self.token
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get("https://api.ipapi.is/", params=params)
            response.raise_for_status()
            data = response.json()
        company = data.get("company", {}) or {}
        asn = data.get("asn", {}) or {}
        quality_class = self._classify(
            is_datacenter=bool(data.get("is_datacenter")),
            is_proxy=bool(data.get("is_proxy")),
            is_vpn=bool(data.get("is_vpn")),
            company_type=(company.get("type") or "").lower(),
            asn_type=(asn.get("type") or "").lower(),
        )
        return IpQualityRecord(
            ip=ip,
            provider="ipapi.is",
            quality_class=quality_class,
            isp=company.get("name"),
            organization=asn.get("org") or company.get("name"),
            company_type=company.get("type"),
            asn_type=asn.get("type"),
            country_code=(data.get("location") or {}).get("country_code"),
            is_datacenter=bool(data.get("is_datacenter")),
            is_proxy=bool(data.get("is_proxy")),
            is_vpn=bool(data.get("is_vpn")),
            is_tor=bool(data.get("is_tor")),
            raw=data,
            updated_at=utcnow_iso(),
        )

    async def _lookup_ipinfo(self, ip: str) -> IpQualityRecord:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(f"https://ipinfo.io/{ip}/json", params={"token": self.token})
            response.raise_for_status()
            data = response.json()
        org = data.get("org", "")
        org_lower = org.lower()
        quality_class = "hosting" if any(token in org_lower for token in ["google", "amazon", "cloud", "hosting"]) else "unknown"
        return IpQualityRecord(
            ip=ip,
            provider="ipinfo",
            quality_class=quality_class,
            organization=org,
            country_code=data.get("country"),
            raw=data,
            updated_at=utcnow_iso(),
        )

    def _classify(self, *, is_datacenter: bool, is_proxy: bool, is_vpn: bool, company_type: str, asn_type: str) -> str:
        if is_datacenter or is_proxy or is_vpn or company_type == "hosting" or asn_type == "hosting":
            return "hosting"
        if company_type == "isp" and asn_type in {"isp", "", "fixed", "broadband"}:
            return "residential"
        return "unknown"

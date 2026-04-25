import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Ingredient(BaseModel):
    name: str
    brand: Optional[str] = None
    perishable: Optional[bool] = None


class Station(BaseModel):
    station_number: str
    ingredient: Optional[Ingredient] = None
    remaining_ml: Optional[float] = None


class DeviceConfig(BaseModel):
    device_number: str
    stations: List[Station]


class DeviceService:
    """
    Service for handling device-specific actions and hardware connection context.
    Device metadata comes from the mobile app in chat requests.
    Enhanced with hardware connection context from defteros-service API.
    """

    def __init__(self):
        # Defteros API URL is provided via environment
        settings = get_settings()
        self.defteros_api_url = settings.defteros_prod_api_url
        self._device_type_patterns = {
            "360": ["BASYS_360", "CHATBOT_360"],
            "coaster": ["CHATBOT_C", "CHATBOT_CA", "CHATBOT_CST2B", "CHATBOT_CST2S"],
        }

    def infer_device_type_from_id(self, device_id: str) -> Optional[str]:
        """
        Infer device type from device ID based on patterns.
        Args: device_id: The device ID to analyze
        Returns: Device type ("360" or "coaster") or None if unknown
        """
        device_id_upper = device_id.upper()

        for device_type, patterns in self._device_type_patterns.items():
            for pattern in patterns:
                if device_id_upper.startswith(pattern):
                    return device_type

        return None

    async def _get_device_info(self, device_number: str) -> Optional[Dict[str, Any]]:
        """
        Get device information from defteros-service API using device_number.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.defteros_api_url}/devices/device-number/{device_number}",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"Device {device_number} not found in defteros-service"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error fetching device info for {device_number}: {e}")
            return None

    def _parse_device_config(
        self, device_number: str, device_info: Dict[str, Any]
    ) -> DeviceConfig:
        """
        Parse device configuration with station information from defteros-service data.
        """
        try:
            config_data = device_info.get("configuration")
            if not config_data or config_data == "null":
                return DeviceConfig(device_number=device_number, stations=[])

            if isinstance(config_data, str):
                import json

                config_data = json.loads(config_data)

            stations_data = config_data.get("stations", {})
            stations = []

            for station_id, station_info in stations_data.items():
                station_number = station_id
                ingredient = None
                ingredient_name = station_info.get("ingredient_name")
                if ingredient_name:
                    ingredient = Ingredient(
                        name=ingredient_name,
                        brand=station_info.get("brand"),
                        perishable=station_info.get("is_perishable"),
                    )

                remaining_ml = None
                quantity_str = station_info.get("quantity")
                if quantity_str:
                    try:
                        quantity_str = (
                            str(quantity_str)
                            .replace("ML", "")
                            .replace("ml", "")
                            .strip()
                        )
                        remaining_ml = float(quantity_str)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Could not parse quantity '{quantity_str}' for station {station_id}"
                        )

                station = Station(
                    station_number=station_number,
                    ingredient=ingredient,
                    remaining_ml=remaining_ml,
                )
                stations.append(station)

            stations.sort(key=lambda x: x.station_number.upper())
            return DeviceConfig(device_number=device_number, stations=stations)

        except Exception as e:
            logger.error(f"Error parsing device configuration for {device_number}: {e}")
            return DeviceConfig(device_number=device_number, stations=[])

    async def get_device_context(
        self, device_metadata: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive device context using device_number from metadata.
        All device information is fetched once from defteros-service.
        """
        device_number = device_metadata.device_number
        device_info = await self._get_device_info(device_number)

        if not device_info:
            return None

        device_config = self._parse_device_config(device_number, device_info)
        device_type = self.infer_device_type_from_id(device_number)

        # Extract category information from raw device_info for each station
        config_data = device_info.get("configuration", {})
        if isinstance(config_data, str):
            config_data = json.loads(config_data)
        stations_data = config_data.get("stations", {}) if config_data else {}

        available_ingredients = []
        empty_stations = []
        low_stock_stations = []

        if device_config:
            for station in device_config.stations:
                if station.ingredient:
                    # Get category info from raw device_info for this station
                    station_info = stations_data.get(station.station_number, {})
                    category_info = station_info.get("category", {})

                    ingredient_data = {
                        "station": station.station_number,
                        "ingredient": station.ingredient.name,
                        "remaining_ml": station.remaining_ml,
                        "perishable": station.ingredient.perishable,
                    }

                    # Add category information if available
                    if category_info:
                        ingredient_data["category_primary"] = category_info.get(
                            "primary"
                        )
                        ingredient_data["secondary_category"] = category_info.get(
                            "secondary"
                        )

                    available_ingredients.append(ingredient_data)
                    if station.remaining_ml and station.remaining_ml < 50:
                        low_stock_stations.append(
                            {
                                "station": station.station_number,
                                "ingredient": station.ingredient.name,
                                "remaining_ml": station.remaining_ml,
                            }
                        )
                else:
                    empty_stations.append(station.station_number)

        context = {
            "device_number": device_number,
            "device_type_id": device_info.get("device_type_id"),
            "device_type": device_type,
            "device_config": device_config.dict() if device_config else None,
            "available_ingredients": available_ingredients,
            "empty_stations": empty_stations,
            "low_stock_stations": low_stock_stations,
        }

        if (
            hasattr(device_metadata, "connection_status")
            and device_metadata.connection_status
        ):
            context["connection_status"] = device_metadata.connection_status

        return context

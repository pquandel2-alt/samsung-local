"""Samsung Tizen media player entity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SamsungLocalConfigEntry
from .entity import SamsungLocalEntity
from .models import Capability, ConnectionStatus, EntityPlatform

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def add(capabilities: list[Capability]) -> None:
        async_add_entities(
            SamsungLocalMediaPlayer(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.MEDIA_PLAYER, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.MEDIA_PLAYER
        ]
    )


class SamsungLocalMediaPlayer(SamsungLocalEntity, MediaPlayerEntity):
    _attr_name = None
    _BASE_FEATURES = (
        MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
    )

    @property
    def available(self) -> bool:
        """Keep confirmed WOL control callable while deep standby is opaque."""
        capability = self.capability
        return super().available or bool(capability and capability.attributes.get("can_power_on"))

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        capability = self.capability
        attributes = capability.attributes if capability else {}
        features = self._BASE_FEATURES
        if attributes.get("can_power_on"):
            features |= MediaPlayerEntityFeature.TURN_ON
        if attributes.get("can_launch_apps"):
            features |= MediaPlayerEntityFeature.PLAY_MEDIA
        return features

    @property
    def state(self) -> MediaPlayerState | None:
        connection = self.coordinator.data.connection
        if connection is ConnectionStatus.CONNECTED:
            return MediaPlayerState.ON
        if connection is ConnectionStatus.STANDBY:
            return MediaPlayerState.OFF
        return None

    @property
    def source_list(self) -> list[str]:
        capability = self.capability
        return list(capability.attributes.get("sources", ())) if capability else []

    async def async_turn_on(self) -> None:
        await self._async_command("power_on")

    async def async_turn_off(self) -> None:
        await self._async_command("power_off")

    async def async_volume_up(self) -> None:
        await self._async_command("volume_up")

    async def async_volume_down(self) -> None:
        await self._async_command("volume_down")

    async def async_mute_volume(self, mute: bool) -> None:
        await self._async_command("mute")

    async def async_media_play(self) -> None:
        await self._async_command("play")

    async def async_media_pause(self) -> None:
        await self._async_command("pause")

    async def async_media_stop(self) -> None:
        await self._async_command("stop")

    async def async_media_next_track(self) -> None:
        await self._async_command("channel_up")

    async def async_media_previous_track(self) -> None:
        await self._async_command("channel_down")

    async def async_select_source(self, source: str) -> None:
        await self._async_command("select_source", value=source)

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        if media_type == MediaType.APP:
            await self._async_command("launch_app", value=media_id, turn_on=True)
            return
        if media_type == MediaType.CHANNEL and media_id.isdigit():
            for digit in media_id:
                await self._async_command("remote_key", value=f"KEY_{digit}")
            await self._async_command("remote_key", value="KEY_ENTER")
            return
        raise HomeAssistantError(
            translation_domain="samsung_local",
            translation_key="unsupported_media_type",
        )

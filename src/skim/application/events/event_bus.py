"""Event bus for event-driven architecture"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from loguru import logger

from skim.domain.models.event import Event, EventType


class EventBus:
    """Central event bus for event-driven architecture

    Manages event publishing and subscription for the trading system.
    Events are processed asynchronously through a queue.
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._handlers: list[Callable] = []
        self._task: asyncio.Task | None = None

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe handler to event type

        Args:
            event_type: Type of event to subscribe to
            handler: Callable to invoke when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to event: {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Remove handler from event type subscription

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler from event: {event_type.value}")

    def add_handler(self, handler: Callable) -> None:
        """Add global handler (e.g., strategy)

        Args:
            handler: Handler to add for all events
        """
        self._handlers.append(handler)
        logger.debug("Added global event handler")

    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers

        Args:
            event: Event to publish
        """
        await self._event_queue.put(event)
        logger.debug(f"Published event: {event}")

    def publish_sync(self, event: Event) -> None:
        """Publish event synchronously (for testing)

        Args:
            event: Event to publish
        """
        self._event_queue.put_nowait(event)
        logger.debug(f"Published event (sync): {event}")

    async def start(self) -> None:
        """Start event processing loop

        Creates a background task that processes events from the queue.
        """
        if self._running:
            logger.warning("Event bus already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop event processing

        Signals the processing loop to stop and waits for completion.
        """
        if not self._running:
            logger.warning("Event bus not running")
            return

        self._running = False

        if self._task:
            await self._event_queue.put(None)
            await self._task
            self._task = None

        logger.info("Event bus stopped")

    async def _process_events(self) -> None:
        """Background task that processes events from the queue"""
        logger.debug("Event processing loop started")

        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=1.0
                )

                if event is None:
                    break

                await self._process_event(event)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(
                    f"Error in event processing loop: {e}", exc_info=True
                )

        logger.debug("Event processing loop stopped")

    async def _process_event(self, event: Event) -> None:
        """Process single event

        Notifies global handlers first, then type-specific handlers.

        Args:
            event: Event to process
        """
        logger.debug(f"Processing event: {event.type.value}")

        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Global handler failed: {e}", exc_info=True)

        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler failed: {e}", exc_info=True)


def create_event(
    type: EventType,
    data: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> Event:
    """Factory function to create an Event

    Args:
        type: Event type
        data: Optional event data
        timestamp: Optional timestamp

    Returns:
        New Event instance
    """
    return Event(type=type, data=data, timestamp=timestamp)

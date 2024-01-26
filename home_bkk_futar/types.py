"""
BKK Futar API Types, see:
https://editor.swagger.io/?url=https://opendata.bkk.hu/docs/futar-openapi.yaml
"""

import datetime as dt
from typing import Any

from pydantic import BaseModel, PositiveInt


class TransitRoute(BaseModel):
    """A transit route, e.g. Tram no. 6, or Bus no. 9"""

    id: str
    shortName: str
    longName: str | None = None
    description: str | None = None
    type: str
    url: str | None = None
    agencyId: str
    bikesAllowed: bool
    style: dict[str, Any]  # TransitRouteStyle
    sortOrder: PositiveInt


class TransitStop(BaseModel):
    """A transit stop, e.g. Császár-Komjádi Uszoda dir South for bus no. 9 and some night buses"""

    id: str
    vertex: str
    lat: float
    lon: float
    name: str
    code: str
    direction: str
    platformCode: str | None = None
    description: str | None = None
    locationType: int
    locationSubType: str | None = None
    parentStationId: str | None = None
    wheelchairBoarding: bool
    routeIds: list[str]
    alertIds: list[str] | None = None
    style: dict[str, Any]  # TransitStopStyle


class TransitTrip(BaseModel):
    """A transit trip, e.g. the tram no. 6 that departs Móricz Zsigmond Körtér at workdays 06:00"""

    id: str
    routeId: str
    shapeId: str
    blockId: str | None = None
    tripHeadsign: str
    tripShortName: str | None = None
    serviceId: str
    directionId: str | None = None  # Not optional according to schema but doesn't always appear
    bikesAllowed: bool
    wheelchairAccessible: bool


class TransitAlert(BaseModel):
    """A transit alert, describing an alert covering certain stops and routes"""

    id: str
    start: dt.datetime
    end: dt.datetime
    timestamp: dt.datetime
    modifiedTime: dt.datetime
    stopIds: list[str]
    routeIds: list[str]
    url: dict[str, Any] | None = None  # TranslatedString
    header: dict[str, Any] | None = None  # TranslatedString
    description: dict[str, Any] | None = None  # TranslatedString
    disableApp: bool | None = None
    startText: dict[str, Any] | None = None  # TranslatedString
    endText: dict[str, Any] | None = None  # TranslatedString
    routes: list[dict[str, Any]]  # TransitAlertRoute


class TransitReferences(BaseModel):
    """Route, stop, trip & alert references"""

    agencies: dict[str, dict]  # TransitAgency
    routes: dict[str, TransitRoute]
    stops: dict[str, TransitStop]
    trips: dict[str, TransitTrip]
    alerts: dict[str, TransitAlert]


class TransitScheduleStopTime(BaseModel):
    """Transit schedule entry at a given stop (trip, arrival, departure)"""

    stopId: str
    stopHeadsign: str
    arrivalTime: dt.datetime | None = None
    departureTime: dt.datetime | None = None
    predictedArrivalTime: dt.datetime | None = None
    predictedDepartureTime: dt.datetime | None = None
    uncertain: bool | None = None
    tripId: str
    serviceDate: str
    wheelchairAccessible: bool | None = None
    mayRequireBooking: bool | None = None


class TransitArrivalsAndDepartures(BaseModel):
    """Arrivals and departures from a given stop"""

    stopId: str
    routeIds: list[str]
    alertIds: list[str]
    nearbyStopIds: list[str]
    stopTimes: list[TransitScheduleStopTime]


class TransitEntryWithReferencesTransitArrivalsAndDepartures(BaseModel):
    """Data model for arrivals-and-departures-for-stop endpoint"""

    limitExceeded: bool
    entry: TransitArrivalsAndDepartures
    references: TransitReferences


class ArrivalsAndDeparturesForStopOTPMethodResponse(BaseModel):
    """Response model for arrivals-and-departures-for-stop endpoint using OTP dialect"""

    currentTime: dt.datetime
    version: PositiveInt
    status: str
    code: int
    text: str
    data: TransitEntryWithReferencesTransitArrivalsAndDepartures

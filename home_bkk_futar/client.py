"""BKK Futar API Client"""

import datetime as dt
import os
from zoneinfo import ZoneInfo
from enum import Enum
from typing import Any, Iterable, Optional, Union

from pydantic import BaseModel, AwareDatetime
from requests import Session

from home_bkk_futar.types import ArrivalsAndDeparturesForStopOTPMethodResponse
from home_bkk_futar.utils import equal_divide, sign_by_stop_from_string

# Stops and corresponding strings to use on the display - comes from secret
SIGN_BY_STOP = sign_by_stop_from_string(os.environ.get("BKK_FUTAR_SIGN_BY_STOP"), "|", ",")
# Don't display stop times that are leaving (have left) earlier than this, compared to machine time
MIN_DEPARTURE_SECONDS: int = -10

# Futar API endpoint settings
BASE_URL: str = "https://futar.bkk.hu/api/query/v1/ws"
ENDPOINT: str = "/otp/api/where/arrivals-and-departures-for-stop"

# Packing it up: these will be the GET request parameters going to BKK Futar
PARAMS: Iterable[tuple[str, Any]] = (
    ("key", os.environ.get("BKK_FUTAR_API_KEY")),
    ("stopId", list(SIGN_BY_STOP.keys())),
    ("minutesBefore", 0),
)

# Configuration only used when printing a `DisplayInfo` object for debugging reasons
STOP_TIME_SEP: str = " | "  # Separate elements of a single stop time using this string
LOCAL_TZ: str = "Europe/Budapest"  # Show the local and server time in this timezone
TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S (UTC%z)"  # Show the local and server time in this format


class Reliability(Enum):
    """
    Allowed reliability values for the departure information of one stop time entry. The official
    application colours the stop times based on these categories:
    - LIVE (green) means the vehicle has already departed the terminus and has its "BKK Futar box"
      up and running, so its position - and the arrival time to our stop - can be determined.
    - SCHEDULED (black) means the vehicle hasn't yet departed or doesn't have a signal, but the
      vehicle should be on the way. We get the scheduled arrival time.
    - UNCERTAIN (orange) is an explicit signal that there is some problem with the vehicle.
    """

    LIVE = "live"  # When `TransitScheduleStopTime.predictedDepartureTime` explicitly exists
    SCHEDULED = "scheduled"  # When only the scheduled departure time exists but not uncertain
    UNCERTAIN = "uncertain"  # When `TransitScheduleStopTime.uncertain` exists and is True


class StopTime(BaseModel):
    """
    Stop Time for one trip at a stop, corresponds to one line on the matrix display. We derive this
    directly from `types.TransitScheduleStopTime`, extracting information we need for the display.
    """

    stop_id: str  # ID of the stop to distinguish multiple stops, e.g. `BKK_F00247`
    route_name: str  # Name of route, corresponds to `TransitRoute.shortName`, e.g. `9`
    headsign: str  # Shows where the trip is heading, e.g. `Óbuda, Bogdáni út`
    departure_time: AwareDatetime  # When will the trip leave the stop
    reliability: Reliability  # How reliable is given time entry

    def __str__(self):
        """Pretty print to a single human-readable row, useful for debugging"""
        departure_seconds = self.get_departure_seconds()
        return (
            SIGN_BY_STOP[self.stop_id].ljust(2)
            + STOP_TIME_SEP
            + self.route_name.ljust(4)
            + STOP_TIME_SEP
            + self.headsign.ljust(35)
            + STOP_TIME_SEP
            + f"{departure_seconds // 60:2d}:{departure_seconds % 60:02d}"
            + STOP_TIME_SEP
            + self.reliability.name.ljust(9)
        )

    def get_departure_seconds(self, now: Optional[AwareDatetime] = None) -> int:
        """In how many seconds (compared to now) will the trip leave the stop"""
        return int(
            (self.departure_time - (now or dt.datetime.now(tz=dt.timezone.utc))).total_seconds()
        )

    def format(self, chars: int) -> str:
        """Format a single stop time item, corresponding to a row on the display, to given chars"""
        departure_seconds = self.get_departure_seconds()
        headsign_chars = chars - 9  # stop sign (2) + route name (4) + departure minutes (3)
        return (
            SIGN_BY_STOP[self.stop_id].ljust(2)
            + self.route_name.ljust(4)
            + self.headsign[: headsign_chars - 1].strip(",").ljust(headsign_chars)
            + ("   " if departure_seconds <= 30 else f"{round(departure_seconds / 60):2d}'")
        )


class DisplayInfo(BaseModel):
    """Central structure, holds all needed stop times to display, plus the current server time"""

    server_time: AwareDatetime
    stop_times: list[StopTime]

    def __str__(self):
        """Pretty print to a structured, table-like output, useful for debugging"""
        return (
            f"Machine: {dt.datetime.now(tz=ZoneInfo(LOCAL_TZ)).strftime(TIME_FORMAT)}\n"
            f"Server: {self.server_time.astimezone(ZoneInfo(LOCAL_TZ)).strftime(TIME_FORMAT)}\n"
            + "=" * (4 * len(STOP_TIME_SEP) + 55)
            + "\n"
            + "\n".join(str(stop_time) for stop_time in self.stop_times)
        )

    @classmethod
    def from_response(
        cls, response: ArrivalsAndDeparturesForStopOTPMethodResponse
    ) -> "DisplayInfo":
        """Transform & filter all needed info for the display from a response object"""
        stop_times = []
        # Loop through mentioned stop times in same order as in response
        for stop_time in response.data.entry.stopTimes:
            # When no scheduled or predicted departure, we cannot do anything (shouldn't happen tho)
            if stop_time.departureTime or stop_time.predictedDepartureTime:

                trip = response.data.references.trips[stop_time.tripId]
                route = response.data.references.routes[trip.routeId]
                no_prediction = stop_time.predictedDepartureTime is None

                stop_times.append(
                    StopTime(
                        stop_id=stop_time.stopId,
                        route_name=route.shortName,
                        headsign=stop_time.stopHeadsign,
                        departure_time=(
                            stop_time.departureTime
                            if no_prediction
                            else stop_time.predictedDepartureTime
                        ),
                        reliability=(
                            Reliability.UNCERTAIN
                            if stop_time.uncertain
                            else (Reliability.SCHEDULED if no_prediction else Reliability.LIVE)
                        ),
                    )
                )
        return cls(server_time=response.currentTime, stop_times=stop_times)

    @classmethod
    def request(
        cls,
        params: Union[dict[str, Any], Iterable[tuple[str, Any]]] = PARAMS,
        session: Optional[Session] = None,
    ) -> "DisplayInfo":
        """Make a new request and derive the `DisplayInfo` object from it"""

        def display_info_from_session(session: Session):
            """Do the request itself inside the session context"""
            response = session.get(BASE_URL + ENDPOINT, params=dict(params))
            response.raise_for_status()
            return DisplayInfo.from_response(
                ArrivalsAndDeparturesForStopOTPMethodResponse(**response.json())
            )

        if not session:
            with Session() as session:
                return display_info_from_session(session)
        return display_info_from_session(session)

    def get_upcoming_stop_times(
        self, min_departure_seconds: int = MIN_DEPARTURE_SECONDS
    ) -> list[StopTime]:
        """Only return those stop times which are not earlier than indicated by minimum seconds"""
        now = dt.datetime.now(tz=dt.timezone.utc)
        return [
            stop_time
            for stop_time in self.stop_times
            if stop_time.get_departure_seconds(now) >= min_departure_seconds
        ]

    def format(self, lines: int, chars: int) -> list[str]:
        """
        Format the first few upcoming stop times using available character height (lines) & width
        (chars), return a list of text rows to display on the matrix.
        """
        # Use equal-divide to determine the number of lines given to each stop
        lines_by_stop = {
            stop_id: stop_lines
            for stop_id, stop_lines in zip(SIGN_BY_STOP, equal_divide(lines, len(SIGN_BY_STOP)))
        }
        # Loop once through stop times and only format if needed
        formats_by_stop = {stop_id: [] for stop_id in SIGN_BY_STOP}
        for stop_time in self.get_upcoming_stop_times():
            if len(formats_by_stop[stop_time.stop_id]) < lines_by_stop[stop_time.stop_id]:
                formats_by_stop[stop_time.stop_id].append(stop_time.format(chars=chars))

        # If we don't have the allotted number of stop times for each stop, append empties
        return sum(
            (
                formats + [""] * (lines_by_stop[stop_id] - len(formats))
                for stop_id, formats in formats_by_stop.items()
            ),
            [],
        )

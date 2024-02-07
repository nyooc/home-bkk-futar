"""BKK Futar API Client"""

import os
from enum import Enum

from pydantic import BaseModel, AwareDatetime
import requests

from home_bkk_futar.types import ArrivalsAndDeparturesForStopOTPMethodResponse
from home_bkk_futar.utils import equal_divide, sign_by_stop_from_string

# Futar API endpoint settings and extra params to include in request (other than API key and stops)
BASE_URL = "https://futar.bkk.hu/api/query/v1/ws"
ENDPOINT = "/otp/api/where/arrivals-and-departures-for-stop"
EXTRA_PARAMS = {"minutesBefore": 0}

# Stops and corresponding strings to use on the display - comes from secret
SIGN_BY_STOP = sign_by_stop_from_string(os.environ.get("BKK_FUTAR_SIGN_BY_STOP"), "|", ",")


class Reliability(Enum):
    """Allowed reliability values for the departure information of one stop time entry"""

    LIVE = "live"  # When `TransitScheduleStopTime.predictedDepartureTime` explicitly exists
    SCHEDULED = "scheduled"  # When only the scheduled departure time exists but not uncertain
    UNCERTAIN = "uncertain"  # When `TransitScheduleStopTime.uncertain` exists and is True


class StopTime(BaseModel):
    """Stop Time for one trip at a stop, corresponds to one line on the matrix display"""

    stop_id: str  # ID of the stop to distinguish multiple stops, e.g. `BKK_F00247`
    route_name: str  # Name of route, corresponds to `TransitRoute.shortName`, e.g. `9`
    headsign: str  # Shows where the trip is heading, e.g. `Óbuda, Bogdáni út`
    departure_seconds: int  # In how many seconds (compared to now) will the trip leave
    reliability: Reliability  # How reliable is given time entry

    def format(self, chars: int) -> str:
        """Format a single stop time item, that is, one row (one arriving vehicle) on the display"""
        headsign_chars = chars - 9  # stop sign (2) + route name (4) + departure minutes (3)
        return (
            SIGN_BY_STOP[self.stop_id].ljust(2)
            + self.route_name.ljust(4)
            + self.headsign[: headsign_chars - 1].strip(",").ljust(headsign_chars)
            + (
                "   "
                if self.departure_seconds <= 30
                else f"{round(self.departure_seconds / 60):2d}'"
            )
        )


class Display(BaseModel):
    """All stop times to display, plus any needed components"""

    current_time: AwareDatetime
    stop_times: list[StopTime]

    @classmethod
    def from_response(cls, response: ArrivalsAndDeparturesForStopOTPMethodResponse) -> "Display":
        """Transform & filter all needed info for the display from a response object"""
        stop_times = []
        # Loop through mentioned stop times in same order as in response
        for stop_time in response.data.entry.stopTimes:
            # When no scheduled or predicted departure, we cannot do anything (shouldn't happen tho)
            if stop_time.departureTime or stop_time.predictedDepartureTime:

                trip = response.data.references.trips[stop_time.tripId]
                route = response.data.references.routes[trip.routeId]
                no_prediction = stop_time.predictedDepartureTime is None
                departure_time = (
                    stop_time.departureTime if no_prediction else stop_time.predictedDepartureTime
                )

                stop_times.append(
                    StopTime(
                        stop_id=stop_time.stopId,
                        route_name=route.shortName,
                        headsign=stop_time.stopHeadsign,
                        departure_seconds=int(
                            (departure_time - response.currentTime).total_seconds()
                        ),
                        reliability=(
                            Reliability.UNCERTAIN
                            if stop_time.uncertain
                            else (Reliability.SCHEDULED if no_prediction else Reliability.LIVE)
                        ),
                    )
                )
        return cls(current_time=response.currentTime, stop_times=stop_times)

    @classmethod
    def request_new(cls) -> "Display":
        """Make a new request and derive the display object from it"""
        params = {
            "key": os.environ["BKK_FUTAR_API_KEY"],
            "stopId": list(SIGN_BY_STOP.keys()),
            **EXTRA_PARAMS,
        }
        response = requests.get(BASE_URL + ENDPOINT, params=params)
        response.raise_for_status()
        return Display.from_response(
            ArrivalsAndDeparturesForStopOTPMethodResponse(**response.json())
        )

    def format(self, lines: int, chars: int) -> list[str]:
        """
        Format the stop times using available character height (lines) & width (chars),
        return a list of rows to display on the matrix.
        """
        # Use equal-divide to determine the number of lines given to each stop
        lines_by_stop = {
            stop_id: stop_lines
            for stop_id, stop_lines in zip(SIGN_BY_STOP, equal_divide(lines, len(SIGN_BY_STOP)))
        }
        # Loop once through stop times and only format if needed
        formats_by_stop = {stop_id: [] for stop_id in SIGN_BY_STOP}
        for stop_time in self.stop_times:
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

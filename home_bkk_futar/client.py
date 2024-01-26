"""BKK Futar API Client"""

from enum import Enum
from pydantic import BaseModel, AwareDatetime

from home_bkk_futar.types import ArrivalsAndDeparturesForStopOTPMethodResponse


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

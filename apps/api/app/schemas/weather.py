from pydantic import BaseModel, Field, model_validator


class City(BaseModel):
    name: str
    state: str
    latitude: float
    longitude: float


class LocationIn(BaseModel):
    city: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _need_a_place(self) -> "LocationIn":
        if self.city is None and (self.latitude is None or self.longitude is None):
            raise ValueError("Give a city, or both latitude and longitude")
        return self


class WeatherStatus(BaseModel):
    enabled: bool  # allowed by settings and licence rules
    free_tier: bool  # True means non-commercial endpoint, no key
    city: str | None
    latitude: float | None
    longitude: float | None
    attribution: str
    note: str | None = None

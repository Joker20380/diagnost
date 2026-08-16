from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    DiagnosticSession,
    Vehicle,
    VehicleConfiguration,
    VehicleIdentityObservation,
)


IDENTITY_FIELDS = {
    "vin",
    "brand",
    "model",
    "generation",
    "year",
    "engine_code",
    "transmission",
    "fuel_type",
    "ecu_hardware",
    "ecu_software",
    "mileage",
    "market",
}


@dataclass(frozen=True)
class ConfirmedVehicleIdentity:
    vehicle: Vehicle
    configuration: VehicleConfiguration


def _optional_int(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value).replace(" ", ""))
    if not match:
        raise ValidationError({field_name: "Enter a valid number."})
    return int(match.group())


@transaction.atomic
def confirm_vehicle_identity(
    *,
    session: DiagnosticSession,
    user,
    submitted_data: dict[str, Any],
) -> ConfirmedVehicleIdentity:
    profile = getattr(user, "userprofile", None)
    technician = getattr(profile, "technician_profile", None) if profile else None
    if (
        technician is None
        or not technician.is_active
        or technician.organization_id != session.organization_id
    ):
        raise PermissionDenied("An active technician in this organization is required.")

    observation = (
        VehicleIdentityObservation.objects.select_for_update()
        .select_related("session")
        .get(session=session)
    )
    if observation.status == VehicleIdentityObservation.Status.CONFIRMED:
        if session.vehicle_id and session.vehicle_configuration_id:
            return ConfirmedVehicleIdentity(
                session.vehicle, session.vehicle_configuration
            )
        raise ValidationError("Confirmed identity is incomplete.")

    cleaned = {
        key: (str(value).strip() if value is not None else "")
        for key, value in submitted_data.items()
        if key in IDENTITY_FIELDS
    }
    effective = {**observation.original_data, **cleaned}
    vin = effective.get("vin", "")
    vin_normalized = re.sub(r"[^A-Z0-9]", "", vin.upper())
    if not vin_normalized:
        raise ValidationError({"vin": "VIN is required."})

    year = _optional_int(effective.get("year"), "year")
    mileage_km = _optional_int(effective.get("mileage"), "mileage")
    vehicle, _ = Vehicle.objects.update_or_create(
        organization=session.organization,
        vin_normalized=vin_normalized,
        defaults={
            "vin": vin,
            "make": effective.get("brand", ""),
            "model": effective.get("model", ""),
            "generation": effective.get("generation", ""),
            "year": year,
        },
    )
    vehicle.configurations.filter(is_current=True).update(is_current=False)
    configuration = VehicleConfiguration.objects.create(
        vehicle=vehicle,
        engine_code=effective.get("engine_code", ""),
        transmission=effective.get("transmission", ""),
        fuel_type=effective.get("fuel_type", ""),
        ecu_hardware=effective.get("ecu_hardware", ""),
        ecu_software=effective.get("ecu_software", ""),
        mileage_km=mileage_km,
        market=effective.get("market", ""),
        confirmed_by=profile,
    )

    original = observation.original_data or {}
    observation.corrections = {
        key: value
        for key, value in cleaned.items()
        if str(original.get(key, "")).strip() != str(value).strip()
    }
    observation.status = VehicleIdentityObservation.Status.CONFIRMED
    observation.confirmed_by = profile
    observation.confirmed_at = timezone.now()
    observation.save(
        update_fields=["corrections", "status", "confirmed_by", "confirmed_at"]
    )

    session.vehicle = vehicle
    session.vehicle_configuration = configuration
    session.vin = vehicle.vin
    session.vehicle_model = " ".join(
        part for part in [vehicle.make, vehicle.model] if part
    )
    session.save(
        update_fields=["vehicle", "vehicle_configuration", "vin", "vehicle_model"]
    )
    return ConfirmedVehicleIdentity(vehicle, configuration)

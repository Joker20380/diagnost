from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .analysis_gate import sync_session_analysis_gate
from .models import (
    DiagnosticCase,
    DiagnosticSession,
    Vehicle,
    VehicleBrand,
    VehicleModel,
    VehicleConfiguration,
    VehicleIdentityObservation,
)


IDENTITY_FIELDS = {
    "vin",
    "brand",
    "model",
    "generation",
    "variant",
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


@dataclass(frozen=True)
class VehicleCompletenessAssessment:
    status: str
    missing_fields: list[str]
    review_reasons: list[str]


def assess_vehicle_completeness(
    effective: dict[str, Any],
) -> VehicleCompletenessAssessment:
    missing_fields = [
        field
        for field in ("brand", "model", "year", "engine_code")
        if not effective.get(field)
    ]
    if not (effective.get("variant") or effective.get("generation")):
        missing_fields.append("variant_or_generation")

    vin = re.sub(r"[^A-Z0-9]", "", str(effective.get("vin", "")).upper())
    review_reasons = []
    if len(vin) != 17 or re.search(r"[IOQ]", vin):
        review_reasons.append("vin_format_requires_review")

    if review_reasons:
        status = VehicleConfiguration.CompletenessStatus.NEEDS_REVIEW
    elif missing_fields:
        status = VehicleConfiguration.CompletenessStatus.INCOMPLETE
    else:
        status = VehicleConfiguration.CompletenessStatus.COMPLETE
    return VehicleCompletenessAssessment(status, missing_fields, review_reasons)


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
    make_name = effective.get("brand", "").strip()
    model_name = effective.get("model", "").strip()
    brand = None
    vehicle_model = None
    if make_name:
        brand = VehicleBrand.objects.filter(name__iexact=make_name).first()
        if brand is None:
            brand = VehicleBrand.objects.create(
                name=make_name, slug=slugify(make_name) or "brand"
            )
        if model_name:
            vehicle_model = VehicleModel.objects.filter(
                brand=brand, name__iexact=model_name
            ).first()
            if vehicle_model is None:
                base_slug = slugify(model_name) or "model"
                model_slug = base_slug
                suffix = 2
                while VehicleModel.objects.filter(brand=brand, slug=model_slug).exists():
                    model_slug = f"{base_slug}-{suffix}"
                    suffix += 1
                vehicle_model = VehicleModel.objects.create(
                    brand=brand, name=model_name, slug=model_slug
                )
    vehicle, _ = Vehicle.objects.update_or_create(
        organization=session.organization,
        vin_normalized=vin_normalized,
        defaults={
            "vin": vin,
            "variant": effective.get("variant", ""),
            "brand": brand,
            "vehicle_model": vehicle_model,
            "make": make_name,
            "model": model_name,
            "generation": effective.get("generation", ""),
            "year": year,
        },
    )
    vehicle.configurations.filter(is_current=True).update(is_current=False)
    completeness = assess_vehicle_completeness(effective)
    configuration = VehicleConfiguration.objects.create(
        vehicle=vehicle,
        engine_code=effective.get("engine_code", ""),
        transmission=effective.get("transmission", ""),
        fuel_type=effective.get("fuel_type", ""),
        ecu_hardware=effective.get("ecu_hardware", ""),
        completeness_status=completeness.status,
        missing_fields=completeness.missing_fields,
        review_reasons=completeness.review_reasons,
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
    case = getattr(session, "diagnostic_case", None)
    if (
        case
        and case.status == DiagnosticCase.Status.IDENTITY_PENDING
        and case.intake_complete
        and configuration.completeness_status
        != VehicleConfiguration.CompletenessStatus.NEEDS_REVIEW
    ):
        case.status = DiagnosticCase.Status.READY
        case.save(update_fields=["status", "updated_at"])

    session.vehicle = vehicle
    session.vehicle_configuration = configuration
    session.vin = vehicle.vin
    session.vehicle_model = " ".join(
        part for part in [vehicle.make, vehicle.model] if part
    )
    session.save(
        update_fields=["vehicle", "vehicle_configuration", "vin", "vehicle_model"]
    )
    sync_session_analysis_gate(session)
    return ConfirmedVehicleIdentity(vehicle, configuration)

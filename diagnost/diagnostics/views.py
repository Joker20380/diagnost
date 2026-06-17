from django.shortcuts import render

# Create your views here.

# --- DTC / OBD reference views ---

def dtc_search(request):
    from django.shortcuts import render
    from diagnostics.models import DTCReference

    query = (request.GET.get("q") or "").strip().upper()
    results = []

    if query:
        results = (
            DTCReference.objects
            .filter(is_active=True)
            .filter(code__icontains=query)
            .order_by("code", "manufacturer")[:50]
        )

    return render(request, "diagnost/dtc_search.html", {
        "query": query,
        "results": results,
    })


def dtc_detail(request, code):
    from django.shortcuts import get_object_or_404, render
    from diagnostics.models import DTCReference

    code = (code or "").strip().upper()

    ref = get_object_or_404(
        DTCReference,
        code=code,
        manufacturer="",
        is_active=True,
    )

    related = (
        DTCReference.objects
        .filter(code=code, is_active=True)
        .exclude(id=ref.id)
        .order_by("manufacturer")
    )

    return render(request, "diagnost/dtc_detail.html", {
        "ref": ref,
        "related": related,
    })


def dtc_api_detail(request, code):
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from diagnostics.models import DTCReference

    code = (code or "").strip().upper()

    ref = get_object_or_404(
        DTCReference,
        code=code,
        manufacturer="",
        is_active=True,
    )

    return JsonResponse({
        "code": ref.code,
        "system": ref.system,
        "scope": ref.scope,
        "manufacturer": ref.manufacturer,
        "title_ru": ref.title_ru,
        "title_en": ref.title_en,
        "description_ru": ref.description_ru,
        "description_en": ref.description_en,
        "symptoms": ref.symptoms,
        "possible_causes": ref.possible_causes,
        "diagnostic_notes": ref.diagnostic_notes,
        "recommended_checks": ref.recommended_checks,
        "severity": ref.severity,
        "source_name": ref.source_name,
        "source_url": ref.source_url,
    }, json_dumps_params={"ensure_ascii": False, "indent": 2})

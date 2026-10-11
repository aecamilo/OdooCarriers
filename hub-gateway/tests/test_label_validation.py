from app.services.label_service import validate_label_payload


def _valid_payload():
    return {
        "schema_version": "1.0",
        "operation": "create_shipment",
        "carrier_code": "ctt",
        "reference": "SO001",
        "shipper": {"country_code": "PT", "postal_code": "1000-001", "city": "Lisboa"},
        "recipient": {"country_code": "PT", "postal_code": "4000-001", "city": "Porto"},
        "parcels": [{"weight_kg": 1.5}],
    }


def test_valid_payload_accepted():
    req, err = validate_label_payload(_valid_payload())
    assert err == ""
    assert req is not None
    assert req.carrier_code == "ctt"


def test_empty_payload_rejected():
    req, err = validate_label_payload({})
    assert req is None
    assert err == "invalid_payload"


def test_wrong_schema_version_rejected():
    data = _valid_payload()
    data["schema_version"] = "2.0"
    req, err = validate_label_payload(data)
    assert req is None
    assert err == "invalid_payload"


def test_zero_weight_rejected():
    data = _valid_payload()
    data["parcels"] = [{"weight_kg": 0}]
    req, err = validate_label_payload(data)
    assert req is None
    assert err == "invalid_payload"

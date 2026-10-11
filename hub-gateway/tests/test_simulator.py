import base64

from app.adapters.simulator import simulate_label


def test_simulate_label_returns_pdf_base64():
    tracking, label_b64, carrier_ref = simulate_label("ctt")
    assert tracking.startswith("SIM-")
    assert carrier_ref.startswith("REF-")
    raw = base64.b64decode(label_b64)
    assert raw.startswith(b"%PDF")

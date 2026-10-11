import base64
import uuid


def simulate_label(carrier_code: str) -> tuple[str, str, str]:
    tracking = f"SIM-{uuid.uuid4().hex[:12].upper()}"
    carrier_ref = f"REF-{uuid.uuid4().hex[:8]}"
    # Minimal valid PDF
    pdf = (
        b"%PDF-1.4\n1 0 obj<<>>endobj\n"
        b"trailer<<>>\n%%EOF"
    )
    label_b64 = base64.b64encode(pdf).decode("ascii")
    return tracking, label_b64, carrier_ref

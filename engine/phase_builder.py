import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/phase-converter-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8").strip()
CUSTOM_PHASE = os.environ.get("CUSTOM_PHASE", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_converters.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Machine / Converter Model Name, 3-Phase Motor HP, 3-Phase FLA Amps @ 230V, Torque Class, Upsized VFD HP, Rotary RPC HP)
SEED_CONVERTERS = [
    ("Bridgeport Series I 2 HP 3-Phase Milling Machine VFD Setup", 2.0, 6.8, "Variable / Spindle", 3.0, 5.0),
    ("Bridgeport 1.5 HP J-Head 3-Phase Mill on 240V Single-Phase", 1.5, 5.2, "Variable / Spindle", 3.0, 3.0),
    ("South Bend / Clausing 3 HP 3-Phase Metal Lathe VFD Setup", 3.0, 9.6, "High-Inertia Lathe", 5.0, 7.5),
    ("5 HP 3-Phase 80-Gallon Shop Air Compressor on Single-Phase", 5.0, 15.2, "Hard-Start Compressor", 10.0, 10.0),
    ("7.5 HP 3-Phase 80/120-Gallon Air Compressor Phase Converter", 7.5, 22.0, "Hard-Start Compressor", 15.0, 15.0),
    ("10 HP 3-Phase Industrial Air Compressor Rotary Converter", 10.0, 28.0, "Hard-Start Compressor", 20.0, 20.0),
    ("5 HP 3-Phase Cabinet Table Saw (Powermatic / Oliver) Setup", 5.0, 15.2, "High-Inertia Saw", 7.5, 10.0),
    ("7.5 HP 3-Phase Industrial Planer & Moulding Machine Setup", 7.5, 22.0, "High-Inertia Wood", 15.0, 15.0),
    ("3 HP 3-Phase Cyclone Dust Collector & Bandsaw VFD Setup", 3.0, 9.6, "Centrifugal / Saw", 5.0, 5.0),
    ("American Rotary AR10 (10 HP) Digital Rotary Phase Converter", 5.0, 15.2, "Hard-Start / Multi-Tool", 10.0, 10.0),
    ("American Rotary AR15 (15 HP) Heavy-Duty Phase Converter", 7.5, 22.0, "Hard-Start / CNC", 15.0, 15.0),
    ("American Rotary AD10 & AD20 Smart CNC Rotary Converter", 10.0, 28.0, "CNC / Multi-Load", 20.0, 20.0),
    ("Phoenix Phase Converters GP10 (10 HP) & GP15 (15 HP) RPC", 5.0, 15.2, "Hard-Start / Shop", 10.0, 10.0),
    ("Phase-A-Matic PAM-600 & R-10 Rotary/Static Phase Converter", 5.0, 15.2, "Medium-Duty Shop", 10.0, 10.0),
    ("Teco Westinghouse L510 & E510 (3 HP / 5 HP) 230V VFD", 3.0, 9.6, "Industrial VFD", 5.0, 7.5),
    ("Fuji Electric Frenic-Mini & Frenic-Ace 5 HP / 7.5 HP VFD", 5.0, 15.2, "Heavy-Duty VFD", 10.0, 10.0),
    ("Hitachi WJ200-022SF (3 HP Single-Phase Input) Sensorless VFD", 3.0, 9.6, "Constant Torque VFD", 3.0, 5.0),
    ("Yaskawa V1000 & GA500 Single-to-3-Phase VFD Sizing", 5.0, 15.2, "Constant Torque VFD", 10.0, 10.0),
    ("AutomationDirect GS20 /DURApulse 5 HP & 10 HP VFD", 5.0, 15.2, "Heavy-Duty VFD", 10.0, 10.0),
    ("Huanyang / Vevor 2.2kW (3 HP) & 4kW (5.5 HP) CNC Spindle VFD", 3.0, 9.6, "High-Speed Spindle", 5.0, 5.0),
    ("Huanyang / Vevor 5.5kW (7.5 HP) & 7.5kW (10 HP) 240V VFD", 5.0, 15.2, "Single-to-3-Phase VFD", 7.5, 10.0),
    ("KB Electronics KBAC-27D & KBAC-29 (2 HP / 3 HP NEMA-4X VFD)", 2.0, 6.8, "Washdown Belt Grinder", 3.0, 5.0),
    ("2x72 Knife Maker Belt Grinder (2 HP / 3 HP 3-Phase + VFD)", 2.0, 6.8, "Variable Speed Grinder", 3.0, 5.0),
    ("Surface Grinder & Cylindrical Grinder 3 HP 3-Phase Setup", 3.0, 9.6, "Precision Balanced", 5.0, 7.5),
    ("2-Post Automotive Lift 3 HP 3-Phase Hydraulic Motor Conversion", 3.0, 9.6, "High-Torque Hydraulic", 5.0, 7.5),
    ("5 HP 3-Phase Submersible Deep Well & Irrigation Pump VFD", 5.0, 15.2, "Submersible Pump", 7.5, 10.0),
    ("10 HP 3-Phase Grain Dryer Fan & Farm Auger Phase Converter", 10.0, 28.0, "High-Inertia Agricultural", 20.0, 20.0),
    ("15 HP 3-Phase Wide-Belt Drum Sander & Sawmill Converter", 15.0, 42.0, "Extreme-Duty Sawmill", 30.0, 30.0),
    ("230V to 460V 3-Phase Step-Up Transformer + RPC/VFD Setup", 7.5, 22.0, "460V 3-Phase Machine", 15.0, 15.0),
    ("VFD Dynamic Braking Resistor Ohms & Wattage Sizing Guide", 5.0, 15.2, "High-Inertia Braking", 10.0, 10.0)
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=5.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_phase_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial 3-Phase Machine × Motor HP Permutator.
    """
    discovered = []
    seeds = [
        "what size phase converter for ",
        "what size vfd for ",
        "single phase to 3 phase vfd ",
        "american rotary phase converter "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        hp_m = re.search(r"\b(1\.5|2|3|5|7\.5|10|15|20)\s*hp\b", cleaned)
                        hp_v = float(hp_m.group(1)) if hp_m else 5.0
                        fla_v = round(hp_v * 3.0, 1)
                        discovered.append((cleaned.title(), hp_v, fla_v, "Heavy-Duty 3-Phase", hp_v * 2.0, hp_v * 2.0))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    hp_tiers = [
        (1.0, 3.6),
        (1.5, 5.2),
        (2.0, 6.8),
        (3.0, 9.6),
        (5.0, 15.2),
        (7.5, 22.0),
        (10.0, 28.0),
        (15.0, 42.0)
    ]
    machines = [
        ("3-Phase Air Compressor", "Hard-Start Compressor", 2.0),
        ("3-Phase Metal Lathe", "High-Inertia Lathe", 1.75),
        ("3-Phase Milling Machine", "Variable Spindle", 1.75),
        ("3-Phase Cabinet Table Saw", "High-Inertia Saw", 1.75),
        ("3-Phase Hydraulic Power Pack", "High-Torque Pump", 2.0),
        ("3-Phase CNC Router Spindle", "High-Frequency Spindle", 1.5)
    ]
    for m_hp, m_fla in hp_tiers:
        for mach_name, t_class, mult in machines:
            combo_title = f"{m_hp:g} HP {mach_name} on 240V Single-Phase"
            test_slug = slugify(f"{combo_title}-vfd-rpc-calculator")
            if test_slug not in published_slugs:
                up_vfd = round(m_hp * mult, 1)
                up_rpc = round(m_hp * 2.0, 1)
                discovered.append((combo_title, m_hp, m_fla, t_class, up_vfd, up_rpc))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_phase_data(phase_tuple):
    """
    LAPIS 3: Mesin Fisika NEC Article 430, Diode-Bridge VFD Derating & Braking Resistor (100% Bebas Gagal).
    """
    model_name, motor_hp, fla_3ph, torque_class, upsized_vfd_hp, rpc_idler_hp = phase_tuple

    # 1. Arus Input 1-Fasa 240V (Single-Phase Input Current = 3-Phase FLA * sqrt(3) / Eff ~ 1.85x):
    input_1ph_amps = round(fla_3ph * 1.85, 1)

    # 2. Ukuran Minimum Output Amps VFD (1.732x - 2.0x derating ketika VFD 3-fasa disuplai listrik 1-fasa):
    min_vfd_rated_amps = round(fla_3ph * 1.85, 1)
    kw_rating = round(upsized_vfd_hp * 0.75, 1)

    # 3. NEC Article 430.122 Single-Phase Input Breaker (125% - 150% dari Input Amps) & Copper Wire Gauge:
    raw_breaker = input_1ph_amps * 1.35
    if raw_breaker <= 15:
        breaker_amps = 15
        wire_awg = "14 AWG THHN / 14/2 NM-B Copper"
    elif raw_breaker <= 20:
        breaker_amps = 20
        wire_awg = "12 AWG THHN / 12/2 NM-B Copper"
    elif raw_breaker <= 30:
        breaker_amps = 30
        wire_awg = "10 AWG THHN / 10/2 NM-B Copper"
    elif raw_breaker <= 40:
        breaker_amps = 40
        wire_awg = "8 AWG THHN / 8/2 NM-B Copper"
    elif raw_breaker <= 50:
        breaker_amps = 50
        wire_awg = "6 AWG THHN / 6/2 NM-B Copper"
    elif raw_breaker <= 70:
        breaker_amps = 70
        wire_awg = "4 AWG THHN Copper in Conduit"
    else:
        breaker_amps = 100
        wire_awg = "2 AWG THHN Copper in Conduit"

    # 4. Perhitungan Dynamic Braking Resistor (untuk DC Bus 380V–400V pada VFD 240V):
    # Peak Braking Current I_brake ~ Motor_HP * 2.5A; Resistance R = 380V / I_brake; Power = 150W per Motor HP
    brake_ohms = max(20, int(round(380.0 / max(2.5, motor_hp * 2.6), -1)))
    brake_watts = max(300, int(round(motor_hp * 160.0, -2)))

    return {
        "converter_name": model_name,
        "torque_class": torque_class,
        "seo_title": f"{model_name} VFD Derating, Rotary Phase Converter & Wire Calculator (2026)",
        "meta_description": f"Calculate exact single-to-3-phase VFD upsizing ({upsized_vfd_hp:g} HP / {min_vfd_rated_amps}A), Rotary Phase Converter size ({rpc_idler_hp:g} HP), 240V 1-phase breaker ({breaker_amps}A / {wire_awg}), and {brake_ohms}Ω {brake_watts}W braking resistor for {model_name}.",
        "specs": {
            "motor_hp_3ph": motor_hp,
            "motor_fla_3ph_amps": fla_3ph,
            "single_phase_input_amps": input_1ph_amps,
            "upsized_vfd_hp": upsized_vfd_hp,
            "upsized_vfd_kw": kw_rating,
            "min_vfd_output_amps": min_vfd_rated_amps,
            "rotary_rpc_idler_hp": rpc_idler_hp,
            "input_breaker_240v_amps": breaker_amps,
            "recommended_wire_awg": wire_awg,
            "braking_resistor_ohms": brake_ohms,
            "braking_resistor_watts": brake_watts,
            "torque_class": torque_class
        },
        "nec_verdict": f"Running a {motor_hp:g} HP 230V 3-phase motor ({fla_3ph}A 3-phase FLA, {torque_class}) on residential 240V single-phase power draws {input_1ph_amps} Amps on the single-phase supply legs ($I_{{1\\phi}} = I_{{3\\phi}} \\times \\sqrt{{3}} \\div \\eta$). Because feeding single-phase 240V into a 3-phase VFD routes all current through just 4 of the 6 input rectifier diodes and doubles DC bus capacitor ripple, you MUST derate the VFD by 50%—selecting a {upsized_vfd_hp:g} HP ({kw_rating} kW, {min_vfd_rated_amps}A+ rated) VFD, or a {rpc_idler_hp:g} HP Digital Rotary Phase Converter. Wire the 240V single-phase input with a {breaker_amps}-Amp 2-pole breaker and {wire_awg}, paired with a {brake_ohms} $\\Omega$ / {brake_watts}W Dynamic Braking Resistor.",
        "hardware_bundle": [
            {
                "badge": f"{upsized_vfd_hp:g} HP ({kw_rating} kW) VFD",
                "title": f"{upsized_vfd_hp:g} HP ({kw_rating} kW / {min_vfd_rated_amps:.0f}A+) Single-Phase 240V Input to 3-Phase 230V Output VFD",
                "price_range": "$139 - $689",
                "amazon_query": f"{upsized_vfd_hp:g} HP {kw_rating}kW 220V Single to 3 Phase VFD Variable Frequency Drive",
                "ph_note": f"Oversized diode bridge and DC bus capacitors safely handle {input_1ph_amps}A single-phase input without tripping under {motor_hp:g} HP load."
            },
            {
                "badge": f"{rpc_idler_hp:g} HP Rotary Converter",
                "title": f"{rpc_idler_hp:g} HP Digital Rotary Phase Converter (American Rotary / Phoenix True 3-Phase Generator)",
                "price_range": "$489 - $1,699",
                "amazon_query": f"{rpc_idler_hp:g} HP Rotary Phase Converter 240V Single to 3 Phase American Rotary",
                "ph_note": f"Generates balanced <3% voltage-imbalance sine-wave 3-phase power ideal for hard-starting air compressors and multi-motor shops."
            },
            {
                "badge": f"{brake_ohms}Ω {brake_watts}W Brake Resistor",
                "title": f"{brake_watts}W {brake_ohms} Ohm Aluminum-Housed Wirewound VFD Dynamic Braking Resistor",
                "price_range": "$29 - $89",
                "amazon_query": f"{brake_watts}W {brake_ohms} Ohm Aluminum Braking Resistor VFD",
                "ph_note": "Dissipates regenerative kinetic energy during rapid spindle/saw deceleration so the VFD never faults on DC Bus Overvoltage (OV)."
            },
            {
                "badge": f"{breaker_amps}A Breaker & Enclosure",
                "title": f"240V {breaker_amps}A 2-Pole Circuit Breaker + Ventilated NEMA-12 Steel VFD Enclosure w/ Filter Fan",
                "price_range": "$69 - $189",
                "amazon_query": f"NEMA Enclosure Fan Filter VFD {breaker_amps}A 2 Pole Breaker",
                "ph_note": "Shields VFD circuit boards from conductive metal swarf and explosive wood dust while maintaining cooling airflow."
            }
        ],
        "machinist_checklist": [
            f"Never wire any magnetic starter, drum switch, or contactor BETWEEN a VFD's 3-phase output (U/V/W) and the {motor_hp:g} HP motor! Opening a switch under load while a VFD is outputting PWM power instantly destroys the IGBT transistor module. Wire all start/stop/reverse toggle switches to the VFD's low-voltage control terminals.",
            f"Apply the $\\sqrt{{3}}$ (1.732x to 2.0x) Single-Phase Derating Rule: a {motor_hp:g} HP motor ({fla_3ph}A 3-phase) draws {input_1ph_amps}A from a 240V single-phase line—so use at least a {upsized_vfd_hp:g} HP ({min_vfd_rated_amps}A+) VFD.",
            "Choose a Rotary Phase Converter (RPC) instead of a VFD if your machine has single-phase 240V control transformers, coolant pumps, power feeds, or PLC electronics wired off the main disconnect, or if you want to run multiple 3-phase machines from one panel.",
            f"Connect a {brake_ohms} $\\Omega$ / {brake_watts}W aluminum-clad braking resistor to the VFD's P+ and DB (PB) terminals and program deceleration ramp time to 2.5–4.0 seconds for lathes, mills, and saws."
        ],
        "faqs": [
            {
                "q": f"Why do I need a {upsized_vfd_hp:g} HP VFD to run a {motor_hp:g} HP 3-phase motor on single-phase 240V?",
                "a": f"When a standard 3-phase VFD is fed by 240V single-phase power (connected to L1 and L2), input current increases by $\\sqrt{{3}}$ (1.732x)—rising from {fla_3ph}A to {input_1ph_amps}A—while flowing through only 4 of the 6 input rectifier diodes. Upsizing to a {upsized_vfd_hp:g} HP ({kw_rating} kW) VFD prevents diode overheating and DC bus undervoltage faults."
            },
            {
                "q": f"Should I use a VFD or a {rpc_idler_hp:g} HP Rotary Phase Converter for {model_name}?",
                "a": f"Use a VFD ({upsized_vfd_hp:g} HP) if you want dial-controlled variable spindle RPM, soft-start acceleration, and electronic dynamic braking on a single motor. Use a {rpc_idler_hp:g} HP Rotary Phase Converter if you are powering a high-inrush reciprocating air compressor, a machine with complex 3-phase transformers/coolant pumps, or multiple 3-phase tools simultaneously."
            },
            {
                "q": f"What size 240V breaker and wire do I need for {model_name}?",
                "a": f"Drawing {input_1ph_amps} Amps on the 240V single-phase input legs, NEC Article 430.122 (125%–135% input rating) requires a dedicated {breaker_amps}-Amp 2-pole circuit breaker wired with {wire_awg}."
            }
        ]
    }


def generate_phase_data(phase_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_phase_data(phase_tuple)

    model_name, motor_hp, fla_3ph, torque_class, upsized_vfd_hp, rpc_idler_hp = phase_tuple
    det_fallback = build_deterministic_phase_data(phase_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Senior Industrial Control Systems Electrical Engineer (NEC Article 430 Specialist) & Master Machinist. Create an accurate 2026 single-to-3-phase VFD derating, Rotary Phase Converter (RPC) idler sizing, 240V breaker/wire gauge, and dynamic braking resistor guide for: "{model_name}".
Baseline specs: 3-Phase Motor={motor_hp} HP ({fla_3ph}A @ 230V, {torque_class}), 240V Single-Phase Input Draw={sp['single_phase_input_amps']}A, Upsized VFD={upsized_vfd_hp} HP ({sp['upsized_vfd_kw']} kW / {sp['min_vfd_output_amps']}A+), Rotary Phase Converter={rpc_idler_hp} HP, 240V Breaker={sp['input_breaker_240v_amps']}A ({sp['recommended_wire_awg']}), Braking Resistor={sp['braking_resistor_ohms']} Ohms / {sp['braking_resistor_watts']}W.
Return ONLY a valid JSON object matching this exact schema:
{{
  "converter_name": "{model_name}",
  "torque_class": "{torque_class}",
  "seo_title": "{model_name} VFD Derating, Rotary Phase Converter & Wire Calculator (2026)",
  "meta_description": "Calculate exact single-to-3-phase VFD upsizing, Rotary Phase Converter idler HP, NEC 430 240V breaker/wire AWG, and braking resistor Ohms/Watts for {model_name}.",
  "specs": {{
    "motor_hp_3ph": {motor_hp},
    "motor_fla_3ph_amps": {fla_3ph},
    "single_phase_input_amps": {sp['single_phase_input_amps']},
    "upsized_vfd_hp": {upsized_vfd_hp},
    "upsized_vfd_kw": {sp['upsized_vfd_kw']},
    "min_vfd_output_amps": {sp['min_vfd_output_amps']},
    "rotary_rpc_idler_hp": {rpc_idler_hp},
    "input_breaker_240v_amps": {sp['input_breaker_240v_amps']},
    "recommended_wire_awg": "{sp['recommended_wire_awg']}",
    "braking_resistor_ohms": {sp['braking_resistor_ohms']},
    "braking_resistor_watts": {sp['braking_resistor_watts']},
    "torque_class": "{torque_class}"
  }},
  "nec_verdict": "3-sentence technical summary stating 3-phase FLA vs 1.732x single-phase input amps, required upsized VFD HP vs Rotary Phase Converter HP, NEC 430 breaker/wire gauge, and braking resistor Ohms/Watts.",
  "hardware_bundle": [
    {{
      "badge": "{upsized_vfd_hp:g} HP ({sp['upsized_vfd_kw']} kW) VFD",
      "title": "{upsized_vfd_hp:g} HP ({sp['upsized_vfd_kw']} kW) Single-Phase 240V to 3-Phase 230V VFD",
      "price_range": "$139 - $689",
      "amazon_query": "{upsized_vfd_hp:g} HP {sp['upsized_vfd_kw']}kW 220V Single to 3 Phase VFD",
      "ph_note": "1-sentence diode bridge derating and soft-start torque note"
    }},
    {{
      "badge": "{rpc_idler_hp:g} HP Rotary Converter",
      "title": "{rpc_idler_hp:g} HP Digital Rotary Phase Converter (240V Single to True 3-Phase)",
      "price_range": "$489 - $1,699",
      "amazon_query": "{rpc_idler_hp:g} HP Rotary Phase Converter 240V American Rotary",
      "ph_note": "1-sentence balanced 3-phase voltage and high-inrush note"
    }},
    {{
      "badge": "{sp['braking_resistor_ohms']}Ω {sp['braking_resistor_watts']}W Resistor",
      "title": "{sp['braking_resistor_watts']}W {sp['braking_resistor_ohms']} Ohm Aluminum-Housed VFD Dynamic Braking Resistor",
      "price_range": "$29 - $89",
      "amazon_query": "{sp['braking_resistor_watts']}W {sp['braking_resistor_ohms']} Ohm Braking Resistor VFD",
      "ph_note": "1-sentence DC bus overvoltage trip prevention note"
    }},
    {{
      "badge": "{sp['input_breaker_240v_amps']}A Breaker & Enclosure",
      "title": "240V {sp['input_breaker_240v_amps']}A 2-Pole Breaker + Ventilated NEMA Steel VFD Enclosure",
      "price_range": "$69 - $189",
      "amazon_query": "NEMA Enclosure Fan Filter VFD {sp['input_breaker_240v_amps']}A 2 Pole Breaker",
      "ph_note": "1-sentence swarf/dust protection and NEC 430 circuit note"
    }}
  ],
  "machinist_checklist": [
    "Step 1 regarding never placing a mechanical switch between VFD output and motor",
    "Step 2 regarding 1.732x to 2.0x VFD upsizing for single-phase 240V input",
    "Step 3 regarding when to choose a Rotary Phase Converter vs VFD",
    "Step 4 regarding P+ and DB braking resistor wiring and deceleration ramp setting"
  ],
  "faqs": [
    {{"q": "What size VFD or Rotary Phase Converter do I need for {model_name}?", "a": "Exact 3-phase FLA, single-phase amps, VFD HP, and RPC HP."}},
    {{"q": "What size 240V breaker and wire do I need for {model_name}?", "a": "Exact single-phase input amps, NEC 430 breaker, and copper AWG."}},
    {{"q": "What Ohm and Watt braking resistor should I use for a {motor_hp:g} HP VFD?", "a": "Exact Ohms and Watts calculation for 380V DC bus braking."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_phase_html_page(data, slug, mon_cfg):
    conv_name = data.get("converter_name", "Single-to-3-Phase VFD & Phase Converter")
    sp = data.get("specs", {})
    m_hp = round(safe_float(sp.get("motor_hp_3ph", 5.0), 5.0), 1)
    fla_3 = round(safe_float(sp.get("motor_fla_3ph_amps", 15.2), 15.2), 1)
    in_1ph = round(safe_float(sp.get("single_phase_input_amps", 28.1), 28.1), 1)
    vfd_hp = round(safe_float(sp.get("upsized_vfd_hp", 10.0), 10.0), 1)
    vfd_kw = round(safe_float(sp.get("upsized_vfd_kw", 7.5), 7.5), 1)
    rpc_hp = round(safe_float(sp.get("rotary_rpc_idler_hp", 10.0), 10.0), 1)
    brk_a = int(safe_float(sp.get("input_breaker_240v_amps", 40), 40))
    wire_awg = sp.get("recommended_wire_awg", "8 AWG THHN Copper")
    b_ohms = int(safe_float(sp.get("braking_resistor_ohms", 30), 30))
    b_watts = int(safe_float(sp.get("braking_resistor_watts", 800), 800))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Single+to+3+Phase+VFD+Rotary+Phase+Converter+240V"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{conv_name} VFD, Rotary Phase Converter & Breaker Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Single to 3 Phase VFD")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', '3-Phase Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">⚙️ {item.get('ph_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build 3-Phase Motor HP vs 1-Phase Amps, Upsized VFD, RPC & Breaker Reference Matrix Table
    ph_tiers = [
        ("1.5 HP 3-Phase (5.2A)", "9.6A @ 240V 1Φ", "3.0 HP (2.2 kW) VFD", "3.0 HP Rotary RPC", "15A / 20A (12 AWG)", "100Ω / 300W"),
        ("2.0 HP 3-Phase (6.8A)", "12.6A @ 240V 1Φ", "3.0 – 5.0 HP (2.2–3.7 kW)", "5.0 HP Rotary RPC", "20A (12 AWG Copper)", "75Ω / 400W"),
        ("3.0 HP 3-Phase (9.6A)", "17.8A @ 240V 1Φ", "5.0 HP (3.7–4.0 kW) VFD", "5.0 – 7.5 HP RPC", "25A / 30A (10 AWG)", "50Ω / 500W"),
        ("5.0 HP 3-Phase (15.2A)", "28.1A @ 240V 1Φ", "7.5 – 10 HP (5.5–7.5 kW)", "10.0 HP Rotary RPC", "40A (8 AWG Copper)", "30Ω / 800W"),
        ("7.5 HP 3-Phase (22.0A)", "40.7A @ 240V 1Φ", "15.0 HP (11 kW) VFD", "15.0 HP Rotary RPC", "60A (6 AWG THHN)", "20Ω / 1,200W"),
        ("10.0 HP 3-Phase (28.0A)", "51.8A @ 240V 1Φ", "20.0 HP (15 kW) VFD", "20.0 HP Rotary RPC", "70A / 80A (4 AWG)", "15Ω / 1,600W")
    ]
    matrix_rows_html = ""
    for m_lbl, i_lbl, v_lbl, r_lbl, b_lbl, br_lbl in ph_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{m_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{i_lbl}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{v_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{r_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{b_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{br_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("machinist_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer ph-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>NEC 430 Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', conv_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', conv_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">3PHASE</span>VFDIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 3-Phase VFDs & Converters →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-zinc-950 px-3 py-1 rounded-full">{m_hp:g} HP Motor → {vfd_hp:g} HP VFD / {rpc_hp:g} HP RPC</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">1Φ Input: {in_1ph}A ({brk_a}A Breaker)</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Braking: {b_ohms}Ω / {b_watts}W | {wire_awg}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', conv_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>NEC Article 430 & Diode-Bridge Derating Verdict:</strong> {data.get('nec_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE SINGLE-TO-3-PHASE VFD DERATING, RPC & BRAKING RESISTOR CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {conv_name} VFD, RPC & Breaker Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Select your 230V 3-phase motor horsepower, machine starting torque load, and conversion method to calculate single-phase 240V input amps, upsized VFD/RPC rating, NEC 430 breaker size, and braking resistor specs.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <label for="hpSelect" class="block text-xs font-medium text-zinc-400 mb-1">3-Phase Motor Nameplate Horsepower (@230V)</label>
            <select id="hpSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm font-bold text-white focus:outline-none focus:border-amber-500">
              <option value="1.0|3.6" {"selected" if m_hp <= 1.1 else ""}>1.0 HP 3-Phase Motor (3.6A FLA)</option>
              <option value="1.5|5.2" {"selected" if 1.1 < m_hp <= 1.6 else ""}>1.5 HP 3-Phase Motor (5.2A FLA)</option>
              <option value="2.0|6.8" {"selected" if 1.6 < m_hp <= 2.2 else ""}>2.0 HP 3-Phase Motor (6.8A FLA)</option>
              <option value="3.0|9.6" {"selected" if 2.2 < m_hp <= 3.5 else ""}>3.0 HP 3-Phase Motor (9.6A FLA)</option>
              <option value="5.0|15.2" {"selected" if 3.5 < m_hp <= 5.5 else ""}>5.0 HP 3-Phase Motor (15.2A FLA)</option>
              <option value="7.5|22.0" {"selected" if 5.5 < m_hp <= 8.0 else ""}>7.5 HP 3-Phase Motor (22.0A FLA)</option>
              <option value="10.0|28.0" {"selected" if 8.0 < m_hp <= 11.0 else ""}>10.0 HP 3-Phase Motor (28.0A FLA)</option>
              <option value="15.0|42.0" {"selected" if m_hp > 11.0 else ""}>15.0 HP 3-Phase Motor (42.0A FLA)</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="dutySelect" class="block text-xs font-medium text-zinc-400 mb-1">Machine Starting Load</label>
              <select id="dutySelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="1.65">Centrifugal Fan / Pump / Spindle (1.65x)</option>
                <option value="1.85" selected>Mill / Lathe / Table Saw / Grinder (1.85x)</option>
                <option value="2.10">Air Compressor / Hydraulic Press (2.1x)</option>
              </select>
            </div>
            <div>
              <label for="brakeSelect" class="block text-xs font-medium text-zinc-400 mb-1">Spindle / Blade Braking Duty</label>
              <select id="brakeSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="120">Standard Stop (3–5 sec Ramp)</option>
                <option value="180" selected>Fast Emergency Stop (1.5–2 sec)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Upsized VFD / RPC</span>
            <div id="vfdOut" class="text-xl sm:text-2xl font-black text-white mt-1">{vfd_hp:g} HP ({vfd_kw} kW)</div>
            <p id="rpcNoteOut" class="text-xs text-amber-400 font-semibold mt-1">Or {rpc_hp:g} HP Rotary Converter</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">240V 1Φ Breaker & Brake</span>
            <div id="brkWireOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{brk_a}A ({wire_awg.split()[0]} AWG)</div>
            <p id="resistorOut" class="text-xs text-zinc-300 font-semibold mt-1">Brake: {b_ohms}Ω / {b_watts}W</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="phAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicPhBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched VFD & Phase Converter on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {conv_name} VFD, RPC & Braking Resistor Bundle</h2>
        <span class="text-xs text-zinc-400">NEC Article 430 & √3 Diode-Derated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Single-Phase 240V to 3-Phase 230V VFD Derating, RPC & Breaker Sizing Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">3-Phase Motor HP</th>
              <th class="py-3.5 px-4">1-Phase 240V Amps</th>
              <th class="py-3.5 px-4 text-amber-400">Min Upsized VFD</th>
              <th class="py-3.5 px-4 text-emerald-400">Rotary Converter (RPC)</th>
              <th class="py-3.5 px-4">240V Breaker & Wire</th>
              <th class="py-3.5 px-4">Braking Resistor</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Master Machinist VFD Control Wiring & Braking Resistor Checklist</h2>
        <span id="phBadge" class="text-xs font-bold bg-zinc-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({conv_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} 3PhaseVFDIndex. Independent Single-to-3-Phase VFD & Rotary Phase Converter Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const hpSelect = document.getElementById('hpSelect');
    const dutySelect = document.getElementById('dutySelect');
    const brakeSelect = document.getElementById('brakeSelect');
    const vfdOut = document.getElementById('vfdOut');
    const rpcNoteOut = document.getElementById('rpcNoteOut');
    const brkWireOut = document.getElementById('brkWireOut');
    const resistorOut = document.getElementById('resistorOut');
    const phAdviceBanner = document.getElementById('phAdviceBanner');
    const dynamicPhBtn = document.getElementById('dynamicPhBtn');

    function recalculatePhase() {{
      const hpParts = hpSelect.value.split('|');
      const motorHp = parseFloat(hpParts[0]);
      const fla3 = parseFloat(hpParts[1]);
      const dutyMult = parseFloat(dutySelect.value);
      const wattsPerHp = parseInt(brakeSelect.value, 10);

      const input1PhAmps = (fla3 * 1.85).toFixed(1);
      const rawVfdHp = motorHp * dutyMult;

      let stdVfdHp = 2.0;
      let stdVfdKw = 1.5;
      if (rawVfdHp <= 2.2) {{ stdVfdHp = 2.0; stdVfdKw = 1.5; }}
      else if (rawVfdHp <= 3.5) {{ stdVfdHp = 3.0; stdVfdKw = 2.2; }}
      else if (rawVfdHp <= 5.8) {{ stdVfdHp = 5.0; stdVfdKw = 4.0; }}
      else if (rawVfdHp <= 8.2) {{ stdVfdHp = 7.5; stdVfdKw = 5.5; }}
      else if (rawVfdHp <= 11.5) {{ stdVfdHp = 10.0; stdVfdKw = 7.5; }}
      else if (rawVfdHp <= 16.5) {{ stdVfdHp = 15.0; stdVfdKw = 11.0; }}
      else if (rawVfdHp <= 22.0) {{ stdVfdHp = 20.0; stdVfdKw = 15.0; }}
      else {{ stdVfdHp = 30.0; stdVfdKw = 22.0; }}

      const rpcHp = Math.max(3.0, motorHp * 2.0);
      const rawBrk = parseFloat(input1PhAmps) * 1.35;
      let brkSpec = "20A (12 AWG)";
      if (rawBrk <= 15) brkSpec = "15A (14 AWG)";
      else if (rawBrk <= 20) brkSpec = "20A (12 AWG)";
      else if (rawBrk <= 30) brkSpec = "30A (10 AWG)";
      else if (rawBrk <= 40) brkSpec = "40A (8 AWG)";
      else if (rawBrk <= 50) brkSpec = "50A (6 AWG)";
      else if (rawBrk <= 70) brkSpec = "70A (4 AWG)";
      else brkSpec = "100A (2 AWG)";

      const bOhms = Math.max(15, Math.round((380.0 / (motorHp * 2.6)) / 5) * 5);
      const bWatts = Math.max(300, Math.round((motorHp * wattsPerHp) / 100) * 100);

      vfdOut.textContent = `${{stdVfdHp}} HP (${{stdVfdKw}} kW)`;
      rpcNoteOut.textContent = `Or ${{rpcHp}} HP Rotary Converter`;
      brkWireOut.textContent = brkSpec;
      resistorOut.textContent = `Brake: ${{bOhms}}Ω / ${{bWatts}}W (${{input1PhAmps}}A 1Φ)`;

      phAdviceBanner.innerHTML = `⚙️ <strong>NEC 430 & Diode Derating Spec:</strong> Running a <strong>${{motorHp}} HP 3-Phase motor (${{fla3}}A)</strong> on 240V single-phase draws <strong>${{input1PhAmps}}A</strong>. Install an upsized <strong>${{stdVfdHp}} HP (${{stdVfdKw}} kW) VFD</strong> (or <strong>${{rpcHp}} HP Rotary Phase Converter</strong>) on a <strong>${{brkSpec}} circuit</strong> with a <strong>${{bOhms}}Ω ${{bWatts}}W Braking Resistor</strong>.`;
      dynamicPhBtn.href = `https://${{amzDomain}}/s?k=${{stdVfdHp}}+HP+${{stdVfdKw}}kW+Single+to+3+Phase+VFD+Rotary+Phase+Converter+240V&tag=${{amzTag}}`;
    }}

    hpSelect.addEventListener('change', recalculatePhase);
    dutySelect.addEventListener('change', recalculatePhase);
    brakeSelect.addEventListener('change', recalculatePhase);
    recalculatePhase();

    const checks = document.querySelectorAll('.ph-check');
    const badge = document.getElementById('phBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Single+to+3+Phase+VFD+Rotary+Phase+Converter+240V"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('m_hp', 5.0):g} HP → {item.get('vfd_hp', 10.0):g} HP VFD</span>
            <span class="text-xs text-zinc-400">1Φ: {item.get('in_amps', 28.1)}A | {item.get('brk_a', 40)}A Brk</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['converter_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate VFD Derating, RPC & Wire →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>3PhaseVFDIndex — Single-to-3-Phase VFD Derating, Rotary Phase Converter & Wire Calculator (2026)</title>
  <meta name="description" content="Calculate exact single-phase 240V to 3-phase 230V VFD upsizing (√3 diode derating), Rotary Phase Converter idler HP, NEC 430 breaker/wire AWG, and braking resistor Ohms/Watts for mills, lathes, air compressors, and saws.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="3PhaseVFDIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">3PHASE</span>VFDIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 3-Phase VFDs & Converters →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Single-to-3-Phase VFD Derating & Rotary Phase Converter Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your 3-phase shop machine or motor HP below to calculate √3 single-phase diode-bridge VFD derating, Rotary Phase Converter idler sizing, 240V breaker/wire AWG, and braking resistor Ohms.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search machine or HP (e.g. Bridgeport Mill, 5 HP Air Compressor, 7.5 HP, American Rotary AR10, Teco VFD, Lathe...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="phGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} 3PhaseVFDIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('phGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>3PhaseVFDIndex Single-to-3-Phase VFD & Rotary Converter Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Single-to-3-Phase VFD Derating, Rotary Phase Converter & Braking Resistor Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_PHASE:
        candidates.append((CUSTOM_PHASE.strip(), 5.0, 15.2, "Heavy-Duty 3-Phase", 10.0, 10.0))
    candidates.extend(SEED_CONVERTERS)
    candidates.extend(discover_google_phase_queries(published_slugs))

    new_urls = []
    count = 0

    for phase_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        c_name = phase_tuple[0]
        slug = slugify(f"{c_name}-vfd-rpc-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating single-to-3-phase VFD & RPC calculator for: {c_name}...")
        try:
            data = generate_phase_data(phase_tuple)
            build_phase_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "converter_name": data.get("converter_name", c_name),
                "slug": slug,
                "title": data.get("seo_title", f"{c_name} Phase Converter Calculator"),
                "description": data.get("meta_description", ""),
                "m_hp": round(safe_float(sp.get("motor_hp_3ph", phase_tuple[1]), phase_tuple[1]), 1),
                "vfd_hp": round(safe_float(sp.get("upsized_vfd_hp", phase_tuple[4]), phase_tuple[4]), 1),
                "in_amps": round(safe_float(sp.get("single_phase_input_amps", 28.1), 28.1), 1),
                "brk_a": int(safe_float(sp.get("input_breaker_240v_amps", 40), 40)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {c_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new single-to-3-phase VFD & RPC calculator pages.")


if __name__ == "__main__":
    main()

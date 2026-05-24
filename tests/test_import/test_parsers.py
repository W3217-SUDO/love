from datetime import date

from app.modules.import_.parsers import parse_apple_health_xml, parse_flo_csv


def test_parse_flo_csv_maps_period_start_and_symptom_tag():
    raw = (
        b"date,type,value\n"
        b"2026-05-01,period,start\n"
        b"2026-05-01,symptom,cramps\n"
    )

    parsed = parse_flo_csv(raw)

    assert len(parsed.periods) == 1
    assert parsed.periods[0].start_date == date(2026, 5, 1)
    assert len(parsed.tags) == 1
    assert parsed.tags[0].date == date(2026, 5, 1)
    assert parsed.tags[0].tag_key == "sym_cramps"


def test_parse_apple_health_xml_maps_menstrual_flow_to_period_start():
    raw = b"""<?xml version="1.0" encoding="UTF-8"?>
    <HealthData>
      <Record
        type="HKCategoryTypeIdentifierMenstrualFlow"
        sourceName="Health"
        value="HKCategoryValueMenstrualFlowMedium"
        startDate="2026-05-01 08:00:00 +0800"
        endDate="2026-05-01 08:00:00 +0800"
      />
    </HealthData>
    """

    parsed = parse_apple_health_xml(raw)

    assert len(parsed.periods) == 1
    assert parsed.periods[0].start_date == date(2026, 5, 1)

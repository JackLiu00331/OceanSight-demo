import logging

import pytest
from sqlalchemy.exc import SQLAlchemyError

import repository
from db import engine


def payload(**changes):
    body = {"buoy_id": "BUOY-01", "timestamp": "2026-10-09T15:00:05Z", "temperature": 14.12, "pressure": 15.03}
    body.update(changes)
    return body


def post(client, **changes):
    return client.post("/api/sensor-data", json=payload(**changes))


def insert_rows(db, rows):
    """rows: (buoy_id, timestamp, temperature, pressure). Direct insert, for tests that need many readings."""
    db.executemany(
        "INSERT INTO sensor_data (buoy_id, timestamp, temperature, pressure) VALUES (?, ?, ?, ?)", rows
    )
    db.commit()


def assert_error(response, status, message=None):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"status", "message"}
    assert body["status"] == "error"
    if message is not None:
        assert body["message"] == message


class TestHealth:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestIngest:
    def test_valid_reading_is_stored_and_acknowledged(self, client, db):
        response = post(client)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "ok"
        assert isinstance(body["id"], int)
        assert body["received_at"].endswith("Z")
        row = db.execute("SELECT * FROM sensor_data WHERE id = ?", (body["id"],)).fetchone()
        assert (row["buoy_id"], row["timestamp"], row["temperature"], row["pressure"]) == (
            "BUOY-01", "2026-10-09T15:00:05Z", 14.12, 15.03)
        assert row["received_at"] == body["received_at"]

    def test_simulator_timestamp_is_kept_not_replaced_by_receive_time(self, client, db):
        post(client, timestamp="2020-01-02T03:04:05Z")
        row = db.execute("SELECT timestamp, received_at FROM sensor_data").fetchone()
        assert row["timestamp"] == "2020-01-02T03:04:05Z"
        assert row["received_at"] != row["timestamp"]

    def test_timestamp_is_normalised_to_utc_seconds(self, client, db):
        post(client, timestamp="2026-10-09T10:00:05.789-05:00")
        assert db.execute("SELECT timestamp FROM sensor_data").fetchone()["timestamp"] == "2026-10-09T15:00:05Z"

    def test_integers_are_accepted_as_numbers(self, client):
        assert post(client, temperature=18, pressure=20).status_code == 201

    @pytest.mark.parametrize("temperature, pressure", [(-5, 0), (40, 100)])
    def test_validity_limits_are_inclusive(self, client, temperature, pressure):
        assert post(client, temperature=temperature, pressure=pressure).status_code == 201

    @pytest.mark.parametrize("field", ["buoy_id", "timestamp", "temperature", "pressure"])
    def test_missing_field_is_400(self, client, db, field):
        body = payload()
        del body[field]
        response = client.post("/api/sensor-data", json=body)
        assert_error(response, 400, f"missing field: {field}")
        assert db.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0] == 0

    @pytest.mark.parametrize("field, value, message", [
        ("temperature", -5.01, "temperature out of valid range [-5, 40]"),
        ("temperature", 40.01, "temperature out of valid range [-5, 40]"),
        ("pressure", -0.01, "pressure out of valid range [0, 100]"),
        ("pressure", 100.01, "pressure out of valid range [0, 100]"),
    ])
    def test_value_outside_validity_range_is_400_and_not_stored(self, client, db, field, value, message):
        assert_error(post(client, **{field: value}), 400, message)
        assert db.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0] == 0

    @pytest.mark.parametrize("value", ["18.4", "hot", None, True, [1]])
    def test_wrongly_typed_number_is_400(self, client, value):
        assert_error(post(client, temperature=value), 400)

    def test_string_number_gets_a_clear_message(self, client):
        assert_error(post(client, temperature="18.4"), 400, "temperature must be a number")

    def test_timestamp_without_timezone_is_400(self, client):
        response = post(client, timestamp="2026-10-09T15:00:05")
        assert_error(response, 400)
        assert "timezone" in response.json()["message"]

    @pytest.mark.parametrize("value", ["yesterday", "2026-13-45T00:00:00Z", 12345, 1.5, True, ""])
    def test_malformed_timestamp_is_400(self, client, db, value):
        assert_error(post(client, timestamp=value), 400)
        assert db.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0] == 0

    def test_number_is_not_read_as_a_unix_time(self, client):
        response = post(client, timestamp=1760000000)
        assert_error(response, 400, "timestamp must be an ISO-8601 string, e.g. 2026-10-09T15:00:05Z")

    def test_unknown_buoy_is_400(self, client, db):
        assert_error(post(client, buoy_id="BUOY-99"), 400, "unknown buoy_id: BUOY-99")
        assert db.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0] == 0

    def test_malformed_json_is_400(self, client):
        response = client.post("/api/sensor-data", content="{not json", headers={"Content-Type": "application/json"})
        assert_error(response, 400, "malformed JSON body")

    def test_body_that_is_not_an_object_is_400(self, client):
        assert_error(client.post("/api/sensor-data", json=[1, 2, 3]), 400, "request body must be a JSON object")

    def test_empty_body_is_400(self, client):
        assert_error(client.post("/api/sensor-data"), 400)

    def test_reading_outside_alert_thresholds_but_valid_is_accepted(self, client):
        assert post(client, temperature=35.0, pressure=55.0).status_code == 201

    def test_every_rejection_is_logged_with_its_reason(self, client, caplog):
        with caplog.at_level(logging.WARNING, logger="oceansight_server"):
            post(client, temperature=99)
            post(client, buoy_id="BUOY-99")
        text = caplog.text
        assert "temperature out of valid range [-5, 40]" in text
        assert "unknown buoy_id: BUOY-99" in text

    def test_accepted_reading_is_logged(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="oceansight_server"):
            post(client)
        assert "BUOY-01" in caplog.text and "14.12" in caplog.text

    def test_insert_failure_is_500_in_the_error_format_and_logged(self, client, monkeypatch, caplog):
        def broken(*args, **kwargs):
            raise SQLAlchemyError("disk full")

        monkeypatch.setattr(repository, "add_reading", broken)
        with caplog.at_level(logging.ERROR, logger="oceansight_server"):
            response = post(client)
        assert_error(response, 500, "failed to store reading")
        assert "could not store reading" in caplog.text


class TestBuoys:
    def test_lists_the_five_seeded_buoys_with_coordinates_and_no_data_yet(self, client):
        response = client.get("/api/buoys")
        assert response.status_code == 200
        buoys = response.json()
        assert [b["buoy_id"] for b in buoys] == [f"BUOY-0{i}" for i in range(1, 6)]
        first = buoys[0]
        assert first == {
            "buoy_id": "BUOY-01", "name": "Monterey Offshore", "status": "active",
            "location_lat": 36.8, "location_lng": -122.5, "latest_reading": None,
        }

    def test_latest_reading_is_the_newest_by_timestamp_not_by_arrival(self, client):
        post(client, timestamp="2026-10-09T15:00:10Z", temperature=20.0)
        post(client, timestamp="2026-10-09T15:00:05Z", temperature=10.0)  # arrives later, is older
        latest = client.get("/api/buoys").json()[0]["latest_reading"]
        assert latest["timestamp"] == "2026-10-09T15:00:10Z"
        assert latest["temperature"] == 20.0

    def test_reading_shape(self, client):
        post(client)
        latest = client.get("/api/buoys").json()[0]["latest_reading"]
        assert set(latest) == {"id", "timestamp", "temperature", "pressure", "out_of_range", "out_of_range_fields"}
        assert latest["out_of_range"] is False and latest["out_of_range_fields"] == []


class TestBuoyData:
    def test_readings_come_back_oldest_first(self, client):
        for second in (30, 10, 20):
            post(client, timestamp=f"2026-10-09T15:00:{second:02d}Z")
        stamps = [r["timestamp"] for r in client.get("/api/buoys/BUOY-01/data").json()]
        assert stamps == ["2026-10-09T15:00:10Z", "2026-10-09T15:00:20Z", "2026-10-09T15:00:30Z"]

    def test_default_limit_is_the_latest_50(self, client, db):
        insert_rows(db, [("BUOY-02", f"2026-10-09T15:{i // 60:02d}:{i % 60:02d}Z", 15.0, 18.0) for i in range(60)])
        data = client.get("/api/buoys/BUOY-02/data").json()
        assert len(data) == 50
        assert data[0]["timestamp"] == "2026-10-09T15:00:10Z"
        assert data[-1]["timestamp"] == "2026-10-09T15:00:59Z"

    def test_limit_picks_the_most_recent_n(self, client, db):
        insert_rows(db, [("BUOY-02", f"2026-10-09T15:00:{i:02d}Z", 15.0, 18.0) for i in range(20)])
        data = client.get("/api/buoys/BUOY-02/data?limit=3").json()
        assert [r["timestamp"] for r in data] == ["2026-10-09T15:00:17Z", "2026-10-09T15:00:18Z", "2026-10-09T15:00:19Z"]

    def test_only_this_buoys_readings(self, client):
        post(client, buoy_id="BUOY-01")
        post(client, buoy_id="BUOY-02")
        assert len(client.get("/api/buoys/BUOY-01/data").json()) == 1

    @pytest.mark.parametrize("limit", [0, -1, 501])
    def test_limit_out_of_range_is_400(self, client, limit):
        assert_error(client.get(f"/api/buoys/BUOY-01/data?limit={limit}"), 400, "limit out of valid range [1, 500]")

    def test_limit_that_is_not_a_number_is_400(self, client):
        assert_error(client.get("/api/buoys/BUOY-01/data?limit=abc"), 400, "limit must be an integer")

    def test_limit_bounds_are_accepted(self, client):
        assert client.get("/api/buoys/BUOY-01/data?limit=1").status_code == 200
        assert client.get("/api/buoys/BUOY-01/data?limit=500").status_code == 200

    def test_unknown_buoy_is_404(self, client):
        assert_error(client.get("/api/buoys/BUOY-99/data"), 404, "unknown buoy_id: BUOY-99")

    def test_known_buoy_without_data_is_200_and_empty(self, client):
        response = client.get("/api/buoys/BUOY-05/data")
        assert response.status_code == 200
        assert response.json() == []


class TestOutOfRange:
    def flags(self, client, **values):
        post(client, **values)
        latest = client.get("/api/buoys").json()[0]["latest_reading"]
        return latest["out_of_range"], latest["out_of_range_fields"]

    def test_normal_reading_is_not_flagged(self, client):
        assert self.flags(client, temperature=15.0, pressure=20.0) == (False, [])

    @pytest.mark.parametrize("temperature", [0.0, 30.0])
    def test_alert_thresholds_are_inclusive_for_temperature(self, client, temperature):
        assert self.flags(client, temperature=temperature) == (False, [])

    @pytest.mark.parametrize("pressure", [10.0, 30.0])
    def test_alert_thresholds_are_inclusive_for_pressure(self, client, pressure):
        assert self.flags(client, pressure=pressure) == (False, [])

    @pytest.mark.parametrize("temperature", [-0.01, 30.01, 35.0, -4.0])
    def test_temperature_outside_thresholds_is_flagged(self, client, temperature):
        assert self.flags(client, temperature=temperature) == (True, ["temperature"])

    @pytest.mark.parametrize("pressure", [9.99, 30.01, 55.0, 0.5])
    def test_pressure_outside_thresholds_is_flagged(self, client, pressure):
        assert self.flags(client, pressure=pressure) == (True, ["pressure"])

    def test_both_fields_can_be_flagged(self, client):
        assert self.flags(client, temperature=36.0, pressure=50.0) == (True, ["temperature", "pressure"])

    def test_flag_also_appears_in_the_history(self, client):
        post(client, temperature=36.0)
        assert client.get("/api/buoys/BUOY-01/data").json()[0]["out_of_range_fields"] == ["temperature"]


class TestPlumbing:
    def test_unknown_route_is_404_in_the_error_format(self, client):
        assert_error(client.get("/api/nope"), 404)

    def test_wrong_method_is_405_in_the_error_format(self, client):
        assert_error(client.get("/api/sensor-data"), 405)

    def test_foreign_keys_are_enforced_on_every_connection(self):
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1

    def test_cors_allows_the_dashboard_origin(self, client):
        response = client.options(
            "/api/buoys", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_cors_does_not_allow_other_origins(self, client):
        response = client.options(
            "/api/buoys", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in response.headers

from sqlalchemy import inspect

from db.database import engine
from db.models.alert import Alert
from db.models.classification import Classification
from db.models.data_source import DataSource
from db.models.emission import Emission
from db.models.event_observation import EventObservation
from db.models.facility import Facility
from db.models.risk_score import RiskScore
from db.models.satellite_image import SatelliteImage
from db.models.site_baseline import SiteBaseline
from db.models.thermal_event import ThermalEvent
from db.models.thermal_observation import ThermalObservation


MODELS = [
    DataSource,
    Facility,
    ThermalObservation,
    ThermalEvent,
    EventObservation,
    SiteBaseline,
    Classification,
    RiskScore,
    Emission,
    SatelliteImage,
    Alert,
]


def test_tables_exist():
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    for model in MODELS:
        assert model.__tablename__ in db_tables, (
            f"Missing table: {model.__tablename__}"
        )

    print("All model tables exist in database.")


def test_model_columns_exist():
    inspector = inspect(engine)

    for model in MODELS:
        table_name = model.__tablename__

        db_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }

        model_columns = set(model.__table__.columns.keys())

        missing = model_columns - db_columns

        assert not missing, (
            f"{table_name}: model columns missing from DB: {missing}"
        )

    print("All model columns exist in database.")


def test_foreign_keys():
    inspector = inspect(engine)

    for model in MODELS:
        table_name = model.__tablename__

        db_fks = inspector.get_foreign_keys(table_name)

        db_fk_pairs = {
            (
                fk["constrained_columns"][0],
                fk["referred_table"],
                fk["referred_columns"][0],
            )
            for fk in db_fks
            if len(fk["constrained_columns"]) == 1
        }

        model_fk_pairs = {
            (
                column.name,
                list(column.foreign_keys)[0].column.table.name,
                list(column.foreign_keys)[0].column.name,
            )
            for column in model.__table__.columns
            if column.foreign_keys
        }

        missing = model_fk_pairs - db_fk_pairs

        assert not missing, (
            f"{table_name}: model foreign keys missing from DB: {missing}"
        )

    print("All model foreign keys exist in database.")


if __name__ == "__main__":
    test_tables_exist()
    test_model_columns_exist()
    test_foreign_keys()

    print("DB/model schema verification passed!")
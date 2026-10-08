"""
db/init_db.py
-------------
Convenience helper for local development and startup initialization.
Ensures all ORM tables, columns, and custom PostgreSQL enum types exist.
"""

import logging
from sqlalchemy import text

from app.db.base import Base          # imports Base + all models
from app.db.session import engine

logger = logging.getLogger(__name__)


async def ensure_schema_up_to_date(conn) -> None:
    """
    Executes idempotent DDL statements to ensure all Postgres enum types,
    tables, and columns exist even if tables were originally created under
    an earlier schema version.
    """
    ddl_statements = [
        # Enum types
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'soil_type_enum') THEN
                CREATE TYPE soil_type_enum AS ENUM ('Clayey', 'Sandy', 'Loamy', 'Rocky', 'Black Cotton', 'Red Soil');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'land_type_enum') THEN
                CREATE TYPE land_type_enum AS ENUM ('Residential', 'Commercial', 'Industrial', 'Agricultural');
            END IF;
        END $$;
        """,
        # Ensure users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # Ensure lands table
        """
        CREATE TABLE IF NOT EXISTS lands (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            land_name VARCHAR(150) NOT NULL,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            address VARCHAR(255) NOT NULL,
            area_sqft FLOAT,
            road_width FLOAT,
            boundary_geojson JSONB,
            soil_type soil_type_enum,
            land_type land_type_enum NOT NULL,
            water_availability BOOLEAN,
            electricity_availability BOOLEAN,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # Defensive ALTER statements for lands table
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS land_name VARCHAR(150);",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS latitude FLOAT;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS longitude FLOAT;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS address VARCHAR(255);",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS area_sqft FLOAT;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS road_width FLOAT;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS boundary_geojson JSONB;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS soil_type soil_type_enum;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS land_type land_type_enum;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS water_availability BOOLEAN;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS electricity_availability BOOLEAN;",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
        "ALTER TABLE lands ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
        # Ensure analyses table
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id UUID PRIMARY KEY,
            land_id UUID NOT NULL REFERENCES lands(id) ON DELETE CASCADE,
            suitability_score FLOAT NOT NULL,
            recommended_building_type VARCHAR(50) NOT NULL,
            flood_risk VARCHAR(20) NOT NULL,
            environmental_risk VARCHAR(20) NOT NULL,
            infrastructure_score FLOAT NOT NULL,
            traffic_accessibility_score FLOAT NOT NULL,
            risk_score FLOAT NOT NULL,
            risk_level VARCHAR(20) NOT NULL,
            risk_breakdown JSONB NOT NULL,
            ai_explanation TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # Defensive ALTER statements for analyses table
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS land_id UUID REFERENCES lands(id) ON DELETE CASCADE;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS suitability_score FLOAT;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS recommended_building_type VARCHAR(50);",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS flood_risk VARCHAR(20);",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS environmental_risk VARCHAR(20);",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS infrastructure_score FLOAT;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS traffic_accessibility_score FLOAT;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS risk_score FLOAT;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20);",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS risk_breakdown JSONB;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS ai_explanation TEXT;",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
    ]

    for stmt in ddl_statements:
        try:
            await conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Defensive DDL execution note for statement: %s - Error: %s", stmt[:50].strip(), exc)


async def create_all_tables() -> None:
    """Creates all tables defined on Base.metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_schema_up_to_date(conn)
    logger.info("Database tables created and updated.")


async def drop_all_tables() -> None:
    """Drops all tables defined on Base.metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Database tables dropped.")


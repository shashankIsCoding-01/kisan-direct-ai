from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KisanDirect AI"
    app_env: str = "development"
    app_debug: bool = True
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/kisandirect"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    forecast_model_path: str = "models/demand_forecast.joblib"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

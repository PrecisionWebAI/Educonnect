"""The one place configuration comes from.

Every value is read from the environment - `backend/.env` locally, the platform's
own env vars when deployed - and nothing environment-specific is written in the
code. The values a deployment cannot run without are checked here, at import, so
a missing `DB_PASSWORD` or a placeholder `SECRET_KEY` in production stops the
process instead of serving with it.
"""

from pathlib import Path
from typing import Literal, Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: `backend/` - three levels above this module, and the home of `backend/.env`.
BASE_DIR = Path(__file__).resolve().parents[2]

#: The placeholder the example files ship. Never acceptable off `local`.
DEV_SECRET_KEY = "dev-only-change-me"
#: What older commits and `docker-compose.yml` used to default to.
_LEGACY_SECRET_KEY = "super_secret_eduverse_key_change_in_production"


class Settings(BaseSettings):
    #: Which environment these values describe. `local` relaxes the checks a
    #: deployed environment must pass; `staging` / `production` are held to them.
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # ---- Database ----
    # The parts are optional only so that a managed DSN (`DATABASE_URL_OVERRIDE`)
    # can stand in for them - the validator insists on one or the other.
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_SCHEMA: str = "public"
    #: A complete DSN that wins over the parts above. The Supabase dashboard hands
    #: one out verbatim, and a pooler URI carries settings (user name, port) the
    #: individual parts cannot express.
    DATABASE_URL_OVERRIDE: str = ""
    #: `require` for Supabase and any managed Postgres; empty for a local server.
    DB_SSLMODE: str = ""

    @property
    def is_managed_db(self) -> bool:
        """True when the database is not ours to create (`CREATE DATABASE`).

        A managed provider (Supabase) owns its databases and schemas: the app may
        only connect to the one its DSN names, never create it.
        """
        return bool(self.DATABASE_URL_OVERRIDE)

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        # URL-encode user/password so special chars like '@' don't break the DSN
        url = (
            f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        if self.DB_SSLMODE:
            url += f"?sslmode={self.DB_SSLMODE}"
        return url

    #: Log every SQL statement. Off by default - it is a debugging switch, and the
    #: app used to ship with it permanently on.
    SQL_ECHO: bool = False

    # ---- Auth ----
    SECRET_KEY: str = DEV_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ---- CORS ----
    # Comma-separated. The defaults are for local development only; a deployment
    # lists its own frontend (see `backend/.env-example`).
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000,http://127.0.0.1:3000"
    #: Preview deploys (Netlify branch URLs) change on every build, so they are
    #: allowed by pattern instead of by name. Set to "" to allow no pattern.
    CORS_ORIGIN_REGEX: str = r"^https:\/\/([a-zA-Z0-9_-]+\.)?netlify\.app$"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    # ---- Seed data (`scripts/seed.py` and the demo roll) ----
    # The credentials the seeds write. They were hard-coded in the scripts - and
    # therefore committed - before they moved here.
    SEED_DEMO_DATA: bool = True
    #: The password every demo student / teacher / guardian account gets. Demo
    #: data with a published password, which is why it may carry a default.
    SEED_DEMO_PASSWORD: str = "demo@1234"
    SEED_PLATFORM_ADMIN_LOGIN: str = "admin"
    #: Required only when the platform account does not exist yet (first boot).
    SEED_PLATFORM_ADMIN_PASSWORD: str = ""
    #: Required only when a school admin does not exist yet (first boot).
    SEED_SCHOOL_ADMIN_PASSWORD: str = ""

    @model_validator(mode="after")
    def _reject_unusable_configuration(self) -> Self:
        """Fail at import, not at the first request."""
        if not self.DATABASE_URL_OVERRIDE:
            missing = [
                name
                for name in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME")
                if not getattr(self, name)
            ]
            if missing:
                raise ValueError(
                    f"Database not configured: set {', '.join(missing)} (in "
                    "backend/.env), or set DATABASE_URL_OVERRIDE to a full DSN."
                )
        if self.ENVIRONMENT != "local" and self.SECRET_KEY in (
            "",
            DEV_SECRET_KEY,
            _LEGACY_SECRET_KEY,
        ):
            raise ValueError(
                f"SECRET_KEY is still the placeholder but ENVIRONMENT={self.ENVIRONMENT}. "
                'Generate one: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return self

    # ---- AI / LLM (blueprint §2.5) ----
    # Provider "ollama" = local Qwen 2.5. Aaj/local, kal OpenAI/Gemini —
    # sirf env badlo, code nahi. (factory isi par decide karegi — Phase 2)
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = "ollama"  # Ollama ko token nahi chahiye; OpenAI ke liye real key
    # NOTE: Ollama ka tag exactly wahi likho jo `ollama list` dikhata hai.
    # Is machine par installed: qwen2.5:latest (7.6B, Q4_K_M, ctx 32768)
    LLM_MODEL: str = "qwen2.5:latest"
    LLM_TEMPERATURE: float = Field(
        default=0.3, ge=0.0, le=1.0
    )  # generation — rigid rehna
    LLM_JUDGE_TEMPERATURE: float = Field(
        default=0.1, ge=0.0, le=1.0
    )  # quality judge — zero creative
    LLM_MAX_TOKENS: int = Field(default=2048, ge=128, le=32768)
    # Local model ka pehla token slow aata hai (model RAM mein load hota hai) —
    # isliye timeout cloud se zyada (120s) rakha hai. Warna pehli call hi fail.
    LLM_TIMEOUT_SECONDS: int = Field(default=180, ge=10, le=600)
    LLM_MAX_RETRIES: int = Field(default=2, ge=0, le=5)

    # ---- Generation mix (blueprint §2.5 — default difficulty/Bloom plan) ----
    # Format "30/50/20" = Easy/Medium/Hard percentage. LLM se nahi maangte ki
    # khud decide kare — hum pehle slot banaate hain, model sirf content bharta hai.
    DIFFICULTY_MIX: str = "30/50/20"
    BLOOM_MIX: str = "20/40/30/10"  # Remember/Understand/Apply/Analyze+

    @property
    def difficulty_mix_list(self) -> list[int]:
        """'30/50/20' → [30, 50, 20]. Galat format → default."""
        try:
            vals = [int(v.strip()) for v in self.DIFFICULTY_MIX.split("/")]
            return vals if len(vals) == 3 else [30, 50, 20]
        except ValueError:
            return [30, 50, 20]

    @property
    def bloom_mix_list(self) -> list[int]:
        """'20/40/30/10' → [20, 40, 30, 10]. Galat format → default."""
        try:
            vals = [int(v.strip()) for v in self.BLOOM_MIX.split("/")]
            return vals if len(vals) == 4 else [20, 40, 30, 10]
        except ValueError:
            return [20, 40, 30, 10]

    # ---- Repair aur judge (bounded agentic loop) ----
    # Repair = khaali/failed slots dobara banana (poore paper ka wait nahi).
    # `passes` **bounded** rakha hai: 1 default, 2 max — infinite loop ka rasta nahi.
    EXAMS_REPAIR_PASSES: int = Field(default=1, ge=0, le=2)
    # Judge (LLM quality check) background job ke andar chalta hai — local Qwen par
    # ~70s lagta hai. Rules (Layer 1) hamesha chalte hain, judge optional hai.
    EXAMS_USE_LLM_JUDGE: bool = True

    # ---- Embeddings (blueprint §2.4) ----
    # Provider:
    #   "dummy"  → deterministic hashing (default) — **network/LLM ke bina** poori
    #              RAG pipeline chalti hai (dev + tests + offline demo). Semantic
    #              quality nahi, par plumbing pura real.
    #   "ollama" → local embeddings (`nomic-embed-text`) — offline + free + semantic
    #   "hf"     → HuggingFace Inference API (token chahiye)
    EMBEDDING_PROVIDER: str = "dummy"
    HUGGINGFACE_API_KEY: str = ""  # free token: huggingface.co/settings/tokens
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = Field(default=384, ge=64, le=8192)
    EMBEDDING_BATCH_SIZE: int = Field(default=16, ge=1, le=128)
    VECTOR_COLLECTION_PREFIX: str = "edu_school_"  # Qdrant tenant isolation

    # ---- RAG / vector store (blueprint §2.4) ----
    # QDRANT_URL set hai   → server mode (production)
    # QDRANT_URL khaali hai → Qdrant ka **local persistent** mode (dev/offline) —
    #   same client, same API, bas data disk par local folder mein.
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_LOCAL_PATH: str = ".qdrant_local"
    # Tenant (school) isolation: abhi single-school product hai (koi School table
    # nahi), isliye ek config value. Multi-school par yeh JWT/DB se aayega.
    VECTOR_TENANT: str = "default"
    RAG_ENABLED: bool = True  # false → purana behaviour (sirf paste-text excerpts)
    RETRIEVAL_TOP_K: int = Field(default=6, ge=1, le=50)
    RETRIEVAL_MIN_SCORE: float = 0.0
    CHUNK_SIZE: int = Field(default=800, ge=200, le=4000)
    CHUNK_OVERLAP: int = Field(default=100, ge=0, le=1000)
    # Anti-repeat: kitne purane questions "already used" list mein bhejne hain
    ANTI_REPEAT_LOOKBACK: int = Field(default=60, ge=0, le=500)

    # ---- OCR (image/scanned source ka text) ----
    # Kyun opt-in? OCR ka engine (tesseract) aur uska python wrapper ek **extra
    # system dependency** hai. Isliye default `none` rakha hai: image source par
    # hum saaf warning dete hain ("iska content retrieval mein nahi aayega"),
    # chup-chaap khaali index nahi karte.
    #   "none"      → OCR nahi (default; koi extra install nahi)
    #   "tesseract" → `uv add pytesseract pillow` + system tesseract binary
    #   "vision"    → LLM vision model (blueprint §2.6 ka M4 vision pipeline)
    OCR_ENABLED: bool = False
    OCR_PROVIDER: str = "none"
    OCR_LANGUAGE: str = "eng"  # tesseract lang codes ("eng+hin" bhi chalta hai)
    OCR_MAX_CHARS: int = Field(default=8000, ge=200, le=100000)

    # ---- Source files (uploads) ----
    # MinIO/S3 config neeche hai, par abhi local disk use karte hain (zero setup).
    # Path backend/ ke relative hai. Baad mein MinIO par shift = sirf ek function.
    UPLOAD_DIR: str = ".uploads"
    UPLOAD_MAX_MB: int = Field(default=25, ge=1, le=200)
    URL_FETCH_MAX_KB: int = Field(default=2048, ge=64, le=20480)
    URL_FETCH_TIMEOUT: int = Field(default=20, ge=5, le=120)

    # ---- Queue / async jobs (blueprint §2.8) ----
    REDIS_URL: str = "redis://localhost:6379/0"
    GENERATION_QUEUE: str = "paper_generation"

    # ---- Object storage (blueprint §2.6) ----
    # The credentials are secrets, so they carry no default: an unconfigured MinIO
    # is visibly unconfigured instead of silently running as `minioadmin`.
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "educonnect"

    #: `backend/.env`, resolved from this file's location rather than from the
    #: current working directory - so `uvicorn`, `alembic`, `pytest` and the
    #: scripts all read the same file no matter where they were started from.
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

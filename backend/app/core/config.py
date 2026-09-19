from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_SCHEMA: str = "public"

    @property
    def DATABASE_URL(self) -> str:
        # URL-encode user/password so special chars like '@' don't break the DSN
        return (
            f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    SECRET_KEY: str = "super_secret_eduverse_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    CORS_ORIGINS: str = (
        "http://localhost,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "https://aieduconnect.netlify.app,"
        "https://educonnect-k1tl.onrender.com"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

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

    # ---- Embeddings (blueprint §2.4) ----
    # Provider "hf" = HuggingFace Inference API (free tier). Badme local (ollama) swap.
    EMBEDDING_PROVIDER: str = "hf"
    HUGGINGFACE_API_KEY: str = ""  # free token: huggingface.co/settings/tokens
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = Field(default=384, ge=64, le=8192)
    VECTOR_COLLECTION_PREFIX: str = "edu_school_"  # Qdrant tenant isolation

    # ---- Queue / async jobs (blueprint §2.8) ----
    REDIS_URL: str = "redis://localhost:6379/0"
    GENERATION_QUEUE: str = "paper_generation"

    # ---- Object storage (blueprint §2.6) ----
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "educonnect"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

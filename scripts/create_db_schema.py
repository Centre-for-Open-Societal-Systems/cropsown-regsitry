import os
import sys
import asyncio
from tortoise import Tortoise

# Ensure core_pkg and cropsown-extension are on python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CORE_PKG_PATH = os.path.join(PROJECT_ROOT, "core_pkg")
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "cropsown-extension", "src")

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, CORE_PKG_PATH)
sys.path.insert(0, EXTENSION_PATH)

async def init_tortoise():
    # Read DB config from env
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5446")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_name = os.getenv("REGISTRY_DB", "cropsown")

    db_url = f"postgres://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    print(f"📡 Connecting to database: postgres://{db_user}:****@{db_host}:{db_port}/{db_name}")

    # Import initializers
    from core_pkg.app import Initializer as CoreInitializer
    from openg2p_registry_cropsown_extension.app import Initializer as ExtensionInitializer

    print("🛠️ Initializing Tortoise ORM models...")
    core_init = CoreInitializer()
    ext_init = ExtensionInitializer()

    # We initialize tortosie ORM with all modules
    models_list = [
        "core_pkg.models",
        "openg2p_registry_cropsown_extension.register_domain.models"
    ]

    await Tortoise.init(
        db_url=db_url,
        modules={"models": models_list}
    )

    print("🏗️ Generating schema for all tables (create_models)...")
    await Tortoise.generate_schemas(safe=True)
    print("✅ Schema creation complete!")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(init_tortoise())

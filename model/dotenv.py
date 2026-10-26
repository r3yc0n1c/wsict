import os

def load_env_file(filepath=".env"):
    # Check if the file exists to avoid crashes
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found.")
        return

    with open(filepath, "r") as file:
        for line in file:
            # Remove leading/trailing whitespace
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Split by the first '=' character only
            if "=" in line:
                key, value = line.split("=", 1)

                # Clean up whitespace and strip quotes from the value
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                # Inject into the environment variables
                os.environ[key] = value
